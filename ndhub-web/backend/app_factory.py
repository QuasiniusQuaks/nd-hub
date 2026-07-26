"""Application factory for ND-Hub web backend (Issue #60/#61)."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from security_manager import SecurityManager
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request as _StarletteRequest
from starlette.responses import JSONResponse as _JSONResponse

import backend.helpers as _helpers_mod
from backend.auth import SessionInfo, TokenStore, bearer_scheme, get_current_session
from backend.config import (
    resolve_auto_backup_hours,
    resolve_db_engine,
    resolve_dual_write_sqlite,
    resolve_email_delivery_settings,
    resolve_mariadb_settings,
    resolve_max_backup_restore_mb,
    resolve_runtime_paths,
)
from backend.database import SqliteRepository
from backend.helpers import *  # noqa: F403
from backend.helpers import (  # noqa: E402
    _add_months,
    _analyze_import_dataframe,
    _build_attachment_target_path,
    _build_import_execution_fingerprint,
    _build_import_template,
    _build_report_export_filename,
    _create_backup_snapshot,
    _create_mariadb_backup_snapshot,
    _csv_response,
    _email_delivery_missing_config,
    _enrich_verfall_rows,
    _get_avatar_path_for_user,
    _get_user_flags,
    _is_valid_sqlite_file,
    _list_backup_files,
    _load_import_dataframe,
    _map_import_columns,
    _normalize_user_row,
    _normalize_verfall_thresholds,
    _parse_id_list_csv,
    _parse_iso_datetime,
    _pdf_response,
    _permissions_for_role,
    _permissions_json_for_storage,
    _persist_pdf_upload,
    _pptx_response,
    _require_http_scheme,
    _restore_mariadb_backup_payload,
    _run_auto_backup_if_due,
    _run_auto_backup_if_due_mariadb,
    _summarize_import_errors,
    _validate_restore_upload_size,
    _validated_report_date_range,
)
from backend.mariadb_repository import MariaDbRepository

# Re-exports for monkeypatch/tests (backend.app._send_email_via_smtp etc.)
from backend.models import *  # noqa: F403
from backend.models import (  # noqa: E402
    ALL_PERMISSION_KEYS,
    ALLOWED_USER_ROLES,
    DEFAULT_USER_PERMISSIONS,
    PDF_MIME_TYPES,
    PERMISSION_DEFINITIONS,
    PERMISSION_TEMPLATES,
    BewegungCreateRequest,
    DepotAssignmentsUpdateRequest,
    DepotUpsertRequest,
    DesktopSyncTokenArchiveItem,
    DesktopSyncTokenCreateRequest,
    DesktopSyncTokenResponse,
    DesktopSyncTokenRevokeRequest,
    EmailDeliveryStatusUpdateRequest,
    EmailDraftCreateRequest,
    EmailRecipientPreviewRequest,
    InstitutionUpsertRequest,
    KontaktUpsertRequest,
    LoginRequest,
    LoginResponse,
    OnboardingInstitutionSetupRequest,
    PasswordChangeRequest,
    PraeparatUpsertRequest,
    SyncPullRequest,
    SyncPushChangeItem,
    SyncPushRequest,
    UserCreateRequest,
    UserDepotPermissionUpdateRequest,
    UserPasswordResetRequest,
    UserUpdateRequest,
)


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
    feature_multi_institution = (os.environ.get("ND_HUB_FEATURE_MULTI_INSTITUTION", "1") or "1").strip().lower() in {"1", "true", "yes", "on"}
    feature_institution_map = (os.environ.get("ND_HUB_FEATURE_INSTITUTION_MAP", "1") or "1").strip().lower() in {"1", "true", "yes", "on"}
    sqlite_fallback_repository = SqliteRepository(database_path)
    if db_engine == "mariadb":
        repository = MariaDbRepository(
            settings=resolve_mariadb_settings(),
            fallback=sqlite_fallback_repository,
            dual_write_sqlite=resolve_dual_write_sqlite(default=True),
        )
    else:
        repository = sqlite_fallback_repository
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
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mindestens ein Depot ist nicht freigegeben.")
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
                # Auto backup should never block startup.
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

    # ---- Security-Middleware (Fix für #31) ----
    # 1) TrustedHost: blockiert Requests mit unbekanntem Host-Header
    #    (verhindert Host-Header-Injection / Cache-Poisoning).
    #    Default ["*"] = alle Hosts; produktiv bitte ND_HUB_ALLOWED_HOSTS setzen.
    _allowed_hosts_raw = os.environ.get("ND_HUB_ALLOWED_HOSTS", "*").strip()
    if _allowed_hosts_raw == "*":
        _allowed_hosts = ["*"]
    else:
        _allowed_hosts = [h.strip() for h in _allowed_hosts_raw.split(",") if h.strip()]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=_allowed_hosts)

    # 2) CORS: restriktiver Default (allow_origins=[]). Cross-Origin nur
    #    explizit via ND_HUB_CORS_ORIGINS (Komma-getrennte Allowlist).
    _cors_raw = os.environ.get("ND_HUB_CORS_ORIGINS", "").strip()
    _cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()] if _cors_raw else []
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    # 3) Security-Header-Middleware: schraubt Standard-Schutz-Header auf
    #    jede Response. HSTS nur bei HTTPS-Request, damit Dev über HTTP ok bleibt.
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

    # ---- Login-Rate-Limit (Fix für #32) ----
    # Per-IP via slowapi (ENV-konfigurierbar; Default 5/min).
    # Per-Username-Lockout: 10 Fehlversuche -> 15 min Sperre (ENV-konfigurierbar).
    # Audit-Log-Eintrag bei Lockout.
    _login_ip_limit = os.environ.get("ND_HUB_LOGIN_IP_LIMIT", "5/minute")
    _login_max_fails = int(os.environ.get("ND_HUB_LOGIN_MAX_FAILS", "10"))
    _login_lockout_seconds = int(os.environ.get("ND_HUB_LOGIN_LOCKOUT_SECONDS", "900"))

    login_limiter = Limiter(key_func=get_remote_address, default_limits=[_login_ip_limit])
    app.state.login_limiter = login_limiter

    # Per-Username-Lockout-Tracker auf app.state (statt closure-lokal),
    # damit er pro App-Instanz eindeutig ist und von Tests verifiziert werden kann.
    # Struktur: {username: (fails, lockout_until_epoch)}
    # In-Memory (Single-Instance). Thread-safe via Lock.
    import threading as _threading
    app.state.login_lockout_state = {}
    app.state.login_lockout_lock = _threading.Lock()
    app.state.login_max_fails = _login_max_fails
    app.state.login_lockout_seconds = _login_lockout_seconds

    def _check_login_lockout(username: str) -> int | None:
        """Returnt verbleibende Sekunden, wenn locked; sonst None."""
        with app.state.login_lockout_lock:
            entry = app.state.login_lockout_state.get(username)
            if not entry:
                return None
            fails, lockout_until = entry
            # Eintraege mit unendlicher Ablaufzeit sind reine Counter
            # (noch nicht max_fails erreicht) und sperren nicht.
            if lockout_until == float("inf"):
                return None
            now = datetime.now().timestamp()
            if lockout_until > now:
                return int(lockout_until - now)
            # Lockout abgelaufen — Counter zuruecksetzen
            app.state.login_lockout_state.pop(username, None)
            return None

    def _record_login_failure(username: str) -> int | None:
        """Verzeichnet einen Fehlversuch. Returnt lockout-Restsekunden, wenn Lockout ausgeloest."""
        with app.state.login_lockout_lock:
            state = app.state.login_lockout_state
            entry = state.get(username)
            if entry is None:
                fails, lockout_until = 0, 0.0
            else:
                fails, lockout_until = entry
            fails += 1
            if fails >= app.state.login_max_fails:
                lockout_until = datetime.now().timestamp() + app.state.login_lockout_seconds
                state[username] = (fails, lockout_until)
                return app.state.login_lockout_seconds
            # Counter-Eintrag ohne aktiven Lockout: Ablaufzeit auf 'unendlich'
            # setzen, damit _check_login_lockout ihn nicht als 'abgelaufen'
            # verwirft, bevor max_fails erreicht ist.
            state[username] = (fails, float("inf"))
            return None

    def _clear_login_lockout(username: str) -> None:
        with app.state.login_lockout_lock:
            app.state.login_lockout_state.pop(username, None)

    def _audit_login_lockout(username: str, ip: str) -> None:
        """Audit-Log-Eintrag bei Lockout. Best-effort, kein Raise bei Fehler."""
        try:
            security.log_activity(
                user_id=0,
                username=username,
                action="login_lockout",
                details=f"ip={ip} max_fails={app.state.login_max_fails} lockout_seconds={app.state.login_lockout_seconds}",
                ip=ip,
            )
        except Exception:
            logger.warning("Audit-Log fuer login_lockout fehlgeschlagen", exc_info=True)

    # slowapi-Exception-Handler: 429 + Retry-After-Header bei IP-Limit
    async def _rate_limit_handler(_request: _StarletteRequest, exc: RateLimitExceeded):
        # Retry-After aus slowapi-Limit-Strategie ableiten
        retry_after = 60  # Default-Fallback
        try:
            # slowapi speichert Limit in exc.limit, Detail in exc.detail
            if hasattr(exc, "limit") and exc.limit and hasattr(exc.limit, "seconds"):
                retry_after = exc.limit.seconds
        except Exception:
            logger.exception("Unexpected error in endpoint")
        return _JSONResponse(
            status_code=429,
            content={"detail": f"Zu viele Login-Versuche. Bitte {retry_after}s warten."},
            headers={"Retry-After": str(retry_after)},
        )

    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
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
        return {"status": "ok", "db_engine": str(app.state.db_engine)}

    @app.post("/auth/login", response_model=LoginResponse)
    @login_limiter.limit(_login_ip_limit)
    def login(payload: LoginRequest, request: Request) -> LoginResponse:
        # Fix #32: per-Username-Lockout pruefen BEVOR authenticate() laeuft
        # (verhindert, dass PBKDF2-CPU-Zeit verschwendet wird, waehrend locked)
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
                # Lockout frisch ausgeloest
                _audit_login_lockout(username_attempt, request.client.host if request.client else "unknown")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Account gesperrt nach {app.state.login_max_fails} Fehlversuchen. "
                           f"Bitte {lockout_seconds}s warten.",
                    headers={"Retry-After": str(lockout_seconds)},
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Benutzername oder Passwort ungueltig.",
            )
        # Erfolgreich: Lockout-Counter zuruecksetzen
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


    # ---- Web-only domain routers (Issue #60) ----
    from backend.routers.desktop_sync_auth import create_desktop_sync_auth_router
    from backend.routers.institutions import create_institutions_router
    from backend.routers.sync import create_sync_router

    app.include_router(
        create_desktop_sync_auth_router(
            token_store=token_store,
            get_current_session=get_current_session,
            DesktopSyncTokenResponse=DesktopSyncTokenResponse,
            DesktopSyncTokenCreateRequest=DesktopSyncTokenCreateRequest,
            DesktopSyncTokenArchiveItem=DesktopSyncTokenArchiveItem,
            DesktopSyncTokenRevokeRequest=DesktopSyncTokenRevokeRequest,
            _parse_iso_datetime=_parse_iso_datetime,
            _mask_token=_mask_token,
            _resolve_archive_status=_resolve_archive_status,
        )
    )
    app.include_router(
        create_institutions_router(
            app=app,
            repository=repository,
            require_permission=require_permission,
            get_current_session=get_current_session,
            OnboardingInstitutionSetupRequest=OnboardingInstitutionSetupRequest,
            InstitutionUpsertRequest=InstitutionUpsertRequest,
            _allowed_depot_ids=_allowed_depot_ids,
            _require_http_scheme=_require_http_scheme,
        )
    )
    app.include_router(
        create_sync_router(
            repository=repository,
            require_permission=require_permission,
            get_current_session=get_current_session,
            SyncPushRequest=SyncPushRequest,
            SyncPushChangeItem=SyncPushChangeItem,
            SyncPullRequest=SyncPullRequest,
            _allowed_depot_ids=_allowed_depot_ids,
            _user_permissions=_user_permissions,
        )
    )
    # ---- /Web-only domain routers ----

    # ---- Shared routers (Issues #60/#61/#65) ----
    from backend.routers.auth import create_auth_router
    from backend.routers.depots import create_depots_router
    from backend.routers.users import create_users_router

    def _enrich_auth_me(session: SessionInfo) -> dict:
        depot_permissions = _allowed_depot_permissions(session)
        return {
            "depot_permissions": [
                {"depot_id": depot_id, **rights}
                for depot_id, rights in sorted(depot_permissions.items())
            ],
        }

    _auth_router = create_auth_router(
        security=security,
        token_store=token_store,
        repository=repository,
        get_current_session=get_current_session,
        bearer_scheme=bearer_scheme,
        password_change_model=PasswordChangeRequest,
        get_user_flags=_get_user_flags,
        get_avatar_path_for_user=_get_avatar_path_for_user,
        enrich_me=_enrich_auth_me,
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
        include_depot_permissions=True,
        user_depot_permission_update_model=UserDepotPermissionUpdateRequest,
        is_multi_institution=lambda: bool(app.state.feature_multi_institution),
    )
    app.include_router(_users_router)

    _depots_router = create_depots_router(
        repository=repository,
        require_permission=require_permission,
        depot_upsert_model=DepotUpsertRequest,
        depot_assignments_update_model=DepotAssignmentsUpdateRequest,
        kontakt_upsert_model=KontaktUpsertRequest,
        ensure_depot_access=_ensure_depot_access,
        resolve_list_allowed_ids=lambda session: (
            list(_allowed_depot_permissions(session).keys()) if session.role != "Admin" else None
        ),
        include_geo_fields=True,
    )
    app.include_router(_depots_router)

    from backend.routers.audit import create_audit_router
    from backend.routers.bewegungen import create_bewegungen_router
    from backend.routers.kontakte import create_kontakte_router
    from backend.routers.permissions import create_permissions_router
    from backend.routers.praeparate import create_praeparate_router

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
            include_extended_fields=True,
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
            ensure_depot_access=_ensure_depot_access,
            scoped_requested_ids=_scoped_requested_ids,
            include_advanced_filters=True,
            include_export=True,
            csv_response=_csv_response,
            attachments_dir=app.state.attachments_dir,
            build_attachment_target_path=_build_attachment_target_path,
            persist_pdf_upload=_persist_pdf_upload,
            pdf_mime_types=PDF_MIME_TYPES,
        )
    )


    from backend.routers.dashboard import create_dashboard_router
    from backend.routers.imports import create_imports_router
    from backend.routers.notifications import create_notifications_router
    from backend.routers.verfall import create_verfall_router

    app.include_router(
        create_imports_router(
            repository=repository,
            require_permission=require_permission,
            build_import_template=_build_import_template,
            load_import_dataframe=_load_import_dataframe,
            map_import_columns=_map_import_columns,
            analyze_import_dataframe=_analyze_import_dataframe,
            enable_web_features=True,
            summarize_import_errors=_summarize_import_errors,
            build_import_execution_fingerprint=_build_import_execution_fingerprint,
            allowed_depot_ids=_allowed_depot_ids,
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
            enable_depot_scope=True,
            allowed_depot_ids=_allowed_depot_ids,
            scoped_requested_ids=_scoped_requested_ids,
        )
    )
    app.include_router(
        create_dashboard_router(
            repository=repository,
            require_permission=require_permission,
            normalize_verfall_thresholds=_normalize_verfall_thresholds,
            enrich_verfall_rows=_enrich_verfall_rows,
            enable_depot_scope=True,
            allowed_depot_ids=_allowed_depot_ids,
        )
    )
    app.include_router(
        create_notifications_router(
            repository=repository,
            require_permission=require_permission,
            normalize_verfall_thresholds=_normalize_verfall_thresholds,
            enrich_verfall_rows=_enrich_verfall_rows,
            enable_depot_scope=True,
            allowed_depot_ids=_allowed_depot_ids,
        )
    )


    from backend.routers.admin_backup import create_admin_backup_router
    from backend.routers.emails import create_emails_router

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
            enable_web_features=True,
            email_delivery_status_update_model=EmailDeliveryStatusUpdateRequest,
            get_email_delivery_settings=lambda: app.state.email_delivery_settings,
            email_delivery_missing_config=_email_delivery_missing_config,
            send_email_via_smtp=lambda *args, **kwargs: _helpers_mod._send_email_via_smtp(*args, **kwargs),
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
            enable_web_features=True,
            db_engine=db_engine,
            max_restore_size_mb=max_backup_restore_mb,
            max_backup_restore_bytes=max_backup_restore_bytes,
            create_mariadb_backup_snapshot=_create_mariadb_backup_snapshot,
            validate_restore_upload_size=_validate_restore_upload_size,
            restore_mariadb_backup_payload=_restore_mariadb_backup_payload,
            is_valid_sqlite_file=_is_valid_sqlite_file,
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
            enable_depot_scope=True,
            enable_rich_filenames=True,
            scoped_requested_ids=_scoped_requested_ids,
            allowed_depot_ids=_allowed_depot_ids,
            validated_report_date_range=_validated_report_date_range,
            build_report_export_filename=_build_report_export_filename,
            add_months=_add_months,
        )
    )

    # ---- /Shared routers ----

    return app

