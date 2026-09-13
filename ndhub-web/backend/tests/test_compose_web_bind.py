"""Compose must not publish app port 8000 on all interfaces (Issue #108)."""

from __future__ import annotations

from pathlib import Path

COMPOSE = Path(__file__).resolve().parents[2] / "docker-compose.yml"


def test_compose_web_port_defaults_to_loopback():
    text = COMPOSE.read_text(encoding="utf-8")
    assert '"8000:8000"' not in text
    assert "'8000:8000'" not in text
    assert "${ND_HUB_WEB_BIND:-127.0.0.1}:8000:8000" in text
