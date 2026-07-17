"""FastAPI app for ND-Hub desktop backend."""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.auth import SessionInfo, TokenStore, bearer_scheme, get_current_session
from backend.config import resolve_db_path
from backend.database import SqliteRepository
from security_manager import SecurityManager

from backend.models import *  # noqa: F403
from backend.helpers import *  # noqa: F403

from backend.models import (  # noqa: E402
    ALLOWED_USER_ROLES,
    DEFAULT_USER_PERMISSIONS,
    PDF_MIME_TYPES,
    PERMISSION_DEFINITIONS,
    PERMISSION_TEMPLATES,
    BewegungCreateRequest,
    DepotAssignmentsUpdateRequest,
    DepotUpsertRequest,
    EmailDraftCreateRequest,
    EmailRecipientPreviewRequest,
    KontaktUpsertRequest,
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    PraeparatUpsertRequest,
    UserCreateRequest,
    UserPasswordResetRequest,
    UserUpdateRequest,
)
from backend.helpers import (  # noqa: E402
    _add_months,
    _analyze_import_dataframe,
    _build_attachment_target_path,
    _build_import_template,
    _create_backup_snapshot,
    _csv_response,
    _enrich_verfall_rows,
    _ensure_import_dependencies,
    _get_avatar_path_for_user,
    _get_user_flags,
    _list_backup_files,
    _load_import_dataframe,
    _map_import_columns,
    _normalize_import_column_name,
    _normalize_user_row,
    _normalize_verfall_thresholds,
    _parse_id_list_csv,
    _parse_import_date,
    _parse_permission_list,
    _pdf_response,
    _permissions_for_role,
    _permissions_json_for_storage,
    _persist_pdf_upload,
    _pptx_response,
    _run_auto_backup_if_due,
    _safe_backup_label,
    _sanitize_filename_part,
    _verfall_category,
)

