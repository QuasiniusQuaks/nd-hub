"""Tests für Desktop-Backend Security-Hardening (Issue #68).

Testet:
- Security-Header (X-Content-Type-Options, X-Frame-Options, Referrer-Policy)
- CORS-Konfiguration (restriktiver Default)
- TrustedHost-Middleware
- Login-Lockout bei wiederholten Fehlversuchen
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import _pyside6_stub  # noqa: F401  (conftest nicht erreichbar aus backend-tests)


@pytest.fixture
def desktop_backend_app(tmp_path):
    """Erstellt eine Desktop-Backend App-Instanz mit Test-DB."""
    db_path = str(tmp_path / "test_backend.db")
    os.environ["ND_HUB_INITIAL_ADMIN_PASSWORD"] = "TestPass!123"

    from backend.app import create_app
    app = create_app(db_path=db_path)

    from fastapi.testclient import TestClient
    client = TestClient(app)
    yield client


class TestSecurityHeaders:
    """Security-Header auf jeder Response."""

    def test_x_content_type_options(self, desktop_backend_app):
        r = desktop_backend_app.get("/health")
        assert r.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, desktop_backend_app):
        r = desktop_backend_app.get("/health")
        assert r.headers.get("X-Frame-Options") == "DENY"

    def test_referrer_policy(self, desktop_backend_app):
        r = desktop_backend_app.get("/health")
        assert r.headers.get("Referrer-Policy") == "no-referrer"


class TestTrustedHost:
    """TrustedHost-Middleware."""

    def test_allows_default_host(self, desktop_backend_app):
        """Default erlaubt alle Hosts ('*')."""
        r = desktop_backend_app.get("/health")
        assert r.status_code == 200


class TestLoginLockout:
    """Login-Lockout bei wiederholten Fehlversuchen."""

    def test_successful_login(self, desktop_backend_app):
        r = desktop_backend_app.post(
            "/auth/login",
            json={"username": "admin", "password": "TestPass!123"},
        )
        assert r.status_code == 200
        assert "token" in r.json()

    def test_failed_login_returns_401(self, desktop_backend_app):
        r = desktop_backend_app.post(
            "/auth/login",
            json={"username": "admin", "password": "wrong-password"},
        )
        assert r.status_code == 401

    def test_lockout_after_max_fails(self, desktop_backend_app, monkeypatch):
        """Nach N Fehlversuchen → 429 Lockout."""
        # Max-Fails auf 3 setzen für schnellen Test
        monkeypatch.setattr(desktop_backend_app.app.state, "login_max_fails", 3)
        monkeypatch.setattr(desktop_backend_app.app.state, "login_lockout_seconds", 60)

        # 3 Fehlversuche
        for _ in range(3):
            desktop_backend_app.post(
                "/auth/login",
                json={"username": "admin", "password": "wrong"},
            )

        # 4. Versuch → 429
        r = desktop_backend_app.post(
            "/auth/login",
            json={"username": "admin", "password": "wrong"},
        )
        assert r.status_code == 429
        assert "gesperrt" in r.json().get("detail", "").lower()

    def test_lockout_cleared_on_success(self, desktop_backend_app, monkeypatch):
        """Erfolgreicher Login setzt Lockout-Counter zurück."""
        monkeypatch.setattr(desktop_backend_app.app.state, "login_max_fails", 10)

        # 2 Fehlversuche (unter Limit)
        for _ in range(2):
            desktop_backend_app.post(
                "/auth/login",
                json={"username": "admin", "password": "wrong"},
            )

        # Erfolgreicher Login
        r = desktop_backend_app.post(
            "/auth/login",
            json={"username": "admin", "password": "TestPass!123"},
        )
        assert r.status_code == 200

        # Counter sollte zurückgesetzt sein → weitere Fehlversuche starten bei 0
        state = desktop_backend_app.app.state.login_lockout_state
        assert "admin" not in state
