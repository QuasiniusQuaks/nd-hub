"""Application factory for ND-Hub web backend (Issue #60/#61/#96)."""

import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from security_manager import SecurityManager

import backend.helpers as _helpers_mod  # noqa: F401 — re-export surface for monkeypatch
from backend.auth import SessionInfo, TokenStore, get_current_session
from backend.config import (
    resolve_auto_backup_hours,
    resolve_db_engine,
    resolve_email_delivery_settings,
    resolve_max_backup_restore_mb,
    resolve_runtime_paths,
)

# Re-exports for monkeypatch/tests (backend.app._send_email_via_smtp etc.)
from backend.helpers import *  # noqa: E402, F403
from backend.helpers import (
    _get_user_flags,
    _permissions_for_role,
    _run_auto_backup_if_due,
    _run_auto_backup_if_due_mariadb,
)
from backend.login_protection import (
    LoginProtectionConfig,
    attach_login_protection,
    make_login_lockout_callbacks,
)
from backend.models import *  # noqa: E402, F403
from backend.models import ALL_PERMISSION_KEYS, LoginRequest, LoginResponse
from backend.repository_factory import create_repository
from backend.router_registration import register_all_routers
from backend.security_middleware import apply_security_middleware


def create_app(db_path: str | None = None) -> FastAPI:
    """Application factory for runtime and tests."""
    db_engine = resolve_db_engine(default="sqlite")
    runtime_paths = resolve_runtime_paths(db_path=db_path)
    database_path = str(runtime_paths.database_path)
    source_db_path = runtime_paths.database_path
    attachments_dir = runtime_paths.attachments_dir
    backups_dir = runtime_paths.backups_dir
    auto_backup_hours = resolve_auto_backup_hours(default=24)
    max_backup_restore_mb = resolve_max_backup_restore_mb(default=200)
    max_backup_restore_bytes = max_backup_restore_mb * 1024 * 1024
    email_delivery_settings = resolve_email_delivery_settings(default_mode="draft")
    feature_multi_institution = (os.environ.get("ND_HUB_FEATURE_MULTI_INSTITUTION", "1") or "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    feature_institution_map = (os.environ.get("ND_HUB_FEATURE_INSTITUTION_MAP", "1") or "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    repository = create_repository(db_path=database_path, db_engine=db_engine)
    security = SecurityManager(database_path)
    token_store = TokenStore(storage_path=database_path)

    def _mask_token(token: str) -> str:
        token = str(token or "")
        if len(token) <= 10:
            return "*" * len(token)
        return f"{token[:4]}{'*' * (len(token) - 8)}{token[-4:]}"

    def _resolve_archive_status(expires_at: datetime | None, revoked_at: datetime | None, token: str) -> str:
        if isinstance(expires_at, datetime) and expires_at <= datetime.now(UTC):
            return "abgelaufen"
        if revoked_at is not None:
            return "widerrufen"
        return "aktiv" if token_store.get(token) is not None else "widerrufen"

    def _user_permissions(username: str, role: str | None) -> set[str]:
        if role == "Admin":
            return set(ALL_PERMISSION_KEYS)
        row = security.cur.execute(
            "SELECT permissions FROM users WHERE username = ?",
            ((username or "").strip(),),
        ).fetchone()
        raw_permissions = row[0] if row else None
        return _permissions_for_role(role, raw_permissions)

    def _allowed_depot_permissions(session: SessionInfo) -> dict[int, dict[str, bool]]:
        if session.role == "Admin":
            depots = repository.list_depots(limit=2000, offset=0)
            return {
                int(item["id"]): {"can_read": True, "can_write": True}
                for item in depots
                if int(item.get("id", 0)) > 0
            }
        if not hasattr(repository, "list_user_depot_permissions"):
            return {}
        rows = repository.list_user_depot_permissions(session.username)
        result: dict[int, dict[str, bool]] = {}
        for row in rows:
            depot_id = int(row.get("depot_id") or 0)
            if depot_id <= 0:
                continue
            result[depot_id] = {
                "can_read": bool(int(row.get("can_read") or 0)),
                "can_write": bool(int(row.get("can_write") or 0)),
            }
        return result

    def _ensure_depot_access(session: SessionInfo, depot_id: int, require_write: bool = False) -> None:
        if session.role == "Admin":
            return
        allowed = _allowed_depot_permissions(session)
        depot_rights = allowed.get(int(depot_id))
        if not depot_rights:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Depot nicht freigegeben.")
        key = "can_write" if require_write else "can_read"
        if not bool(depot_rights.get(key)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Depot-Berechtigung fehlt.")

    def _allowed_depot_ids(session: SessionInfo, require_write: bool = False) -> list[int]:
        if session.role == "Admin":
            rows = repository.list_depots(limit=5000, offset=0)
            return [int(row["id"]) for row in rows if int(row.get("id", 0)) > 0]
        key = "can_write" if require_write else "can_read"
        allowed = _allowed_depot_permissions(session)
        return sorted([depot_id for depot_id, rights in allowed.items() if rights.get(key)])

    def _scoped_requested_ids(session: SessionInfo, requested_ids: list[int], require_write: bool = False) -> list[int]:
        allowed_ids = set(_allowed_depot_ids(session, require_write=require_write))
        if session.role != "Admin" and not allowed_ids:
            return []
        if not requested_ids:
            return sorted(allowed_ids) if session.role != "Admin" else []
        safe_requested = sorted({int(item) for item in requested_ids if int(item) > 0})
        if session.role == "Admin":
            return safe_requested
        forbidden = [item for item in safe_requested if item not in allowed_ids]
        if forbidden:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Mindestens ein Depot ist nicht freigegeben.",
            )
        return safe_requested

    def require_permission(permission_key: str):
        def _dependency(session: SessionInfo = Depends(get_current_session)) -> SessionInfo:
            if permission_key not in ALL_PERMISSION_KEYS:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Unbekannte Berechtigung: {permission_key}",
                )
            if session.role == "Admin":
                return session
            permissions = _user_permissions(session.username, session.role)
            if permission_key not in permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Berechtigung fehlt.",
                )
            return session

        return _dependency

    @asynccontextmanager
    async def _lifespan(_app: FastAPI):
        try:
            try:
                if db_engine == "mariadb":
                    created = _run_auto_backup_if_due_mariadb(backups_dir, auto_backup_hours)
                else:
                    created = _run_auto_backup_if_due(source_db_path, backups_dir, auto_backup_hours)
                if created is not None:
                    repository.log_audit(
                        username="system",
                        action="create",
                        resource_type="backup",
                        details={"operation": "auto", "filename": created.name},
                    )
            except Exception:
                logger.warning("Auto-backup during startup failed", exc_info=True)
            yield
        finally:
            security.close()
            token_store.close()

    app = FastAPI(title="ND-Hub Backend", version="0.1.1", lifespan=_lifespan)
    app.state.repository = repository
    app.state.security = security
    app.state.token_store = token_store
    app.state.database_path = database_path
    app.state.web_dir = Path(__file__).parent / "web"
    app.state.attachments_dir = attachments_dir
    app.state.backups_dir = backups_dir
    app.state.auto_backup_hours = auto_backup_hours
    app.state.max_backup_restore_mb = max_backup_restore_mb
    app.state.db_engine = db_engine
    app.state.email_delivery_settings = email_delivery_settings
    app.state.feature_multi_institution = feature_multi_institution
    app.state.feature_institution_map = feature_institution_map

    apply_security_middleware(app)

    login_cfg = LoginProtectionConfig.from_env()
    tracker = attach_login_protection(app, login_cfg)
    _check_login_lockout, _record_login_failure, _clear_login_lockout, _audit_login_lockout = (
        make_login_lockout_callbacks(
            tracker,
            security,
            max_fails=login_cfg.max_fails,
            lockout_seconds=login_cfg.lockout_seconds,
        )
    )
    login_limiter = app.state.login_limiter
    login_ip_limit = app.state.login_ip_limit

    app.mount(
        "/web",
        StaticFiles(directory=app.state.web_dir, html=False),
        name="web",
    )

    @app.get("/")
    def web_index() -> FileResponse:
        return FileResponse(app.state.web_dir / "index.html")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "db_engine": str(app.state.db_engine)}

    @app.post("/auth/login", response_model=LoginResponse)
    @login_limiter.limit(login_ip_limit)
    def login(payload: LoginRequest, request: Request) -> LoginResponse:
        username_attempt = payload.username.strip()
        remaining_lockout = _check_login_lockout(username_attempt)
        if remaining_lockout is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Account temporaer gesperrt. Bitte {remaining_lockout}s warten.",
                headers={"Retry-After": str(remaining_lockout)},
            )
        ok, _message = security.authenticate(username_attempt, payload.password)
        if not ok:
            lockout_seconds = _record_login_failure(username_attempt)
            if lockout_seconds is not None:
                _audit_login_lockout(username_attempt, request.client.host if request.client else "unknown")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Account gesperrt nach {app.state.login_max_fails} Fehlversuchen. "
                        f"Bitte {lockout_seconds}s warten."
                    ),
                    headers={"Retry-After": str(lockout_seconds)},
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Benutzername oder Passwort ungueltig.",
            )
        _clear_login_lockout(username_attempt)
        username = security.get_current_user() or payload.username
        user_flags = _get_user_flags(security, username)
        token = token_store.issue(
            username=username,
            role=security.get_current_role(),
        )
        return LoginResponse(
            token=token,
            username=username,
            role=security.get_current_role(),
            requires_password_change=user_flags["requires_password_change"],
            permissions=user_flags["permissions"],
        )

    def _close_security() -> None:
        nonlocal security
        security.close()

    def _reopen_security() -> None:
        nonlocal security, token_store
        security = SecurityManager(database_path)
        app.state.security = security
        token_store = TokenStore()
        app.state.token_store = token_store

    register_all_routers(
        app,
        security=security,
        token_store=token_store,
        repository=repository,
        require_permission=require_permission,
        database_path=database_path,
        source_db_path=source_db_path,
        backups_dir=backups_dir,
        auto_backup_hours=auto_backup_hours,
        max_backup_restore_mb=max_backup_restore_mb,
        max_backup_restore_bytes=max_backup_restore_bytes,
        db_engine=db_engine,
        close_security=_close_security,
        reopen_security=_reopen_security,
        mask_token=_mask_token,
        resolve_archive_status=_resolve_archive_status,
        allowed_depot_permissions=_allowed_depot_permissions,
        ensure_depot_access=_ensure_depot_access,
        scoped_requested_ids=_scoped_requested_ids,
        allowed_depot_ids=_allowed_depot_ids,
        user_permissions=_user_permissions,
    )

    return app
