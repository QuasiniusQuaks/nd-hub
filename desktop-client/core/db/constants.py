"""DB-Konstanten (Tabellen- und Setting-Keys). Issue #66.

Aus ``db_manager`` ausgelagert für zirkelfreie Mixin-Imports.
SETTING_*-Aliase: Call-Sites nutzen historisch das Prefix.
"""
from __future__ import annotations

from enum import StrEnum


class TableName(StrEnum):
    """Namen der Datenbank-Tabellen."""
    DEPOTS = "depots"
    KONTAKTE = "kontakte"
    PRAEPARATE = "praeparate"
    DEPOT_PRAEPARATE = "depot_praeparate"
    BEWEGUNGEN = "bewegungen"
    EMAIL_VERLAUF = "email_verlauf"
    EINSTELLUNGEN = "einstellungen"
    TRACKING = "meldungs_tracking"


class SettingKey(StrEnum):
    """Schlüssel für die Anwendungs-Einstellungen (Tabelle ``einstellungen``)."""
    AUTO_BACKUP = "auto_backup"
    SETTING_AUTO_BACKUP = "auto_backup"
    LETZTES_BACKUP = "letztes_backup"
    SETTING_LETZTES_BACKUP = "letztes_backup"
    PASSWORD_HASH = "password_hash"  # gitleaks:allow nosec B105: settings KEY name, not a secret
    SETTING_PASSWORD_HASH = "password_hash"  # gitleaks:allow nosec B105: settings KEY name, not a secret
    MAX_BACKUPS = "max_backups"
    SETTING_MAX_BACKUPS = "max_backups"
    SMTP_HOST = "smtp_host"
    SETTING_SMTP_HOST = "smtp_host"
    SMTP_PORT = "smtp_port"
    SETTING_SMTP_PORT = "smtp_port"
    SMTP_USERNAME = "smtp_username"
    SETTING_SMTP_USERNAME = "smtp_username"
    SMTP_PASSWORD = "smtp_password"  # gitleaks:allow nosec B105: settings KEY name, not a secret
    SETTING_SMTP_PASSWORD = "smtp_password"  # gitleaks:allow nosec B105: settings KEY name, not a secret
    SMTP_USE_TLS = "smtp_use_tls"
    SETTING_SMTP_USE_TLS = "smtp_use_tls"
    SMTP_USE_SSL = "smtp_use_ssl"
    SETTING_SMTP_USE_SSL = "smtp_use_ssl"
    SMTP_FROM_ADDRESS = "smtp_from_address"
    SETTING_SMTP_FROM_ADDRESS = "smtp_from_address"
    SMTP_FROM_NAME = "smtp_from_name"
    SETTING_SMTP_FROM_NAME = "smtp_from_name"
    SETUP_WIZARD_COMPLETED = "setup_wizard_completed"
    SETTING_SETUP_WIZARD_COMPLETED = "setup_wizard_completed"
    SETUP_WIZARD_LAST_STEP = "setup_wizard_last_step"
    SETTING_SETUP_WIZARD_LAST_STEP = "setup_wizard_last_step"
    SETUP_WIZARD_DRAFT = "setup_wizard_draft"
    SETTING_SETUP_WIZARD_DRAFT = "setup_wizard_draft"


# Rückwärtskompatibler Alias (deprecated, wird schrittweise entfernt)
DB = SettingKey
