from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from backend.app import create_app
from fastapi.testclient import TestClient
from security_manager import SecurityManager


def _seed_data(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO institutions (name) VALUES (?)", ("Institution A",))
        cur.execute("INSERT INTO depots (name, institution_id) VALUES (?, ?)", ("Depot A", 1))
        cur.execute("INSERT INTO depots (name, institution_id) VALUES (?, ?)", ("Depot B", 1))
        cur.execute("INSERT INTO praeparate (name) VALUES (?)", ("Praeparat X",))
        cur.execute("INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand) VALUES (1, 1, 10)")
        cur.execute("INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand) VALUES (2, 1, 10)")
        cur.execute(
            """
            INSERT INTO bewegungen (depot_id, praeparat_id, charge, verfall, eingang_datum, anzahl, typ)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (1, 1, "A-1", "2027-01-01", "2026-01-01", 3, "Zugang"),
        )
        cur.execute(
            """
            INSERT INTO bewegungen (depot_id, praeparat_id, charge, verfall, eingang_datum, anzahl, typ)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (2, 1, "B-1", "2027-01-01", "2026-01-01", 4, "Zugang"),
        )
        user_hash = SecurityManager.hash_password("UserPass!123")
        cur.execute(
            """
            INSERT INTO users (username, password_hash, role, created_at, is_active, permissions)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (
                "user1",
                user_hash,
                "User",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                json.dumps(["masterdata_read", "movements_read", "movements_write"]),
            ),
        )
        cur.execute(
            "INSERT INTO user_depot_permissions (username, depot_id, can_read, can_write) VALUES (?, ?, ?, ?)",
            ("user1", 1, 1, 1),
        )
        conn.commit()
    finally:
        conn.close()


def _login(client: TestClient, username: str, password: str) -> dict[str, str]:
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_non_admin_only_sees_allowed_depot_data(monkeypatch, tmp_path):
    db_path = str(tmp_path / "scope.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "AdminPass!123")
    app = create_app(db_path=db_path)
    _seed_data(db_path)
    client = TestClient(app)

    headers = _login(client, "user1", "UserPass!123")
    depots = client.get("/depots?limit=100&offset=0", headers=headers)
    assert depots.status_code == 200
    rows = depots.json()
    assert len(rows) == 1
    assert rows[0]["name"] == "Depot A"

    bewegungen = client.get("/bewegungen?limit=100&offset=0", headers=headers)
    assert bewegungen.status_code == 200
    charges = {row["charge"] for row in bewegungen.json()}
    assert "A-1" in charges
    assert "B-1" not in charges


def test_non_admin_cannot_write_foreign_depot(monkeypatch, tmp_path):
    db_path = str(tmp_path / "scope_write.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "AdminPass!123")
    app = create_app(db_path=db_path)
    _seed_data(db_path)
    client = TestClient(app)
    headers = _login(client, "user1", "UserPass!123")

    blocked = client.post(
        "/bewegungen",
        json={
            "depot_id": 2,
            "praeparat_id": 1,
            "typ": "Zugang",
            "charge": "X-NEW",
            "verfall": "2027-02-01",
            "datum": "2026-02-01",
            "anzahl": 1,
            "empfaenger": None,
        },
        headers=headers,
    )
    assert blocked.status_code == 403
