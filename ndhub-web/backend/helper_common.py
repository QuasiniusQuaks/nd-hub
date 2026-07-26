"""Domain helpers for ND-Hub web backend (Issue #96/#94).

Pure utilities live in ``shared.backend_helpers``; this module re-exports
historical ``_``-prefixed names for factory/router imports.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from urllib.parse import urlparse

from fastapi import HTTPException, status

from shared.backend_helpers.common import (
    add_months,
    parse_id_list_csv,
    safe_backup_label,
    safe_report_filename_token,
    sanitize_filename_part,
)


def _require_http_scheme(url: str) -> str:
    """Validates that the URL uses only http/https (SSRF protection)."""
    scheme = urlparse(url).scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError(f"URL scheme not allowed: {url}")
    return url


def _sanitize_filename_part(value: str) -> str:
    return sanitize_filename_part(value)


def _quote_sql_identifier(name: str) -> str:
    """Quote and validate a SQL identifier (table/column name)."""
    import re

    if not name or not re.fullmatch(r"[A-Za-z0-9_]+", name):
        raise ValueError(f"Ungueltiger SQL-Bezeichner: {name!r}")
    return f"`{name}`"


def _parse_id_list_csv(value: str) -> list[int]:
    return parse_id_list_csv(value)


def _add_months(iso_date: date, months: int) -> date:
    return add_months(iso_date, months)


def _parse_optional_iso_date(value: str, field_name: str) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} muss YYYY-MM-DD sein.",
        ) from exc


def _parse_iso_datetime(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _normalize_json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _safe_backup_label(value: str) -> str:
    return safe_backup_label(value)


def _safe_report_filename_token(value: str) -> str:
    return safe_report_filename_token(value)
