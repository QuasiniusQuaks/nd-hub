"""Router registration for ND-Hub web backend (Issue #96)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from security_manager import SecurityManager

import backend.helpers as _helpers_mod
from backend.auth import SessionInfo, get_current_session
from backend.helpers import (
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
    _permissions_json_for_storage,
    _persist_pdf_upload,
    _pptx_response,
    _require_http_scheme,
    _restore_mariadb_backup_payload,
    _summarize_import_errors,
    _validate_restore_upload_size,
    _validated_report_date_range,
)
from backend.models import (
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


def _register_web_only_routers(
    app: Any,
    *,
    token_store: Any,
    repository: Any,
    require_permission: Callable,
    mask_token: Callable[[str], str],
    resolve_archive_status: Callable[[datetime | None, datetime | None, str], str],
    allowed_depot_ids: Callable,
    user_permissions: Callable,
) -> None:
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
            _mask_token=mask_token,
            _resolve_archive_status=resolve_archive_status,
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
            _allowed_depot_ids=allowed_depot_ids,
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
            _allowed_depot_ids=allowed_depot_ids,
            _user_permissions=user_permissions,
        )
    )


def _register_shared_routers(
    app: Any,
    *,
    security: Any,
    token_store: Any,
    repository: Any,
    require_permission: Callable,
    source_db_path: Path,
    backups_dir: Path,
    auto_backup_hours: int,
    max_backup_restore_mb: int,
    max_backup_restore_bytes: int,
    db_engine: str,
    database_path: str,
    close_security: Callable[[], None],
    reopen_security: Callable[[], None],
    allowed_depot_permissions: Callable[[SessionInfo], dict[int, dict[str, bool]]],
    ensure_depot_access: Callable,
    scoped_requested_ids: Callable,
    allowed_depot_ids: Callable,
) -> None:
    from backend.auth import bearer_scheme
    from backend.routers.admin_backup import create_admin_backup_router
    from backend.routers.audit import create_audit_router
    from backend.routers.auth import create_auth_router
    from backend.routers.bewegungen import create_bewegungen_router
    from backend.routers.dashboard import create_dashboard_router
    from backend.routers.depots import create_depots_router
    from backend.routers.emails import create_emails_router
    from backend.routers.imports import create_imports_router
    from backend.routers.kontakte import create_kontakte_router
    from backend.routers.notifications import create_notifications_router
    from backend.routers.permissions import create_permissions_router
    from backend.routers.praeparate import create_praeparate_router
    from backend.routers.reports import create_reports_router
    from backend.routers.users import create_users_router
    from backend.routers.verfall import create_verfall_router

    def _enrich_auth_me(session: SessionInfo) -> dict:
        depot_permissions = allowed_depot_permissions(session)
        return {
            "depot_permissions": [
                {"depot_id": depot_id, **rights}
                for depot_id, rights in sorted(depot_permissions.items())
            ],
        }

    app.include_router(
        create_auth_router(
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
    )
    app.include_router(
        create_users_router(
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
    )
    app.include_router(
        create_depots_router(
            repository=repository,
            require_permission=require_permission,
            depot_upsert_model=DepotUpsertRequest,
            depot_assignments_update_model=DepotAssignmentsUpdateRequest,
            kontakt_upsert_model=KontaktUpsertRequest,
            ensure_depot_access=ensure_depot_access,
            resolve_list_allowed_ids=lambda session: (
                list(allowed_depot_permissions(session).keys()) if session.role != "Admin" else None
            ),
            include_geo_fields=True,
        )
    )
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
            ensure_depot_access=ensure_depot_access,
            scoped_requested_ids=scoped_requested_ids,
            include_advanced_filters=True,
            include_export=True,
            csv_response=_csv_response,
            attachments_dir=app.state.attachments_dir,
            build_attachment_target_path=_build_attachment_target_path,
            persist_pdf_upload=_persist_pdf_upload,
            pdf_mime_types=PDF_MIME_TYPES,
        )
    )
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
            allowed_depot_ids=allowed_depot_ids,
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
            allowed_depot_ids=allowed_depot_ids,
            scoped_requested_ids=scoped_requested_ids,
        )
    )
    app.include_router(
        create_dashboard_router(
            repository=repository,
            require_permission=require_permission,
            normalize_verfall_thresholds=_normalize_verfall_thresholds,
            enrich_verfall_rows=_enrich_verfall_rows,
            enable_depot_scope=True,
            allowed_depot_ids=allowed_depot_ids,
        )
    )
    app.include_router(
        create_notifications_router(
            repository=repository,
            require_permission=require_permission,
            normalize_verfall_thresholds=_normalize_verfall_thresholds,
            enrich_verfall_rows=_enrich_verfall_rows,
            enable_depot_scope=True,
            allowed_depot_ids=allowed_depot_ids,
        )
    )

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
            close_security=close_security,
            reopen_security=reopen_security,
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
            scoped_requested_ids=scoped_requested_ids,
            allowed_depot_ids=allowed_depot_ids,
            validated_report_date_range=_validated_report_date_range,
            build_report_export_filename=_build_report_export_filename,
            add_months=_add_months,
        )
    )


def register_all_routers(
    app: Any,
    *,
    security: Any,
    token_store: Any,
    repository: Any,
    require_permission: Callable,
    database_path: str,
    source_db_path: Path,
    backups_dir: Path,
    auto_backup_hours: int,
    max_backup_restore_mb: int,
    max_backup_restore_bytes: int,
    db_engine: str,
    close_security: Callable[[], None],
    reopen_security: Callable[[], None],
    mask_token: Callable[[str], str],
    resolve_archive_status: Callable[[datetime | None, datetime | None, str], str],
    allowed_depot_permissions: Callable[[SessionInfo], dict[int, dict[str, bool]]],
    ensure_depot_access: Callable,
    scoped_requested_ids: Callable,
    allowed_depot_ids: Callable,
    user_permissions: Callable,
) -> None:
    """Mount web-only + shared domain routers (OpenAPI path parity target)."""
    _register_web_only_routers(
        app,
        token_store=token_store,
        repository=repository,
        require_permission=require_permission,
        mask_token=mask_token,
        resolve_archive_status=resolve_archive_status,
        allowed_depot_ids=allowed_depot_ids,
        user_permissions=user_permissions,
    )
    _register_shared_routers(
        app,
        security=security,
        token_store=token_store,
        repository=repository,
        require_permission=require_permission,
        source_db_path=source_db_path,
        backups_dir=backups_dir,
        auto_backup_hours=auto_backup_hours,
        max_backup_restore_mb=max_backup_restore_mb,
        max_backup_restore_bytes=max_backup_restore_bytes,
        db_engine=db_engine,
        database_path=database_path,
        close_security=close_security,
        reopen_security=reopen_security,
        allowed_depot_permissions=allowed_depot_permissions,
        ensure_depot_access=ensure_depot_access,
        scoped_requested_ids=scoped_requested_ids,
        allowed_depot_ids=allowed_depot_ids,
    )
