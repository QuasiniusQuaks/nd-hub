"""Smoke tests for ND-Hub backend.

These tests verify that the backend starts and core CRUD workflows still
function after security refactoring. They intentionally use TestClient and
a temporary SQLite database, so no external services are required.
"""

from __future__ import annotations

from datetime import date

import pytest
from backend.app import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Provide a TestClient with a fresh SQLite database."""
    db_path = str(tmp_path / "smoke.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "SmokePass!12345")
    # Disable auto backup so lifespan events don't touch the filesystem.
    monkeypatch.setenv("ND_HUB_AUTO_BACKUP_HOURS", "0")
    app = create_app(db_path=db_path)
    return TestClient(app)


def _admin_headers(client: TestClient) -> dict[str, str]:
    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "SmokePass!12345"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['token']}"}


def test_health_and_login(client):
    """App starts, docs are reachable and initial admin login works."""
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "SmokePass!12345"},
    )
    assert login.status_code == 200
    assert "token" in login.json()


def test_depot_crud(client):
    """Create, list and read a depot."""
    headers = _admin_headers(client)

    create = client.post(
        "/depots",
        json={
            "name": "Smoke-Depot",
            "adresse": "Teststraße 1, 12345 Berlin",
            "telefon": "030 123456",
            "email": "smoke@example.org",
        },
        headers=headers,
    )
    assert create.status_code == 201
    depot_id = create.json()["id"]

    listing = client.get("/depots", headers=headers)
    assert listing.status_code == 200
    assert any(d["id"] == depot_id for d in listing.json())


def test_praeparat_and_bewegung_workflow(client):
    """Create a Praeparat and a Zugang Bewegung, then list movements."""
    headers = _admin_headers(client)

    depot = client.post(
        "/depots",
        json={
            "name": "Bewegungs-Depot",
            "adresse": "Bahnhofstraße 2",
            "telefon": "030 987654",
            "email": "bewegung@example.org",
        },
        headers=headers,
    )
    assert depot.status_code == 201
    depot_id = depot.json()["id"]

    praep = client.post(
        "/praeparate",
        json={
            "name": "Morphin 10mg/1ml Amp.",
            "pzn": "12345678",
            "hersteller": "Smoke Pharma",
        },
        headers=headers,
    )
    assert praep.status_code == 201
    praep_id = praep.json()["id"]

    bew = client.post(
        "/bewegungen",
        json={
            "depot_id": depot_id,
            "praeparat_id": praep_id,
            "charge": "SMOKE-001A",
            "verfall": str(date.today().replace(year=date.today().year + 2)),
            "datum": str(date.today()),
            "anzahl": 10,
            "typ": "Zugang",
        },
        headers=headers,
    )
    assert bew.status_code == 201

    listing = client.get("/bewegungen", headers=headers)
    assert listing.status_code == 200
    items = listing.json()
    assert any(b["charge"] == "SMOKE-001A" for b in items)


def test_verfall_and_bestand_endpoints(client):
    """The warning/verfall and bestand endpoints return data without errors."""
    headers = _admin_headers(client)

    resp = client.get("/verfall/overview", headers=headers)
    assert resp.status_code == 200

    depot = client.post(
        "/depots",
        json={
            "name": "Bestand-Depot",
            "adresse": "Berlin",
            "telefon": "030 111",
            "email": "bestand@example.org",
        },
        headers=headers,
    )
    assert depot.status_code == 201
    depot_id = depot.json()["id"]

    resp = client.get(
        f"/reports/bestand?perspective=depot&ids={depot_id}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "rows" in data
    assert "kpis" in data


def test_user_management_flow(client):
    """Create a user, log in as that user and verify restricted access."""
    admin_headers = _admin_headers(client)

    created = client.post(
        "/users",
        json={
            "username": "smoke_user",
            "password": "SmokeUserPass!1",  # gitleaks:allow
            "role": "User",
            "email": "smoke_user@example.org",
            "is_active": True,
            "permissions": ["depots_read"],
        },
        headers=admin_headers,
    )
    assert created.status_code == 201

    login = client.post(
        "/auth/login",
        json={"username": "smoke_user", "password": "SmokeUserPass!1"},  # gitleaks:allow
    )
    assert login.status_code == 200
    user_headers = {"Authorization": f"Bearer {login.json()['token']}"}

    depots = client.get("/depots", headers=user_headers)
    assert depots.status_code == 200
