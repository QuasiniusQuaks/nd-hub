"""Authz helpers for ND-Hub web backend (Issue #96/#94)."""

from __future__ import annotations

from pathlib import Path

from security_manager import SecurityManager

from backend.models import ALL_PERMISSION_KEYS, DEFAULT_USER_PERMISSIONS
from shared.backend_helpers.common import (
    normalize_user_row,
    parse_permission_list,
    permissions_for_role,
    permissions_json_for_storage,
)


def _parse_permission_list(raw_permissions: object) -> set[str]:
    return parse_permission_list(raw_permissions, ALL_PERMISSION_KEYS)


def _permissions_for_role(role: str | None, raw_permissions: object) -> set[str]:
    return permissions_for_role(
        role,
        raw_permissions,
        allowed_keys=ALL_PERMISSION_KEYS,
        default_permissions=DEFAULT_USER_PERMISSIONS,
    )


def _permissions_json_for_storage(role: str, requested: list[str] | None) -> str:
    return permissions_json_for_storage(
        role,
        requested,
        allowed_keys=ALL_PERMISSION_KEYS,
        default_permissions=DEFAULT_USER_PERMISSIONS,
    )


def _normalize_user_row(row: tuple) -> dict:
    return normalize_user_row(
        row,
        allowed_keys=ALL_PERMISSION_KEYS,
        default_permissions=DEFAULT_USER_PERMISSIONS,
    )


def _get_user_flags(security: SecurityManager, username: str) -> dict[str, bool]:
    row = security.cur.execute(
        "SELECT is_default_password, role, permissions FROM users WHERE username = ?",
        ((username or "").strip(),),
    ).fetchone()
    if not row:
        return {
            "requires_password_change": False,
            "permissions": sorted(DEFAULT_USER_PERMISSIONS),
        }  # nosec B105: boolean flag, not a password
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
