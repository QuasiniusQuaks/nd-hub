"""Tests für Constant-Time Password-Verify im Web-Layer (Fix für #29).

Verifiziert, dass `SecurityManager.verify_password`:
1. Korrektes Passwort akzeptiert
2. Falsches Passwort ablehnt
3. Auch für alte 100k-Iteration-Hashes (Legacy-Fallback) korrekt arbeitet
4. Den bcrypt-Pfad nicht beeinträchtigt
"""
import hashlib
import hmac
import os
import sys
import unittest

# ndhub-web als Top-Level-Modul verfügbar machen
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from security_manager import SecurityManager  # noqa: E402


def _make_legacy_hash(password: str) -> str:
    """Erzeugt einen Hash im alten 100k-Iterations-Schema (Salt+Hex-Suffix)."""
    salt = os.urandom(32)
    pwdhash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return salt.hex() + pwdhash.hex()


class VerifyPasswordConstantTimeTests(unittest.TestCase):
    """Akzeptanzkriterien für Issue #29: timing-attack-frei."""

    def test_modern_hash_correct_password_returns_true(self):
        pwd = "S3cret!Pass_with_unicode_äöü"
        pwd_hash = SecurityManager.hash_password(pwd)
        # Falls bcrypt verfügbar ist, nutzt hash_password bcrypt; verify_password
        # geht dann in den bcrypt-Branch — das ist constant-time per Definition.
        self.assertTrue(SecurityManager.verify_password(pwd, pwd_hash))

    def test_modern_hash_wrong_password_returns_false(self):
        pwd_hash = SecurityManager.hash_password("CorrectHorseBatteryStaple")
        self.assertFalse(SecurityManager.verify_password("wrong-password", pwd_hash))

    def test_legacy_100k_hash_correct_password_returns_true(self):
        """Legacy-Hash (100k Iter) muss weiterhin verifizieren."""
        pwd = "legacy_user_password_42"
        pwd_hash = _make_legacy_hash(pwd)
        self.assertTrue(SecurityManager.verify_password(pwd, pwd_hash))

    def test_legacy_100k_hash_wrong_password_returns_false(self):
        pwd_hash = _make_legacy_hash("right_password")
        self.assertFalse(SecurityManager.verify_password("wrong_password", pwd_hash))

    def test_empty_hash_returns_false_without_raising(self):
        self.assertFalse(SecurityManager.verify_password("anything", ""))

    def test_compare_digest_is_used_for_pbkdf2_path(self):
        """Stellt sicher, dass hmac.compare_digest für den PBKDF2-Pfad genutzt wird.

        Wir monkey-patchen hmac.compare_digest und prüfen, ob es aufgerufen wird
        — bei einem korrekten Passwort, dessen Hash wir mit Sicherheit NICHT
        per bcrypt erzeugen (wir erzeugen einen 600k-PBKDF2-Hash direkt).
        """
        pwd = "monkey-patch-test-password"
        salt = os.urandom(32)
        pwdhash = hashlib.pbkdf2_hmac(
            "sha256", pwd.encode("utf-8"), salt, 600000
        )
        pwd_hash = salt.hex() + pwdhash.hex()

        original = hmac.compare_digest
        called = {"n": 0}

        def spy(a, b):
            called["n"] += 1
            return original(a, b)

        hmac.compare_digest = spy
        try:
            result = SecurityManager.verify_password(pwd, pwd_hash)
        finally:
            hmac.compare_digest = original

        self.assertTrue(result)
        # Mindestens 1 Aufruf (modern-Pfad); der Legacy-Pfad kann ebenfalls
        # betreten werden, dann 2.
        self.assertGreaterEqual(called["n"], 1)


if __name__ == "__main__":
    unittest.main()
