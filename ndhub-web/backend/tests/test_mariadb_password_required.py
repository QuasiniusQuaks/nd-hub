"""Fail-closed MariaDB passwords (Issue #104)."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.config import resolve_mariadb_settings
from backend.repository_factory import create_repository

NDHUB_WEB = Path(__file__).resolve().parents[2]
COMPOSE = NDHUB_WEB / "docker-compose.yml"
ENV_EXAMPLE = NDHUB_WEB / ".env.example"


def test_compose_requires_mariadb_passwords():
    text = COMPOSE.read_text(encoding="utf-8")
    assert "${ND_HUB_MARIADB_PASSWORD:-}" not in text
    assert "${ND_HUB_MARIADB_ROOT_PASSWORD:-}" not in text
    assert "${ND_HUB_MARIADB_PASSWORD:?" in text
    assert "${ND_HUB_MARIADB_ROOT_PASSWORD:?" in text
    assert text.count("${ND_HUB_MARIADB_PASSWORD:?") == 2
    assert text.count("${ND_HUB_MARIADB_ROOT_PASSWORD:?") == 1


def test_env_example_has_placeholders_not_secrets():
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    assert "ND_HUB_MARIADB_PASSWORD=__CHANGE_ME__" in text
    assert "ND_HUB_MARIADB_ROOT_PASSWORD=__CHANGE_ME__" in text
    lowered = text.lower()
    for forbidden in ("changeme", "changerootme", "password=secret", "password=admin"):
        assert forbidden not in lowered.replace("__change_me__", "")


def test_resolve_mariadb_settings_rejects_empty_password(monkeypatch):
    monkeypatch.delenv("ND_HUB_MARIADB_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="ND_HUB_MARIADB_PASSWORD"):
        resolve_mariadb_settings()

    monkeypatch.setenv("ND_HUB_MARIADB_PASSWORD", "   ")
    with pytest.raises(RuntimeError, match="ND_HUB_MARIADB_PASSWORD"):
        resolve_mariadb_settings()


def test_resolve_mariadb_settings_accepts_set_password(monkeypatch):
    monkeypatch.setenv("ND_HUB_MARIADB_PASSWORD", "not-a-default")
    monkeypatch.setenv("ND_HUB_MARIADB_USER", "ndhub")
    settings = resolve_mariadb_settings()
    assert settings.password == "not-a-default"
    assert settings.user == "ndhub"


def test_factory_mariadb_rejects_empty_password(tmp_path, monkeypatch):
    monkeypatch.delenv("ND_HUB_MARIADB_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="ND_HUB_MARIADB_PASSWORD"):
        create_repository(db_path=str(tmp_path / "x.db"), db_engine="mariadb")
