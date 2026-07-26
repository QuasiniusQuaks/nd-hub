"""Helper functions for ND-Hub web backend (Issue #60/#96).

Thin facade: domain modules live in helper_*.py. Import from backend.helpers
remains the stable public surface (tests monkeypatch this module).
"""

from __future__ import annotations

from backend.helper_authz import (
    _get_avatar_path_for_user,
    _get_user_flags,
    _normalize_user_row,
    _parse_permission_list,
    _permissions_for_role,
    _permissions_json_for_storage,
)
from backend.helper_backup import (
    _create_backup_snapshot,
    _create_mariadb_backup_snapshot,
    _is_valid_sqlite_file,
    _list_backup_files,
    _read_upload_size_bytes,
    _restore_mariadb_backup_payload,
    _run_auto_backup_if_due,
    _run_auto_backup_if_due_mariadb,
    _validate_restore_upload_size,
)
from backend.helper_common import (
    _add_months,
    _normalize_json_value,
    _parse_id_list_csv,
    _parse_iso_datetime,
    _parse_optional_iso_date,
    _quote_sql_identifier,
    _require_http_scheme,
    _safe_backup_label,
    _safe_report_filename_token,
    _sanitize_filename_part,
)
from backend.helper_email import (
    _email_delivery_missing_config,
    _send_email_via_smtp,
)
from backend.helper_import import (
    _analyze_import_dataframe,
    _build_attachment_target_path,
    _build_import_execution_fingerprint,
    _build_import_template,
    _classify_import_error_code,
    _ensure_import_dependencies,
    _load_import_dataframe,
    _map_import_columns,
    _normalize_import_column_name,
    _parse_import_date,
    _persist_pdf_upload,
    _summarize_import_errors,
)
from backend.helper_report import (
    _build_report_export_filename,
    _csv_response,
    _enrich_verfall_rows,
    _normalize_verfall_thresholds,
    _pdf_response,
    _pptx_response,
    _validated_report_date_range,
    _verfall_category,
)

__all__ = [
    "_require_http_scheme",
    "_email_delivery_missing_config",
    "_send_email_via_smtp",
    "_sanitize_filename_part",
    "_quote_sql_identifier",
    "_build_attachment_target_path",
    "_persist_pdf_upload",
    "_normalize_import_column_name",
    "_parse_id_list_csv",
    "_add_months",
    "_normalize_verfall_thresholds",
    "_verfall_category",
    "_enrich_verfall_rows",
    "_ensure_import_dependencies",
    "_load_import_dataframe",
    "_map_import_columns",
    "_analyze_import_dataframe",
    "_parse_import_date",
    "_parse_optional_iso_date",
    "_validated_report_date_range",
    "_safe_report_filename_token",
    "_build_report_export_filename",
    "_build_import_execution_fingerprint",
    "_classify_import_error_code",
    "_summarize_import_errors",
    "_build_import_template",
    "_csv_response",
    "_pdf_response",
    "_pptx_response",
    "_parse_permission_list",
    "_permissions_for_role",
    "_permissions_json_for_storage",
    "_normalize_user_row",
    "_get_user_flags",
    "_get_avatar_path_for_user",
    "_safe_backup_label",
    "_normalize_json_value",
    "_parse_iso_datetime",
    "_create_backup_snapshot",
    "_create_mariadb_backup_snapshot",
    "_list_backup_files",
    "_run_auto_backup_if_due",
    "_run_auto_backup_if_due_mariadb",
    "_restore_mariadb_backup_payload",
    "_read_upload_size_bytes",
    "_validate_restore_upload_size",
    "_is_valid_sqlite_file",
]
