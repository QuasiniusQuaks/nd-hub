"""Placeholder/empty deploy secrets (Issues #141 #142)."""

from __future__ import annotations

from pathlib import Path

import pytest
from shared.security.runtime_secrets import (
    PlaceholderSecretError,
    is_placeholder_secret,
    require_runtime_secret,
    resolve_initial_admin_password,
)

from backend.config import resolve_mariadb_settings

ROOT = Path(__file__).resolve().parents[3]
WEB_SM = ROOT / "ndhub-web" / "security_manager.py"
DESKTOP_SM = ROOT / "desktop-client" / "security_manager.py"


def test_placeholders_detected():
    assert is_placeholder_secret("__CHANGE_ME__")
    assert is_placeholder_secret("ChangeMe")
    assert is_placeholder_secret("ChangeMeToAStrongPassword_123!")
    assert not is_placeholder_secret("unique-deploy-secret-9f3a")
    assert not is_placeholder_secret("")


def test_require_runtime_secret_rejects_empty_and_placeholder():
    with pytest.raises(PlaceholderSecretError, match="must be set"):
        require_runtime_secret("ND_HUB_MARIADB_PASSWORD", "")
    with pytest.raises(PlaceholderSecretError, match="placeholder"):
        require_runtime_secret("ND_HUB_MARIADB_PASSWORD", "__CHANGE_ME__")
    assert require_runtime_secret("X", "unique-deploy-secret-9f3a") == "unique-deploy-secret-9f3a"


def test_resolve_initial_admin_password_fail_closed(monkeypatch):
    monkeypatch.delenv("ND_HUB_INITIAL_ADMIN_PASSWORD", raising=False)
    with pytest.raises(PlaceholderSecretError, match="ND_HUB_INITIAL_ADMIN_PASSWORD"):
        resolve_initial_admin_password(required=True)
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "__CHANGE_ME__")
    with pytest.raises(PlaceholderSecretError, match="placeholder"):
        resolve_initial_admin_password(required=True)
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "unique-admin-secret-9f3a")
    assert resolve_initial_admin_password(required=True) == "unique-admin-secret-9f3a"


def test_resolve_mariadb_settings_rejects_placeholder(monkeypatch):
    monkeypatch.setenv("ND_HUB_MARIADB_PASSWORD", "__CHANGE_ME__")
    with pytest.raises(RuntimeError, match="placeholder"):
        resolve_mariadb_settings()


def test_security_managers_do_not_log_generated_passwords():
    forbidden = "generiertes Initial-Passwort"
    for path in (WEB_SM, DESKTOP_SM):
        text = path.read_text(encoding="utf-8")
        assert forbidden not in text, path
        assert "token_urlsafe(18)" not in text, path
