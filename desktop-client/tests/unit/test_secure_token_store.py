"""
Tests für Fix #2: Sicherer Token-Speicher (SecureTokenStore).

Stellt sicher, dass:
1. Token via Fernet-Fallback-Datei gelesen/geschrieben werden kann.
2. Token nie in der INI-Datei als Klartext landet.
3. Legacy-Klartext-Tokens automatisch in den Store migriert werden.
4. ``clear()`` aus beiden Backends entfernt.
"""
from __future__ import annotations

import configparser
import os

# Vor dem Import sicherstellen, dass cryptography + keyring vorhanden sind
import cryptography  # noqa: F401
import keyring  # noqa: F401
import pytest

from core.config_manager import ConfigManager, reset_secure_store_cache


@pytest.fixture
def temp_data_dir(tmp_path):
    """Stellt ein frisches Datenverzeichnis pro Test bereit."""
    reset_secure_store_cache()
    d = tmp_path / "ndhub_data"
    d.mkdir()
    yield str(d)
    reset_secure_store_cache()


class TestSecureTokenStore:
    def test_set_and_get_token(self, temp_data_dir, monkeypatch):
        """Token wird gesetzt und korrekt gelesen (über Fallback-Datei)."""
        # Keyring deaktivieren → nur Fallback-Datei-Pfad
        from core import secure_token_store
        # Keyring-Backend auf Null-Setzen, damit wir deterministisch
        # nur die Datei testen
        monkeypatch.setattr(secure_token_store, "_machine_specific_seed",
                            staticmethod(lambda: b"test-seed"))

        from core.secure_token_store import SecureTokenStore
        store = SecureTokenStore(temp_data_dir)

        # Setzen + Lesen
        assert store.set("super-secret-token-123") is True
        assert store.get() == "super-secret-token-123"

        # Datei existiert und ist NICHT lesbar als Klartext
        fb_path = os.path.join(temp_data_dir, "backend_token.enc")
        assert os.path.exists(fb_path)
        with open(fb_path, "rb") as f:
            content = f.read()
        assert b"super-secret-token-123" not in content, "Token im Klartext in der Datei!"

    def test_clear_removes_token(self, temp_data_dir, monkeypatch):
        from core import secure_token_store
        monkeypatch.setattr(secure_token_store, "_machine_specific_seed",
                            staticmethod(lambda: b"test-seed"))

        from core.secure_token_store import SecureTokenStore
        store = SecureTokenStore(temp_data_dir)

        store.set("geheim")
        assert store.get() == "geheim"
        store.clear()
        assert store.get() is None

    def test_empty_token_clears(self, temp_data_dir, monkeypatch):
        from core import secure_token_store
        monkeypatch.setattr(secure_token_store, "_machine_specific_seed",
                            staticmethod(lambda: b"test-seed"))

        from core.secure_token_store import SecureTokenStore
        store = SecureTokenStore(temp_data_dir)
        store.set("vorhanden")
        # Leeres Token sollte clear() triggern
        assert store.set("") is True
        assert store.get() is None

    def test_backend_status_reports_fernet(self, temp_data_dir, monkeypatch):
        from core.secure_token_store import SecureTokenStore
        store = SecureTokenStore(temp_data_dir)
        status = store.backend_status()
        assert status["fernet_available"] is True


class TestConfigManagerTokenIntegration:
    def test_set_backend_token_writes_to_store(self, temp_data_dir, monkeypatch):
        """set_backend_token() schreibt ins SecureStore, nicht in die INI."""
        from core import secure_token_store
        monkeypatch.setattr(secure_token_store, "_machine_specific_seed",
                            staticmethod(lambda: b"test-seed"))

        cm = ConfigManager()
        # data_dir umlenken
        cm.data_dir = temp_data_dir
        # Klartext-INI sicher leeren
        if "General" in cm.config and "backend_token" in cm.config["General"]:
            cm.config["General"]["backend_token"] = ""
        cm.set_backend_token("my-secret-jwt-xyz")
        cm.save_config()

        # 1. INI enthält KEIN Klartext-Token
        ini = configparser.ConfigParser()
        ini.read(cm.config_path, encoding="utf-8")
        assert ini.get("General", "backend_token", fallback="") == ""

        # 2. Store liefert das Token
        assert cm.get_backend_token() == "my-secret-jwt-xyz"

    def test_legacy_cleartext_token_migrates(self, temp_data_dir, monkeypatch):
        """
        Wenn noch ein Klartext-Token in der INI steht, muss ``get_backend_token``
        es automatisch in den Store migrieren und aus der INI entfernen.
        """
        from core import secure_token_store
        monkeypatch.setattr(secure_token_store, "_machine_specific_seed",
                            staticmethod(lambda: b"test-seed"))

        # INI mit Legacy-Klartext anlegen
        cm = ConfigManager()
        cm.data_dir = temp_data_dir
        if "General" not in cm.config:
            cm.config["General"] = {}
        cm.config["General"]["backend_token"] = "legacy-cleartext-abc"
        cm.save_config()

        # reset cache, damit der neue data_dir gezogen wird
        reset_secure_store_cache()
        cm2 = ConfigManager()
        cm2.data_dir = temp_data_dir

        # Erster Aufruf: liest legacy, migriert in Store
        token = cm2.get_backend_token()
        assert token == "legacy-cleartext-abc"

        # INI wurde auf leer gesetzt
        ini = configparser.ConfigParser()
        ini.read(cm2.config_path, encoding="utf-8")
        assert ini.get("General", "backend_token", fallback="") == ""

    def test_set_empty_token_clears_store(self, temp_data_dir, monkeypatch):
        from core import secure_token_store
        monkeypatch.setattr(secure_token_store, "_machine_specific_seed",
                            staticmethod(lambda: b"test-seed"))

        cm = ConfigManager()
        cm.data_dir = temp_data_dir
        cm.set_backend_token("x")
        assert cm.get_backend_token() == "x"
        cm.set_backend_token("")
        assert cm.get_backend_token() == ""
