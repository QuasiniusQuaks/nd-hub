import configparser
import logging
import os
import sys

logger = logging.getLogger("ND-Hub.Config")

# Lazy-Import, damit Tests ohne installiertes keyring/cryptography funktionieren
_secure_store_cache = {}


def _get_secure_store(data_dir: str):
    """Lazy-Initializer für SecureTokenStore (vermeidet Import auf Modulebene)."""
    if "store" not in _secure_store_cache:
        from core.secure_token_store import SecureTokenStore
        _secure_store_cache["store"] = SecureTokenStore(data_dir)
    return _secure_store_cache["store"]


def reset_secure_store_cache():
    """Erzwingt Neuinitialisierung des Caches (z. B. nach data_dir-Änderung in Tests)."""
    _secure_store_cache.clear()

class ConfigManager:
    """Zentrales Konfigurationsmanagement für ND-Hub."""
    
    APP_NAME = "ND-Hub"
    DEFAULT_CONFIG_FILENAME = "settings.ini"
    
    def __init__(self):
        self.data_dir = self._get_app_data_dir()
        self.config_path = os.path.join(self.data_dir, self.DEFAULT_CONFIG_FILENAME)
        self.config = configparser.ConfigParser()
        self._ensure_data_dir_exists()
        self.load_config()

    def _get_app_data_dir(self) -> str:
        """Ermittelt den Pfad für Anwendungsdaten (Benutzer-AppData oder Home). Rezession-sicher."""
        if sys.platform == 'win32':
            base_dir = os.environ.get('APPDATA', os.path.expanduser("~"))
        else:
            base_dir = os.path.expanduser("~")
        
        data_dir = os.path.join(base_dir, self.APP_NAME)
        return data_dir

    def _ensure_data_dir_exists(self):
        """Stellt sicher, dass das Datenverzeichnis existiert."""
        if not os.path.exists(self.data_dir):
            try:
                os.makedirs(self.data_dir)
                logger.info(f"Datenverzeichnis erstellt: {self.data_dir}")
            except Exception as e:
                logger.error(f"Fehler beim Erstellen des Datenverzeichnisses: {e}")

    def load_config(self):
        """Lädt die Konfiguration aus der INI-Datei."""
        if os.path.exists(self.config_path):
            try:
                self.config.read(self.config_path, encoding='utf-8')
            except Exception as e:
                logger.error(f"Fehler beim Lesen der Konfigurationsdatei: {e}")
                self._set_defaults()
        else:
            self._set_defaults()
            self.save_config()

    def _set_defaults(self):
        """Setzt Standardwerte für die Konfiguration."""
        if 'General' not in self.config:
            self.config['General'] = {}
        
        self.config['General']['database_path'] = os.path.join(self.data_dir, "nd_hub.db")
        self.config['General']['log_level'] = "INFO"
        self.config['General']['theme'] = "light"
        self.config['General']['operating_mode'] = "local_only"
        self.config['General']['backend_url'] = ""
        self.config['General']['backend_token'] = ""  # nosec B105: placeholder; real token lives in SecureTokenStore
        self.config['General']['sync_interval_seconds'] = "120"
        self.config['General']['sync_cursor'] = "0"

    def save_config(self):
        """Speichert die Konfiguration in der INI-Datei."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as configfile:
                self.config.write(configfile)
            logger.info("Konfiguration gespeichert.")
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Konfiguration: {e}")

    def get_db_path(self) -> str:
        """Gibt den Pfad zur Datenbank zurück (priorisiert config)."""
        return self.config.get('General', 'database_path', fallback=os.path.join(self.data_dir, "nd_hub.db"))

    def set_db_path(self, path: str):
        """Setzt einen neuen Pfad für die Datenbank."""
        if 'General' not in self.config:
            self.config['General'] = {}
        self.config['General']['database_path'] = path
        self.save_config()

    def get_log_dir(self) -> str:
        """Gibt das Log-Verzeichnis zurück."""
        log_dir = os.path.join(self.data_dir, "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        return log_dir

    def get_operating_mode(self) -> str:
        """Liefert den konfigurierten Betriebsmodus (local_only/hybrid_sync/remote_only)."""
        return self.config.get('General', 'operating_mode', fallback='local_only').strip().lower()

    def set_operating_mode(self, mode: str):
        """Setzt den Betriebsmodus."""
        if 'General' not in self.config:
            self.config['General'] = {}
        self.config['General']['operating_mode'] = (mode or 'local_only').strip().lower()
        self.save_config()

    def get_backend_url(self) -> str:
        """Liefert die Backend-URL fuer den Sync-Client."""
        return self.config.get('General', 'backend_url', fallback='').strip()

    def set_backend_url(self, url: str):
        """Setzt die Backend-URL."""
        if 'General' not in self.config:
            self.config['General'] = {}
        self.config['General']['backend_url'] = (url or '').strip()
        self.save_config()

    def get_backend_token(self) -> str:
        """
        Liefert optionales Bearer-Token fuer Sync-API-Aufrufe.

        Sicherheits-Migration: Falls noch ein Legacy-Klartext-Token in
        ``settings.ini`` liegt, wird es automatisch in den SecureTokenStore
        migriert und aus der INI entfernt.
        """
        store = _get_secure_store(self.data_dir)
        secure_value = store.get()
        if secure_value:
            return secure_value

        # Legacy-Klartext-Token migrieren (One-Shot)
        legacy = self.config.get('General', 'backend_token', fallback='').strip()
        if legacy:
            logger.info("Migriere Legacy-Klartext-Token in den SecureTokenStore.")
            if store.set(legacy):
                self.config['General']['backend_token'] = ""
                self.save_config()
            return legacy
        return ""

    def set_backend_token(self, token: str):
        """Setzt optionales Bearer-Token fuer Sync (im SecureTokenStore)."""
        store = _get_secure_store(self.data_dir)
        if 'General' not in self.config:
            self.config['General'] = {}
        if not token:
            store.clear()
            self.config['General']['backend_token'] = ""
        else:
            if not store.set(token):
                logger.warning(
                    "Konnte Token nicht in SecureTokenStore schreiben — "
                    "Fallback auf Legacy-Klartext in settings.ini."
                )
                self.config['General']['backend_token'] = (token or '').strip()
            else:
                # Klartext in INI explizit leer halten
                self.config['General']['backend_token'] = ""
        self.save_config()

    def get_sync_interval_seconds(self) -> int:
        """Liefert das Sync-Intervall in Sekunden."""
        raw = self.config.get('General', 'sync_interval_seconds', fallback='120').strip()
        try:
            value = int(raw)
            return max(10, value)
        except (TypeError, ValueError):
            return 120

    def get_sync_cursor(self) -> str:
        """Liefert den letzten erfolgreichen Sync-Cursor."""
        return self.config.get('General', 'sync_cursor', fallback='0').strip() or '0'

    def set_sync_cursor(self, cursor: str):
        """Persistiert den letzten Sync-Cursor."""
        if 'General' not in self.config:
            self.config['General'] = {}
        self.config['General']['sync_cursor'] = (cursor or '0').strip() or '0'
        self.save_config()
