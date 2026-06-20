from __future__ import annotations

import sqlite3

from backend.app import create_app
from fastapi.testclient import TestClient


def _admin_headers(client: TestClient) -> dict[str, str]:
    login = client.post("/auth/login", json={"username": "admin", "password": "InitPass!12345"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['token']}"}


def test_onboarding_status_requires_setup_for_fresh_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "onboarding_status.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    monkeypatch.setenv("ND_HUB_FEATURE_MULTI_INSTITUTION", "1")
    app = create_app(db_path=db_path)
    client = TestClient(app)
    headers = _admin_headers(client)

    response = client.get("/onboarding/status", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["requires_onboarding"] is True
    assert int(payload["counts"]["depots"]) == 0
    assert int(payload["counts"]["praeparate"]) == 0


def test_onboarding_institution_setup_creates_everything_transactional(monkeypatch, tmp_path):
    db_path = str(tmp_path / "onboarding_setup.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    monkeypatch.setenv("ND_HUB_FEATURE_MULTI_INSTITUTION", "1")
    app = create_app(db_path=db_path)
    client = TestClient(app)
    headers = _admin_headers(client)

    payload = {
        "institution": {"name": "Klinik Nord", "adresse": "Hauptstrasse 1"},
        "praeparate": [{"name": "Adrenalin"}, {"name": "Tranexamsaeure"}],
        "depots": [
            {
                "name": "Notfalldepot A",
                "adresse": "Haus A",
                "assignments": [
                    {"praeparat_name": "Adrenalin", "sollbestand": 0},
                    {"praeparat_name": "Tranexamsaeure", "sollbestand": 0},
                ],
            }
        ],
    }
    created = client.post("/onboarding/institution-setup", json=payload, headers=headers)
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "created"
    assert int(body["institution_id"]) > 0
    assert int(body["praeparate_count"]) == 2
    assert len(body["depots"]) == 1

    status_after = client.get("/onboarding/status", headers=headers)
    assert status_after.status_code == 200
    assert status_after.json()["requires_onboarding"] is False

    invalid_payload = {
        "institution": {"name": "Klinik Sued"},
        "praeparate": [{"name": "NaCl 0.9%"}],
        "depots": [
            {
                "name": "Notfalldepot Fehler",
                "assignments": [{"praeparat_name": "Unbekannt", "sollbestand": 0}],
            }
        ],
    }
    failed = client.post("/onboarding/institution-setup", json=invalid_payload, headers=headers)
    assert failed.status_code == 400

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        total_institutions = int(cur.execute("SELECT COUNT(*) FROM institutions").fetchone()[0] or 0)
        total_depots = int(cur.execute("SELECT COUNT(*) FROM depots").fetchone()[0] or 0)
        total_praeparate = int(cur.execute("SELECT COUNT(*) FROM praeparate").fetchone()[0] or 0)
    finally:
        conn.close()

    # No partial writes from failed transaction.
    assert total_institutions == 2  # Standard-Institution + Klinik Nord
    assert total_depots == 1
    assert total_praeparate == 2
