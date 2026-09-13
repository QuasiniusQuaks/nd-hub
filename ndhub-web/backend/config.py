"""Backend configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from shared.security.runtime_secrets import require_runtime_secret


def _read_env_str(name: str, default: str = "") -> str:
    return (os.environ.get(name, default) or "").strip()


def _read_env_int(name: str, default: int) -> int:
    raw = _read_env_str(name, str(default))
    try:
        return int(raw)
    except ValueError:
        return default


def _read_env_bool(name: str, default: bool) -> bool:
    raw = _read_env_str(name, "1" if default else "0").lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def resolve_db_path() -> str:
    """Resolve database path for backend usage."""
    env_path = _read_env_str("ND_HUB_DB_PATH")
    if env_path:
        return env_path

    # For the first solo migration step we keep backend data local to the project
    # unless explicitly overridden via ND_HUB_DB_PATH.
    return os.path.abspath("nd_hub_backend.db")


@dataclass(frozen=True)
class RuntimePaths:
    """Resolved filesystem paths used by the backend runtime."""

    database_path: Path
    attachments_dir: Path
    backups_dir: Path


@dataclass(frozen=True)
class MariaDbSettings:
    """MariaDB connection settings from environment."""

    host: str
    port: int
    database: str
    user: str
    password: str


@dataclass(frozen=True)
class EmailDeliverySettings:
    """Optional runtime settings for real e-mail delivery."""

    mode: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool
    smtp_use_ssl: bool
    smtp_from_address: str
    smtp_from_name: str
    smtp_timeout_seconds: int


def resolve_runtime_paths(db_path: str | None = None) -> RuntimePaths:
    """Resolve runtime paths with optional environment overrides."""
    database_path = Path(db_path or resolve_db_path()).resolve()
    default_base = database_path.parent

    attachments_override = _read_env_str("ND_HUB_ATTACHMENTS_DIR")
    backups_override = _read_env_str("ND_HUB_BACKUPS_DIR")
    attachments_dir = Path(attachments_override).expanduser().resolve() if attachments_override else (default_base / "attachments")
    backups_dir = Path(backups_override).expanduser().resolve() if backups_override else (default_base / "backups")
    return RuntimePaths(
        database_path=database_path,
        attachments_dir=attachments_dir,
        backups_dir=backups_dir,
    )


def resolve_auto_backup_hours(default: int = 24) -> int:
    """Resolve and sanitize backup interval hours."""
    value = _read_env_int("ND_HUB_AUTO_BACKUP_HOURS", default)
    return max(1, value)


def resolve_max_backup_restore_mb(default: int = 200) -> int:
    """Resolve maximum backup restore upload size in MB."""
    value = _read_env_int("ND_HUB_MAX_BACKUP_RESTORE_MB", default)
    return max(1, min(value, 2048))


def resolve_db_engine(default: str = "sqlite") -> str:
    """Resolve storage engine setting."""
    value = _read_env_str("ND_HUB_DB_ENGINE", default).lower()
    if value in {"sqlite", "mariadb"}:
        return value
    return default


def resolve_mariadb_settings() -> MariaDbSettings:
    """Resolve MariaDB settings used by migration scripts/runtime checks.

    Empty passwords and documented placeholders such as ``__CHANGE_ME__``
    are rejected (Issues #104 #142). There is no fallback secret.
    """
    password = require_runtime_secret(
        "ND_HUB_MARIADB_PASSWORD",
        _read_env_str("ND_HUB_MARIADB_PASSWORD", ""),
    )
    root = _read_env_str("ND_HUB_MARIADB_ROOT_PASSWORD", "")
    if root:
        require_runtime_secret("ND_HUB_MARIADB_ROOT_PASSWORD", root)
    return MariaDbSettings(
        host=_read_env_str("ND_HUB_MARIADB_HOST", "mariadb"),
        port=max(1, _read_env_int("ND_HUB_MARIADB_PORT", 3306)),
        database=_read_env_str("ND_HUB_MARIADB_DATABASE", "ndhub"),
        user=_read_env_str("ND_HUB_MARIADB_USER", "ndhub"),
        password=password,
    )


def resolve_dual_write_sqlite(default: bool = True) -> bool:
    """Resolve whether MariaDB mode mirrors writes to SQLite fallback."""
    return _read_env_bool("ND_HUB_DUAL_WRITE_SQLITE", default)


def resolve_email_delivery_settings(default_mode: str = "draft") -> EmailDeliverySettings:
    """Resolve optional e-mail delivery settings."""
    mode = _read_env_str("ND_HUB_EMAIL_DELIVERY_MODE", default_mode).lower()
    if mode not in {"draft", "smtp"}:
        mode = default_mode
    return EmailDeliverySettings(
        mode=mode,
        smtp_host=_read_env_str("ND_HUB_SMTP_HOST"),
        smtp_port=max(1, _read_env_int("ND_HUB_SMTP_PORT", 587)),
        smtp_username=_read_env_str("ND_HUB_SMTP_USERNAME"),
        smtp_password=_read_env_str("ND_HUB_SMTP_PASSWORD"),
        smtp_use_tls=_read_env_bool("ND_HUB_SMTP_USE_TLS", True),
        smtp_use_ssl=_read_env_bool("ND_HUB_SMTP_USE_SSL", False),
        smtp_from_address=_read_env_str("ND_HUB_SMTP_FROM_ADDRESS"),
        smtp_from_name=_read_env_str("ND_HUB_SMTP_FROM_NAME"),
        smtp_timeout_seconds=max(3, _read_env_int("ND_HUB_SMTP_TIMEOUT_SECONDS", 10)),
    )

