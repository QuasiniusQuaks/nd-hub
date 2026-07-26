"""Domain helpers for ND-Hub web backend (Issue #96)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


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

from security_manager import SecurityManager

from backend.models import (
    ALL_PERMISSION_KEYS,
    DEFAULT_USER_PERMISSIONS,
)


def _parse_permission_list(raw_permissions: object) -> set[str]:
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
        if key in ALL_PERMISSION_KEYS:
            result.add(key)
    return result

def _permissions_for_role(role: str | None, raw_permissions: object) -> set[str]:
    if role == "Admin":
        return set(ALL_PERMISSION_KEYS)
    parsed = _parse_permission_list(raw_permissions)
    return parsed or set(DEFAULT_USER_PERMISSIONS)

def _permissions_json_for_storage(role: str, requested: list[str] | None) -> str:
    allowed = _permissions_for_role(role, requested)
    return json.dumps(sorted(allowed), ensure_ascii=True)

def _normalize_user_row(row: tuple) -> dict:
    effective_permissions = sorted(_permissions_for_role(str(row[2]), row[10] if len(row) > 10 else None))
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

def _get_user_flags(security: SecurityManager, username: str) -> dict[str, bool]:
    row = security.cur.execute(
        "SELECT is_default_password, role, permissions FROM users WHERE username = ?",
        ((username or "").strip(),),
    ).fetchone()
    if not row:
        return {"requires_password_change": False, "permissions": sorted(DEFAULT_USER_PERMISSIONS)}  # nosec B105: boolean flag, not a password
    return {
        "requires_password_change": bool(row[0]),
        "permissions": sorted(_permissions_for_role(str(row[1]), row[2])),
    }

def _get_avatar_path_for_user(security: SecurityManager, username: str) -> Path | None:
    row = security.cur.execute(
        "SELECT avatar_path FROM users WHERE username = ?",
        ((username or "").strip(),),
    ).fetchone()
    if not row or not row[0]:
        return None
    avatar_path = Path(str(row[0])).expanduser()
    if not avatar_path.exists() or not avatar_path.is_file():
        return None
    return avatar_path

