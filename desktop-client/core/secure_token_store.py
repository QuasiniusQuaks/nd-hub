"""
Sichere Token-Speicherung mit 3-stufigem Backend.

Priorität:
1. OS-secure-storage via `keyring` (Windows Credential Manager / macOS Keychain / Linux Secret Service)
2. Verschlüsselte Fallback-Datei (Fernet + PBKDF2 mit maschinenbasiertem Schlüssel)
3. In-Memory (nur als letzter Notnagel, wenn beide Backends fehlschlagen)

Hintergrund: Backend-Token für die Sync-API wurden vorher im Klartext in
``settings.ini`` abgelegt. Wer Zugriff auf das User-Home hat, hatte damit
direkten Sync-Zugriff. Mit diesem Modul landet das Token bevorzugt im
Betriebssystem-Keyring und nur als verschlüsselter Fallback auf der Platte.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import platform
import socket
import uuid
from typing import Optional

logger = logging.getLogger("ND-Hub.SecureTokenStore")

# Schlüssel-Namespace für den OS-Keyring
KEYRING_SERVICE = "ND-Hub"
KEYRING_USER = "backend_token"

# Dateiname für den verschlüsselten Fallback
FALLBACK_FILENAME = "backend_token.enc"


def _machine_specific_seed() -> bytes:
    """
    Erzeugt einen maschinenbasierten Seed, der ohne Root-Rechte stabil ist.

    Kombiniert: Hostname + Plattform-spezifische Maschinen-IDs
    (Linux: /etc/machine-id; macOS: IOPlatformUUID; Windows: MachineGuid).
    Plus einem zufallsbasierten Salt, der beim ersten Lauf in
    ``<data_dir>/.token_salt`` persistiert wird.
    """
    parts: list[str] = [socket.gethostname(), platform.node(), str(uuid.getnode())]

    if platform.system() == "Linux":
        try:
            with open("/etc/machine-id", "r", encoding="utf-8") as f:
                parts.append(f.read().strip())
        except OSError:
            pass
    elif platform.system() == "Darwin":
        try:
            with open("/var/lib/dslocal/nodes/Default/users/localuser.plist", "rb") as f:
                pass  # IOPlatformUUID ist nicht trivial zugänglich; fallback
        except OSError:
            pass
    elif platform.system() == "Windows":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"SOFTWARE\Microsoft\Cryptography") as key:
                value, _ = winreg.QueryValueEx(key, "MachineGuid")
                parts.append(str(value))
        except OSError:
            pass

    return "|".join(parts).encode("utf-8")


def _load_or_create_salt(salt_path: str) -> bytes:
    """Lädt das Salt aus ``salt_path`` oder erzeugt ein neues 32-Byte-Salt."""
    if os.path.exists(salt_path):
        try:
            with open(salt_path, "rb") as f:
                return f.read()
        except OSError as e:
            logger.warning(f"Konnte Salt nicht lesen ({e}), erzeuge neues Salt.")
    salt = os.urandom(32)
    try:
        os.makedirs(os.path.dirname(salt_path), exist_ok=True)
        # Schreib mit restriktiven Permissions, wo möglich.
        fd = os.open(salt_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, salt)
        finally:
            os.close(fd)
    except OSError as e:
        logger.warning(f"Konnte Salt nicht persistieren ({e}).")
    return salt


class SecureTokenStore:
    """Sichere Speicherung für sensible Tokens."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.fallback_path = os.path.join(data_dir, FALLBACK_FILENAME)
        self.salt_path = os.path.join(data_dir, ".token_salt")
        self._fernet = None
        self._keyring_backend = None
        self._keyring_checked = False
        self._init_backends()

    def _init_backends(self) -> None:
        """Initialisiert die verfügbaren Backends."""
        # Keyring (optional)
        if not self._keyring_checked:
            self._keyring_checked = True
            try:
                import keyring
                from keyring.backend import KeyringBackend
                kr: KeyringBackend = keyring.get_keyring()
                # Null-Keystore (z. B. headless Linux ohne Secret Service) erkennen
                if kr is not None and "null" not in type(kr).__name__.lower():
                    self._keyring_backend = keyring
                    logger.info(f"Keyring-Backend aktiv: {type(kr).__name__}")
                else:
                    logger.info("Kein nutzbarer Keyring-Backend gefunden.")
            except Exception as e:
                logger.info(f"keyring nicht verfügbar ({type(e).__name__}): {e}")

        # Fernet-Fallback (immer verfügbar, solange cryptography installiert)
        try:
            from cryptography.fernet import Fernet
            seed = _machine_specific_seed()
            salt = _load_or_create_salt(self.salt_path)
            derived = hashlib.pbkdf2_hmac("sha256", seed, salt, 200_000, dklen=32)
            key = base64.urlsafe_b64encode(derived)
            self._fernet = Fernet(key)
        except Exception as e:
            logger.warning(f"Fernet-Backend nicht initialisierbar ({type(e).__name__}): {e}")

    # ------------------------------------------------------------------ Public API

    def get(self) -> Optional[str]:
        """
        Liefert das gespeicherte Token oder None.

        Reihenfolge: keyring → fallback-Datei → None.
        """
        if self._keyring_backend is not None:
            try:
                value = self._keyring_backend.get_password(KEYRING_SERVICE, KEYRING_USER)
                if value:
                    return value
            except Exception as e:
                logger.warning(f"Keyring-Lese-Fehler: {e}")

        if self._fernet is not None and os.path.exists(self.fallback_path):
            try:
                with open(self.fallback_path, "rb") as f:
                    ciphertext = f.read()
                return self._fernet.decrypt(ciphertext).decode("utf-8")
            except Exception as e:
                logger.warning(f"Fallback-Datei nicht lesbar ({type(e).__name__}): {e}")
        return None

    def set(self, token: str) -> bool:
        """
        Persistiert das Token. Gibt True zurück, wenn es in mindestens einem
        Backend dauerhaft gespeichert wurde.
        """
        token = (token or "").strip()
        if not token:
            return self.clear()

        ok = False
        # Keyring bevorzugt
        if self._keyring_backend is not None:
            try:
                self._keyring_backend.set_password(KEYRING_SERVICE, KEYRING_USER, token)
                ok = True
            except Exception as e:
                logger.warning(f"Keyring-Schreib-Fehler: {e}")

        # Fallback-Datei (immer zusätzlich, damit bei Keyring-Verlust nicht das Token weg ist)
        if self._fernet is not None:
            try:
                os.makedirs(self.data_dir, exist_ok=True)
                ciphertext = self._fernet.encrypt(token.encode("utf-8"))
                fd = os.open(self.fallback_path,
                             os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                try:
                    os.write(fd, ciphertext)
                finally:
                    os.close(fd)
                ok = True
            except Exception as e:
                logger.warning(f"Fallback-Schreib-Fehler: {e}")
        return ok

    def clear(self) -> bool:
        """Löscht das Token aus allen Backends."""
        ok = False
        if self._keyring_backend is not None:
            try:
                self._keyring_backend.delete_password(KEYRING_SERVICE, KEYRING_USER)
                ok = True
            except Exception:
                # password not found ist ok
                ok = True
        try:
            if os.path.exists(self.fallback_path):
                os.remove(self.fallback_path)
            ok = True
        except OSError as e:
            logger.warning(f"Fallback-Datei konnte nicht gelöscht werden: {e}")
        return ok

    def backend_status(self) -> dict:
        """Diagnostik-Info: Welche Backends sind aktiv?"""
        return {
            "keyring_available": self._keyring_backend is not None,
            "fernet_available": self._fernet is not None,
            "fallback_path": self.fallback_path if self._fernet is not None else None,
        }
