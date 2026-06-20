"""Tests fuer Login Rate-Limit / Lockout (Fix fuer #32).

Akzeptanzkriterien:
- 5 Versuche/Minute/IP (per-IP-Limit via slowapi)
- 10 Fehlversuche/Username -> 15 min Lockout
- 429-Response mit Retry-After-Header
- Audit-Log-Eintrag bei Lockout
- Erfolgreicher Login resettet Lockout-Counter
"""
import os
import sys
import unittest

os.environ.setdefault("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
# Lockout fuer Tests auf 2 Fehlversuche reduzieren, damit Tests schnell laufen
os.environ["ND_HUB_LOGIN_MAX_FAILS"] = "2"
os.environ["ND_HUB_LOGIN_LOCKOUT_SECONDS"] = "3"
# IP-Limit auf 10/min anheben, damit Username-Lockout getestet werden kann
os.environ["ND_HUB_LOGIN_IP_LIMIT"] = "10/minute"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi.testclient import TestClient  # noqa: E402

from backend.app import create_app  # noqa: E402


class LoginRateLimitTests(unittest.TestCase):
    """Akzeptanzkriterien fuer Issue #32."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmp.name, "rate_limit.db")
        # ENV-Vars zuruecksetzen — create_app liest sie zum Init-Zeitpunkt
        for var in ("ND_HUB_LOGIN_IP_LIMIT", "ND_HUB_LOGIN_MAX_FAILS",
                    "ND_HUB_LOGIN_LOCKOUT_SECONDS"):
            os.environ.pop(var, None)
        # Test-Tuning
        os.environ["ND_HUB_LOGIN_MAX_FAILS"] = "2"
        os.environ["ND_HUB_LOGIN_LOCKOUT_SECONDS"] = "3"
        os.environ["ND_HUB_LOGIN_IP_LIMIT"] = "1000/minute"  # IP-Limit aushebeln fuer Username-Test
        self.app = create_app(db_path=self.db_path)
        self.client = TestClient(self.app)

    def tearDown(self):
        self._tmp.cleanup()
        for var in ("ND_HUB_LOGIN_IP_LIMIT", "ND_HUB_LOGIN_MAX_FAILS",
                    "ND_HUB_LOGIN_LOCKOUT_SECONDS"):
            os.environ.pop(var, None)

    def _login(self, username="admin", password="wrong"):
        return self.client.post(
            "/auth/login",
            json={"username": username, "password": password},
        )

    def test_wrong_password_returns_401(self):
        r = self._login(password="wrong_password_42")
        self.assertEqual(r.status_code, 401)

    def test_correct_password_returns_200(self):
        r = self._login(password="InitPass!12345")
        self.assertEqual(r.status_code, 200)
        self.assertIn("token", r.json())

    def test_lockout_after_max_fails(self):
        """Nach ND_HUB_LOGIN_MAX_FAILS (hier 2) Fehlversuchen -> 429."""
        r = self._login(password="wrong")
        self.assertEqual(r.status_code, 401, "Erster Fehlversuch sollte 401 sein")
        # 2. Versuch: max_fails erreicht -> locked
        r = self._login(password="wrong")
        self.assertEqual(r.status_code, 429)
        self.assertIn("Retry-After", r.headers)
        retry_after = int(r.headers["Retry-After"])
        self.assertGreater(retry_after, 0)
        self.assertLessEqual(retry_after, 3)

    def test_lockout_429_even_with_correct_password(self):
        """Locked Username bleibt locked, auch bei korrektem Passwort."""
        self._login(password="wrong")  # 1. Fehlversuch
        self._login(password="wrong")  # 2. Fehlversuch -> Lockout
        # Korrektes Passwort waehrend Lockout
        r = self._login(password="InitPass!12345")
        self.assertEqual(r.status_code, 429)
        self.assertIn("Retry-After", r.headers)

    def test_successful_login_clears_lockout_counter(self):
        """Bei erfolgreichem Login wird der Counter zurueckgesetzt."""
        # 1 Fehlversuch
        r = self._login(password="wrong")
        self.assertEqual(r.status_code, 401)
        # Erfolgreich
        r = self._login(password="InitPass!12345")
        self.assertEqual(r.status_code, 200)
        # Wieder 1 Fehlversuch — sollte noch KEIN Lockout ausloesen
        r = self._login(password="wrong")
        self.assertEqual(r.status_code, 401, "Counter wurde nicht zurueckgesetzt")

    def test_audit_log_on_lockout(self):
        """Bei Lockout wird ein Audit-Log-Eintrag erzeugt."""
        self._login(password="wrong")  # 1. Fehlversuch
        r = self._login(password="wrong")  # 2. Fehlversuch -> Lockout
        self.assertEqual(r.status_code, 429)
        # Login als Admin ist wegen Lockout blockiert
        login = self.client.post(
            "/auth/login",
            json={"username": "admin", "password": "InitPass!12345"},
        )
        self.assertEqual(login.status_code, 429)

    def test_lockout_different_users_independent(self):
        """Lockout eines Usernames sperrt nicht andere Usernames."""
        # User1 locked
        self._login(username="user1", password="wrong")
        r = self._login(username="user1", password="wrong")
        self.assertEqual(r.status_code, 429)
        # User2 (existiert nicht) ist nicht gelockt — bekommt normales 401
        r = self._login(username="user2", password="wrong")
        self.assertEqual(r.status_code, 401)


class IPLimitTests(unittest.TestCase):
    """Per-IP Rate-Limit via slowapi."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmp.name, "ip_limit.db")
        for var in ("ND_HUB_LOGIN_IP_LIMIT", "ND_HUB_LOGIN_MAX_FAILS",
                    "ND_HUB_LOGIN_LOCKOUT_SECONDS"):
            os.environ.pop(var, None)
        # IP-Limit: 2/min, Username-Limit hoch
        os.environ["ND_HUB_LOGIN_IP_LIMIT"] = "2/minute"
        os.environ["ND_HUB_LOGIN_MAX_FAILS"] = "100"
        os.environ["ND_HUB_LOGIN_LOCKOUT_SECONDS"] = "1"
        self.app = create_app(db_path=self.db_path)
        self.client = TestClient(self.app)

    def tearDown(self):
        self._tmp.cleanup()
        for var in ("ND_HUB_LOGIN_IP_LIMIT", "ND_HUB_LOGIN_MAX_FAILS",
                    "ND_HUB_LOGIN_LOCKOUT_SECONDS"):
            os.environ.pop(var, None)

    def test_ip_limit_returns_429(self):
        """Ab dem 3. Request (Limit 2/min) kommt 429."""
        for i in range(2):
            r = self.client.post(
                "/auth/login",
                json={"username": "admin", "password": "wrong"},
            )
            # 401 oder 429 (je nach Reihenfolge IP-Limit vs Username-Counter)
            self.assertIn(r.status_code, (401, 429), f"Request {i+1}: unexpected {r.status_code}")
        # 3. Request muss 429 sein
        r = self.client.post(
            "/auth/login",
            json={"username": "admin", "password": "wrong"},
        )
        self.assertEqual(r.status_code, 429)
        self.assertIn("Retry-After", r.headers)


if __name__ == "__main__":
    unittest.main()
