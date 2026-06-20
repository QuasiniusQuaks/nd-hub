from __future__ import annotations

import sqlite3

from backend.app import create_app
from fastapi.testclient import TestClient


def _seed_masterdata(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO depots (name, adresse, telefon, email) VALUES (?, ?, ?, ?)",
            ("Depot A", "A-Str", "111", "a@example.org"),
        )
        cur.execute("INSERT INTO praeparate (name) VALUES (?)", ("Praeparat X",))
        conn.commit()
    finally:
        conn.close()


def _admin_headers(client: TestClient) -> dict[str, str]:
    login = client.post("/auth/login", json={"username": "admin", "password": "InitPass!12345"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['token']}"}


def test_import_execute_is_idempotent_for_same_payload(monkeypatch, tmp_path):
    db_path = str(tmp_path / "import_idempotent.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_masterdata(db_path)
    client = TestClient(app)
    headers = _admin_headers(client)

    csv_content = (
        b"Depot,Praeparat,Typ,Charge,Verfall,Datum,Anzahl,Empfaenger\n"
        b"Depot A,Praeparat X,Zugang,C-001,2027-12-31,2026-06-01,3,\n"
    )

    first = client.post(
        "/imports/bewegungen/execute",
        files={"file": ("import.csv", csv_content, "text/csv")},
        headers=headers,
    )
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["imported"] == 1
    assert first_payload["deduplicated"] is False

    second = client.post(
        "/imports/bewegungen/execute",
        files={"file": ("import.csv", csv_content, "text/csv")},
        headers=headers,
    )
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["deduplicated"] is True
    assert second_payload["imported"] == 1

    rows = client.get("/bewegungen?limit=100&offset=0", headers=headers)
    assert rows.status_code == 200
    assert len(rows.json()) == 1


def test_import_preview_returns_error_summary(monkeypatch, tmp_path):
    db_path = str(tmp_path / "import_summary.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_masterdata(db_path)
    client = TestClient(app)
    headers = _admin_headers(client)

    csv_content = (
        b"Depot,Praeparat,Typ,Charge,Verfall,Datum,Anzahl,Empfaenger\n"
        b"Depot B,Praeparat X,Zugang,C-001,2027-12-31,2026-06-01,3,\n"
        b"Depot A,Praeparat X,Zugang,C-002,invalid,2026-06-01,3,\n"
        b"Depot A,Praeparat X,Zugang,C-003,2027-12-31,2026-06-01,0,\n"
    )

    preview = client.post(
        "/imports/bewegungen/preview",
        files={"file": ("preview.csv", csv_content, "text/csv")},
        headers=headers,
    )
    assert preview.status_code == 200
    payload = preview.json()
    assert payload["error_count"] == 3
    summary = payload.get("error_summary") or {}
    by_code = summary.get("by_code") or {}
    assert int(by_code.get("unknown_depot") or 0) == 1
    assert int(by_code.get("invalid_expiry") or 0) == 1
    assert int(by_code.get("invalid_amount") or 0) == 1


def test_import_execute_dry_run_does_not_write(monkeypatch, tmp_path):
    db_path = str(tmp_path / "import_dry_run.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_masterdata(db_path)
    client = TestClient(app)
    headers = _admin_headers(client)

    csv_content = (
        b"Depot,Praeparat,Typ,Charge,Verfall,Datum,Anzahl,Empfaenger\n"
        b"Depot A,Praeparat X,Zugang,C-DRY,2027-12-31,2026-06-01,4,\n"
    )

    execute = client.post(
        "/imports/bewegungen/execute",
        files={"file": ("import.csv", csv_content, "text/csv")},
        data={"dry_run": "true"},
        headers=headers,
    )
    assert execute.status_code == 200
    payload = execute.json()
    assert payload["dry_run"] is True
    assert payload["imported"] == 0
    assert payload["would_imported"] == 1

    rows = client.get("/bewegungen?limit=100&offset=0", headers=headers)
    assert rows.status_code == 200
    assert len(rows.json()) == 0