def create_app(db_path: str | None = None) -> FastAPI:
    """Application factory for runtime and tests."""
    database_path = db_path or resolve_db_path()
    source_db_path = Path(database_path).resolve()
    backups_dir = source_db_path.parent / "backups"
    auto_backup_hours = int((os.environ.get("ND_HUB_AUTO_BACKUP_HOURS", "24") or "24").strip() or "24")
    repository = SqliteRepository(database_path)
    security = SecurityManager(database_path)
    token_store = TokenStore()

    def _user_permissions(username: str, role: str | None) -> set[str]:
        if role == "Admin":
            return set(ALL_PERMISSION_KEYS)
        row = security.cur.execute(
            "SELECT permissions FROM users WHERE username = ?",
            ((username or "").strip(),),
        ).fetchone()
        raw_permissions = row[0] if row else None
        return _permissions_for_role(role, raw_permissions)

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
                created = _run_auto_backup_if_due(source_db_path, backups_dir, auto_backup_hours)
                if created is not None:
                    repository.log_audit(
                        username="system",
                        action="create",
                        resource_type="backup",
                        details={"operation": "auto", "filename": created.name},
                    )
            except Exception:
                # Auto backup should never block startup.
                logger.warning("Auto-backup during startup failed", exc_info=True)
            yield
        finally:
            security.close()

    app = FastAPI(title="ND-Hub Backend", version="0.1.1", lifespan=_lifespan)
    app.state.repository = repository
    app.state.security = security
    app.state.token_store = token_store
    app.state.database_path = database_path
    app.state.web_dir = Path(__file__).parent / "web"
    app.state.attachments_dir = Path(database_path).resolve().parent / "attachments"
    app.state.backups_dir = backups_dir
    app.state.auto_backup_hours = auto_backup_hours

    # ---- Security-Middleware (Issue #68 — Port aus Web-Backend) ----
    # 1) TrustedHost: blockiert Host-Header-Injection
    _allowed_hosts_raw = os.environ.get("ND_HUB_ALLOWED_HOSTS", "*").strip()
    if _allowed_hosts_raw == "*":
        _allowed_hosts = ["*"]
    else:
        _allowed_hosts = [h.strip() for h in _allowed_hosts_raw.split(",") if h.strip()]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=_allowed_hosts)

    # 2) CORS: restriktiver Default (leere allow_origins)
    _cors_raw = os.environ.get("ND_HUB_CORS_ORIGINS", "").strip()
    _cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()] if _cors_raw else []
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    # 3) Security-Header auf jede Response
    @app.middleware("http")
    async def _security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains",
            )
        return response
    # ---- /Security-Middleware ----

    # ---- Login-Rate-Limit (Issue #68 — Port aus Web-Backend) ----
    import threading as _threading

    app.state.login_lockout_state: dict[str, tuple[int, float]] = {}
    app.state.login_lockout_lock = _threading.Lock()
    app.state.login_max_fails = int(os.environ.get("ND_HUB_LOGIN_MAX_FAILS", "10"))
    app.state.login_lockout_seconds = int(os.environ.get("ND_HUB_LOGIN_LOCKOUT_SECONDS", "900"))
    # ---- /Login-Rate-Limit ----

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
        return {"status": "ok"}

    @app.post("/auth/login", response_model=LoginResponse)
    def login(payload: LoginRequest, request: Request) -> LoginResponse:
        # ---- Login-Lockout (Issue #68) ----
        username = payload.username.strip()
        with app.state.login_lockout_lock:
            _state = app.state.login_lockout_state
            import time as _time
            now = _time.time()
            if username in _state:
                fails, lockout_until = _state[username]
                if lockout_until > now:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Account temporär gesperrt. Bitte später erneut versuchen.",
                    )

        ok, _message = security.authenticate(username, payload.password)
        if not ok:
            # Fehlversuch registrieren
            with app.state.login_lockout_lock:
                import time as _time
                now = _time.time()
                if username in _state:
                    fails, _lockout = _state[username]
                else:
                    fails = 0
                fails += 1
                if fails >= app.state.login_max_fails:
                    _state[username] = (fails, now + app.state.login_lockout_seconds)
                else:
                    _state[username] = (fails, 0.0)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Benutzername oder Passwort ungueltig.",
            )

        # Erfolg → Lockout-Counter zurücksetzen
        with app.state.login_lockout_lock:
            _state.pop(username, None)

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

    # ---- Shared routers (Issues #60/#61/#65) ----
    from backend.routers.auth import create_auth_router
    from backend.routers.users import create_users_router
    from backend.routers.depots import create_depots_router

    _auth_router = create_auth_router(
        security=security,
        token_store=token_store,
        repository=repository,
        get_current_session=get_current_session,
        bearer_scheme=bearer_scheme,
        password_change_model=PasswordChangeRequest,
        get_user_flags=_get_user_flags,
        get_avatar_path_for_user=_get_avatar_path_for_user,
        enrich_me=None,
    )
    app.include_router(_auth_router)

    _users_router = create_users_router(
        security=security,
        repository=repository,
        require_permission=require_permission,
        normalize_user_row=_normalize_user_row,
        permissions_json_for_storage=_permissions_json_for_storage,
        allowed_user_roles=ALLOWED_USER_ROLES,
        hash_password=SecurityManager.hash_password,
        user_create_model=UserCreateRequest,
        user_update_model=UserUpdateRequest,
        user_password_reset_model=UserPasswordResetRequest,
        include_depot_permissions=False,
    )
    app.include_router(_users_router)

    _depots_router = create_depots_router(
        repository=repository,
        require_permission=require_permission,
        depot_upsert_model=DepotUpsertRequest,
        depot_assignments_update_model=DepotAssignmentsUpdateRequest,
        kontakt_upsert_model=KontaktUpsertRequest,
        ensure_depot_access=None,
        resolve_list_allowed_ids=None,
        include_geo_fields=False,
    )
    app.include_router(_depots_router)

    from backend.routers.praeparate import create_praeparate_router
    from backend.routers.kontakte import create_kontakte_router
    from backend.routers.audit import create_audit_router
    from backend.routers.permissions import create_permissions_router
    from backend.routers.bewegungen import create_bewegungen_router

    app.include_router(
        create_permissions_router(
            get_current_session,
            permission_definitions=PERMISSION_DEFINITIONS,
            default_user_permissions=DEFAULT_USER_PERMISSIONS,
            permission_templates=PERMISSION_TEMPLATES,
        )
    )
    app.include_router(
        create_praeparate_router(
            repository=repository,
            require_permission=require_permission,
            praeparat_upsert_model=PraeparatUpsertRequest,
            include_extended_fields=False,
        )
    )
    app.include_router(
        create_kontakte_router(
            repository=repository,
            require_permission=require_permission,
            kontakt_upsert_model=KontaktUpsertRequest,
        )
    )
    app.include_router(
        create_audit_router(
            repository=repository,
            require_permission=require_permission,
        )
    )
    app.include_router(
        create_bewegungen_router(
            repository=repository,
            require_permission=require_permission,
            bewegung_create_model=BewegungCreateRequest,
            ensure_depot_access=None,
            scoped_requested_ids=None,
            include_advanced_filters=False,
            include_export=False,
            attachments_dir=app.state.attachments_dir,
            build_attachment_target_path=_build_attachment_target_path,
            persist_pdf_upload=_persist_pdf_upload,
            pdf_mime_types=PDF_MIME_TYPES,
        )
    )


    from backend.routers.imports import create_imports_router
    from backend.routers.verfall import create_verfall_router
    from backend.routers.dashboard import create_dashboard_router
    from backend.routers.notifications import create_notifications_router

    app.include_router(
        create_imports_router(
            repository=repository,
            require_permission=require_permission,
            build_import_template=_build_import_template,
            load_import_dataframe=_load_import_dataframe,
            map_import_columns=_map_import_columns,
            analyze_import_dataframe=_analyze_import_dataframe,
            enable_web_features=False,
        )
    )
    app.include_router(
        create_verfall_router(
            repository=repository,
            require_permission=require_permission,
            parse_id_list_csv=_parse_id_list_csv,
            normalize_verfall_thresholds=_normalize_verfall_thresholds,
            enrich_verfall_rows=_enrich_verfall_rows,
            csv_response=_csv_response,
            enable_depot_scope=False,
        )
    )
    app.include_router(
        create_dashboard_router(
            repository=repository,
            require_permission=require_permission,
            normalize_verfall_thresholds=_normalize_verfall_thresholds,
            enrich_verfall_rows=_enrich_verfall_rows,
            enable_depot_scope=False,
        )
    )
    app.include_router(
        create_notifications_router(
            repository=repository,
            require_permission=require_permission,
            normalize_verfall_thresholds=_normalize_verfall_thresholds,
            enrich_verfall_rows=_enrich_verfall_rows,
            enable_depot_scope=False,
        )
    )


    from backend.routers.emails import create_emails_router
    from backend.routers.admin_backup import create_admin_backup_router

    def _close_security():
        nonlocal security
        security.close()

    def _reopen_security():
        nonlocal security, token_store
        security = SecurityManager(database_path)
        app.state.security = security
        token_store = TokenStore()
        app.state.token_store = token_store

    app.include_router(
        create_emails_router(
            repository=repository,
            require_permission=require_permission,
            email_recipient_preview_model=EmailRecipientPreviewRequest,
            email_draft_create_model=EmailDraftCreateRequest,
            enable_web_features=False,
        )
    )
    app.include_router(
        create_admin_backup_router(
            repository=repository,
            require_permission=require_permission,
            backups_dir=backups_dir,
            source_db_path=source_db_path,
            database_path=database_path,
            list_backup_files=_list_backup_files,
            create_backup_snapshot=_create_backup_snapshot,
            auto_backup_hours=auto_backup_hours,
            close_security=_close_security,
            reopen_security=_reopen_security,
            enable_web_features=False,
        )
    )


    from backend.routers.reports import create_reports_router

    app.include_router(
        create_reports_router(
            repository=repository,
            require_permission=require_permission,
            parse_id_list_csv=_parse_id_list_csv,
            csv_response=_csv_response,
            pdf_response=_pdf_response,
            pptx_response=_pptx_response,
            enable_depot_scope=False,
            enable_rich_filenames=False,
            add_months=_add_months,
        )
    )

    # ---- /Shared routers ----

    return app

