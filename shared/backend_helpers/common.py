"""Pure backend helper functions shared by Desktop + Web (Issue #94).

No FastAPI / framework imports — safe for both stacks. Backend packages
re-export under their historical ``_name`` symbols.
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any


def sanitize_filename_part(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", value or "")
    return safe.strip("._") or "datei"


def parse_id_list_csv(value: str) -> list[int]:
    if not value.strip():
        return []
    result: list[int] = []
    for part in value.split(","):
        item = part.strip()
        if not item:
            continue
        result.append(int(item))
    return result


def add_months(iso_date: date, months: int) -> date:
    month_index = (iso_date.year * 12 + iso_date.month - 1) + months
    year = month_index // 12
    month = (month_index % 12) + 1
    return date(year, month, 1)


def normalize_import_column_name(name: str) -> str:
    lowered = (name or "").strip().lower()
    lowered = (
        lowered.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    lowered = re.sub(r"[^a-z0-9]+", "", lowered)
    return lowered


def normalize_verfall_thresholds(
    critical_days: int = 30,
    warning_days: int = 90,
    attention_days: int = 180,
) -> tuple[int, int, int]:
    critical = max(1, min(int(critical_days), 3650))
    warning = max(critical + 1, min(int(warning_days), 3650))
    attention = max(warning + 1, min(int(attention_days), 3650))
    return critical, warning, attention


def verfall_category(
    tage_bis_verfall: int,
    critical_days: int,
    warning_days: int,
    attention_days: int,
) -> str:
    if tage_bis_verfall <= critical_days:
        return "kritisch"
    if tage_bis_verfall <= warning_days:
        return "warnung"
    if tage_bis_verfall <= attention_days:
        return "achtung"
    return "ok"


def enrich_verfall_rows(
    rows: list[dict[str, Any]],
    critical_days: int,
    warning_days: int,
    attention_days: int,
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        try:
            tage = int(item.get("tage_bis_verfall"))
        except (TypeError, ValueError):
            tage = 99999
        item["tage_bis_verfall"] = tage
        item["kategorie"] = verfall_category(tage, critical_days, warning_days, attention_days)
        enriched.append(item)
    return enriched


def parse_import_date(value: object) -> str | None:
    if value is None:
        return None
    if hasattr(value, "date") and callable(getattr(value, "date", None)):
        try:
            return value.date().isoformat()  # type: ignore[no-any-return]
        except Exception:
            pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "nat"}:
        return None
    # ISO first
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        pass
    # common DE formats
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            from datetime import datetime

            return datetime.strptime(text[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def safe_backup_label(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "_", (value or "").strip().lower()) or "manual"


def safe_report_filename_token(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "_", (value or "").strip().lower()).strip("_") or "report"


def parse_permission_list(raw_permissions: object, allowed_keys: set[str]) -> set[str]:
    if raw_permissions in (None, ""):
        return set()
    if isinstance(raw_permissions, str):
        try:
            parsed = json.loads(raw_permissions)
        except json.JSONDecodeError:
            return set()
    elif isinstance(raw_permissions, (list, tuple, set)):
        parsed = list(raw_permissions)
    else:
        return set()
    result: set[str] = set()
    for item in parsed:
        key = str(item or "").strip()
        if key in allowed_keys:
            result.add(key)
    return result


def permissions_for_role(
    role: str | None,
    raw_permissions: object,
    *,
    allowed_keys: set[str],
    default_permissions: set[str] | list[str],
) -> set[str]:
    if role == "Admin":
        return set(allowed_keys)
    parsed = parse_permission_list(raw_permissions, allowed_keys)
    return parsed or set(default_permissions)


def permissions_json_for_storage(
    role: str,
    requested: list[str] | None,
    *,
    allowed_keys: set[str],
    default_permissions: set[str] | list[str],
) -> str:
    allowed = permissions_for_role(
        role,
        requested,
        allowed_keys=allowed_keys,
        default_permissions=default_permissions,
    )
    return json.dumps(sorted(allowed), ensure_ascii=True)


def normalize_user_row(
    row: tuple,
    *,
    allowed_keys: set[str],
    default_permissions: set[str] | list[str],
) -> dict:
    effective_permissions = sorted(
        permissions_for_role(
            str(row[2]),
            row[10] if len(row) > 10 else None,
            allowed_keys=allowed_keys,
            default_permissions=default_permissions,
        )
    )
    return {
        "id": int(row[0]),
        "username": str(row[1]),
        "role": str(row[2]),
        "email": row[3],
        "created_at": row[4],
        "last_login": row[5],
        "is_active": bool(row[6]),
        "failed_attempts": int(row[7] or 0),
        "locked_until": row[8],
        "is_default_password": bool(row[9]),
        "permissions": effective_permissions,
    }
