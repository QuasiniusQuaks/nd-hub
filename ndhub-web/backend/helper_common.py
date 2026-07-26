"""Domain helpers for ND-Hub web backend (Issue #96)."""

from __future__ import annotations

import logging
import re
from datetime import UTC, date, datetime
from decimal import Decimal
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

from fastapi import HTTPException, status

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None
try:
    from openpyxl import Workbook
    from openpyxl.worksheet.datavalidation import DataValidation
except ImportError:  # pragma: no cover
    Workbook = None
    DataValidation = None



def _require_http_scheme(url: str) -> str:
    """Validates that the URL uses only http/https (SSRF protection)."""
    scheme = urlparse(url).scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError(f"URL scheme not allowed: {url}")
    return url

def _sanitize_filename_part(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", value or "")
    return safe.strip("._") or "datei"

def _quote_sql_identifier(name: str) -> str:
    """Quote and validate a SQL identifier (table/column name)."""
    if not name or not re.fullmatch(r"[A-Za-z0-9_]+", name):
        raise ValueError(f"Ungueltiger SQL-Bezeichner: {name!r}")
    return f"`{name}`"

def _parse_id_list_csv(value: str) -> list[int]:
    if not value.strip():
        return []
    result: list[int] = []
    for part in value.split(","):
        item = part.strip()
        if not item:
            continue
        result.append(int(item))
    return result

def _add_months(iso_date: date, months: int) -> date:
    month_index = (iso_date.year * 12 + iso_date.month - 1) + months
    year = month_index // 12
    month = (month_index % 12) + 1
    return date(year, month, 1)

def _parse_optional_iso_date(value: str, field_name: str) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field_name} muss YYYY-MM-DD sein.") from exc

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
    return re.sub(r"[^a-z0-9_-]+", "_", (value or "").strip().lower()) or "manual"

def _safe_report_filename_token(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "_", (value or "").strip().lower()).strip("_") or "report"

