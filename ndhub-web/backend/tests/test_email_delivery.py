from __future__ import annotations

import sqlite3

import backend.app as app_module
from backend.app import create_app
from fastapi.testclient import TestClient


def _seed_email_contacts(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO depots (name, adresse, telefon, email) VALUES (?, ?, ?, ?)",
            ("Depot Mail", "Mail-Str", "123", "depot@example.org"),
        )
        cur.execute(
            "INSERT INTO kontakte (depot_id, name, rolle, telefon, email) VALUES (?, ?, ?, ?, ?)",
            (1, "Max Mustermann", "Leitung", "555", "max@example.org"),
        )
        conn.commit()
    finally:
        conn.close()


def _admin_headers(client: TestClient) -> dict[str, str]:
    login = client.post("/auth/login", json={"username": "admin", "password": "InitPass!12345"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['token']}"}


def test_email_delivery_status_defaults_to_draft_mode(monkeypatch, tmp_path):
    db_path = str(tmp_path / "email_delivery_status.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    monkeypatch.setenv("ND_HUB_EMAIL_DELIVERY_MODE", "draft")
    app = create_app(db_path=db_path)
    _seed_email_contacts(db_path)
    client = TestClient(app)
    headers = _admin_headers(client)

    status_response = client.get("/emails/delivery/status", headers=headers)
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["mode"] == "draft"
    assert payload["can_send_now"] is False


def test_email_send_now_uses_smtp_when_configured(monkeypatch, tmp_path):
    db_path = str(tmp_path / "email_delivery_send_ok.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    monkeypatch.setenv("ND_HUB_EMAIL_DELIVERY_MODE", "smtp")
    monkeypatch.setenv("ND_HUB_SMTP_HOST", "smtp.example.org")
    monkeypatch.setenv("ND_HUB_SMTP_FROM_ADDRESS", "ndhub@example.org")
    app = create_app(db_path=db_path)
    _seed_email_contacts(db_path)
    client = TestClient(app)
    headers = _admin_headers(client)

    def _fake_send(*_args, **_kwargs):
        return {"sent_count": 1, "rejected_recipients": []}

    monkeypatch.setattr(app_module, "_send_email_via_smtp", _fake_send)

    create_response = client.post(
        "/emails/drafts",
        json={
            "depot_ids": [1],
            "betreff": "Test Betreff",
            "nachricht": "Hallo Welt",
            "send_now": True,
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["delivery_status"] == "sent"
    assert payload["sent_count"] == 1

    detail_response = client.get(f"/emails/history/{payload['id']}", headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["versand_status"] == "sent"


def test_email_send_now_failure_keeps_draft(monkeypatch, tmp_path):
    db_path = str(tmp_path / "email_delivery_send_fail.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    monkeypatch.setenv("ND_HUB_EMAIL_DELIVERY_MODE", "smtp")
    monkeypatch.setenv("ND_HUB_SMTP_HOST", "smtp.example.org")
    monkeypatch.setenv("ND_HUB_SMTP_FROM_ADDRESS", "ndhub@example.org")
    app = create_app(db_path=db_path)
    _seed_email_contacts(db_path)
    client = TestClient(app)
    headers = _admin_headers(client)

    def _fake_send_fail(*_args, **_kwargs):
        raise RuntimeError("SMTP down")

    monkeypatch.setattr(app_module, "_send_email_via_smtp", _fake_send_fail)

    create_response = client.post(
        "/emails/drafts",
        json={
            "depot_ids": [1],
            "betreff": "Test Betreff",
            "nachricht": "Hallo Welt",
            "send_now": True,
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["delivery_status"] == "send_failed"
    assert "SMTP down" in (payload.get("delivery_error") or "")

    history = client.get("/emails/history?limit=50", headers=headers)
    assert history.status_code == 200
    rows = history.json()
    assert len(rows) == 1
    assert rows[0]["versand_status"] == "send_failed"
