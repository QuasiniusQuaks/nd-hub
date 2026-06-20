from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from backend.app import create_app


def _seed_report_data(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO depots (name, adresse, telefon, email) VALUES (?, ?, ?, ?)", ("Depot A", "", "", ""))
        cur.execute("INSERT INTO depots (name, adresse, telefon, email) VALUES (?, ?, ?, ?)", ("Depot B", "", "", ""))
        cur.execute("INSERT INTO praeparate (name) VALUES (?)", ("Praeparat X",))
        cur.execute("INSERT INTO praeparate (name) VALUES (?)", ("Praeparat Y",))
        cur.execute(
            "INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand) VALUES (?, ?, ?)",
            (1, 1, 10),
        )
        cur.execute(
            """
            INSERT INTO bewegungen (depot_id, praeparat_id, charge, verfall, eingang_datum, ausgang_datum, empfaenger, anzahl, typ)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (1, 1, "R-001", "2027-12-31", "2026-05-01", None, None, 5, "Zugang"),
        )
        conn.commit()
    finally:
        conn.close()


def _admin_headers(client: TestClient) -> dict[str, str]:
    login = client.post("/auth/login", json={"username": "admin", "password": "InitPass!12345"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['token']}"}


def test_report_rejects_invalid_date_range(monkeypatch, tmp_path):
    db_path = str(tmp_path / "report_invalid_dates.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_report_data(db_path)
    client = TestClient(app)
    headers = _admin_headers(client)

    response = client.get(
        "/reports/bewegungen?perspective=depot&ids=1&start_date=2026-06-01&end_date=2026-05-01",
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json().get("detail") == "start_date darf nicht nach end_date liegen."


def test_report_export_filename_contains_context(monkeypatch, tmp_path):
    db_path = str(tmp_path / "report_export_filename.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_report_data(db_path)
    client = TestClient(app)
    headers = _admin_headers(client)

    response = client.get(
        "/reports/bewegungen/export.csv?perspective=depot&ids=1&start_date=2026-05-01&end_date=2026-05-31",
        headers=headers,
    )
    assert response.status_code == 200
    disposition = response.headers.get("content-disposition", "")
    assert "attachment" in disposition.lower()
    assert "bewegungsanalyse_depot_2026-05-01_to_2026-05-31_" in disposition
    assert ".csv" in disposition
