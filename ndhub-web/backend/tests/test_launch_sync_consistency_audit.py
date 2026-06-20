from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[3]
NDHUB_WEB_DIR = PROJECT_ROOT / "ndhub-web"
DESKTOP_CLIENT_DIR = PROJECT_ROOT / "desktop-client"


def _prepare_sys_path() -> None:
    """Ndhub-Web muss vor desktop-client stehen: sonst importiert `backend` das Desktop-Paket (ohne /sync/*)."""
    for p in (str(NDHUB_WEB_DIR), str(DESKTOP_CLIENT_DIR)):
        while p in sys.path:
            sys.path.remove(p)
    sys.path.insert(0, str(NDHUB_WEB_DIR))
    sys.path.insert(1, str(DESKTOP_CLIENT_DIR))


_prepare_sys_path()

from backend.app import create_app  # noqa: E402
from core.data_access_layer import DataAccessRouter, OperatingMode  # noqa: E402
from core.sync_service import DesktopSyncService  # noqa: E402
from db_manager import Database  # noqa: E402


class _InMemorySyncConfig:
    def __init__(self):
        self._cursor = "0"

    def get_sync_cursor(self) -> str:
        return self._cursor

    def set_sync_cursor(self, cursor: str):
        self._cursor = str(cursor or "0")


class _ClientApiAdapter:
    def __init__(self, client: TestClient, token: str):
        self.client = client
        self.token = token
        self.config = SimpleNamespace(access_token=token)

    def is_configured(self) -> bool:
        return True

    def check_health(self) -> bool:
        response = self.client.get("/health")
        return response.status_code == 200

    def push_changes(self, batch_id: str, changes: list[dict]) -> dict:
        response = self.client.post(
            "/sync/push",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"batch_id": batch_id, "changes": changes},
        )
        response.raise_for_status()
        return response.json()

    def pull_changes(self, cursor: str | None, entities: list[str] | None, limit: int = 300) -> dict:
        response = self.client.post(
            "/sync/pull",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"cursor": cursor, "entities": entities or [], "limit": limit},
        )
        response.raise_for_status()
        return response.json()


def _admin_token(client: TestClient, password: str) -> str:
    login = client.post("/auth/login", json={"username": "admin", "password": password})
    assert login.status_code == 200
    token = login.json()["token"]
    assert isinstance(token, str) and token
    return token


def _create_user(
    client: TestClient,
    admin_token: str,
    username: str,
    role: str,
    password: str = "UserPass!123",
    permissions: list[str] | None = None,
):
    response = client.post(
        "/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "username": username,
            "password": password,
            "role": role,
            "email": f"{username}@example.org",
            "is_active": True,
            "permissions": permissions or [],
        },
    )
    assert response.status_code == 201


def _user_token(client: TestClient, username: str, password: str = "UserPass!123") -> str:
    login = client.post("/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200
    token = login.json()["token"]
    assert isinstance(token, str) and token
    return token


def test_p0_sync_status_includes_depot_praeparate(monkeypatch, tmp_path):
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=str(tmp_path / "backend.db"))
    client = TestClient(app)
    token = _admin_token(client, "InitPass!12345")
    response = client.get("/sync/status", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    entities = response.json().get("features", {}).get("entities", [])
    assert "depot_praeparate" in entities


def test_p0_roundtrip_praeparate_extended_fields(monkeypatch, tmp_path):
    backend_db = str(tmp_path / "backend.db")
    desktop_db = str(tmp_path / "desktop.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=backend_db)
    client = TestClient(app)
    token = _admin_token(client, "InitPass!12345")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/praeparate",
        headers=headers,
        json={
            "name": "Audit Praeparat",
            "wirkstoff": "Wirk A",
            "darreichungsform": "Ampulle",
            "staerke": "10",
            "einheit": "mg",
            "pzn": "12345678",
            "hersteller": "Audit Pharma",
        },
    )
    assert created.status_code == 201

    desktop = Database(desktop_db)
    try:
        router = DataAccessRouter(
            local_db=desktop,
            operating_mode=OperatingMode.HYBRID_SYNC,
            api_client=_ClientApiAdapter(client=client, token=token),
        )
        sync_service = DesktopSyncService(db=desktop, config=_InMemorySyncConfig(), router=router)
        cycle = sync_service.run_cycle(actor_username="admin")
        assert cycle.pulled >= 1

        row = next((r for r in desktop.list_praeparate_extended() if r["name"] == "Audit Praeparat"), None)
        assert row is not None
        assert row["wirkstoff"] == "Wirk A"
        assert row["darreichungsform"] == "Ampulle"
        assert row["staerke"] == "10"
        assert row["einheit"] == "mg"
        assert row["pzn"] == "12345678"
        assert row["hersteller"] == "Audit Pharma"
    finally:
        desktop.release_write_lease()
        desktop.conn.close()


def test_p0_roundtrip_depot_extended_fields(monkeypatch, tmp_path):
    backend_db = str(tmp_path / "backend.db")
    desktop_db = str(tmp_path / "desktop.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=backend_db)
    client = TestClient(app)
    token = _admin_token(client, "InitPass!12345")
    headers = {"Authorization": f"Bearer {token}"}

    inst = client.post(
        "/institutions",
        headers=headers,
        json={
            "name": "Audit Klinik",
            "strasse": "Hauptstrasse",
            "hausnummer": "7a",
            "postleitzahl": "12345",
            "stadt": "Berlin",
            "latitude": 52.5208,
            "longitude": 13.4095,
        },
    )
    assert inst.status_code == 201
    inst_id = int(inst.json()["id"])

    depot = client.post(
        "/depots",
        headers=headers,
        json={
            "name": "Audit Depot",
            "strasse": "Nebenweg",
            "hausnummer": "3",
            "postleitzahl": "12345",
            "stadt": "Berlin",
            "telefon": "030-1234",
            "email": "depot@example.org",
            "institution_id": inst_id,
            "latitude": 52.51,
            "longitude": 13.41,
        },
    )
    assert depot.status_code == 201

    desktop = Database(desktop_db)
    try:
        router = DataAccessRouter(
            local_db=desktop,
            operating_mode=OperatingMode.HYBRID_SYNC,
            api_client=_ClientApiAdapter(client=client, token=token),
        )
        sync_service = DesktopSyncService(db=desktop, config=_InMemorySyncConfig(), router=router)
        cycle = sync_service.run_cycle(actor_username="admin")
        assert cycle.pulled >= 1

        row = next((r for r in desktop.list_depots() if r["name"] == "Audit Depot"), None)
        assert row is not None
        assert int(row["institution_id"] or 0) == inst_id
        assert str(row["strasse"] or "").strip() == "Nebenweg"
        assert str(row["hausnummer"] or "").strip() == "3"
        assert str(row["postleitzahl"] or "").strip() == "12345"
        assert str(row["stadt"] or "").strip() == "Berlin"
        assert row["latitude"] is not None and abs(float(row["latitude"]) - 52.51) < 1e-6
        assert row["longitude"] is not None and abs(float(row["longitude"]) - 13.41) < 1e-6

        inst_row = next((r for r in desktop.list_institutions() if r["name"] == "Audit Klinik"), None)
        assert inst_row is not None
        assert str(inst_row["strasse"] or "").strip() == "Hauptstrasse"
        assert str(inst_row["hausnummer"] or "").strip() == "7a"
        assert str(inst_row["postleitzahl"] or "").strip() == "12345"
        assert str(inst_row["stadt"] or "").strip() == "Berlin"
        assert inst_row["latitude"] is not None and abs(float(inst_row["latitude"]) - 52.5208) < 1e-6
        assert inst_row["longitude"] is not None and abs(float(inst_row["longitude"]) - 13.4095) < 1e-6
    finally:
        desktop.release_write_lease()
        desktop.conn.close()


def test_p0_wizard_entities_are_sync_accepted(monkeypatch, tmp_path):
    backend_db = str(tmp_path / "backend.db")
    desktop_db = str(tmp_path / "desktop.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=backend_db)
    client = TestClient(app)
    token = _admin_token(client, "InitPass!12345")

    desktop = Database(desktop_db)
    try:
        desktop.apply_setup_wizard_draft(
            {
                "institution": {
                    "name": "Audit Institution",
                    "strasse": "Musterstrasse",
                    "hausnummer": "1",
                    "postleitzahl": "12345",
                    "stadt": "Berlin",
                    "adresse": "Musterstrasse 1, 12345 Berlin",
                    "latitude": 52.0,
                    "longitude": 13.0,
                },
                "praeparate": [{"name": "Audit P", "wirkstoff": "A"}],
                "depots": [
                    {
                        "name": "Audit D",
                        "strasse": "Musterstrasse",
                        "hausnummer": "2",
                        "postleitzahl": "12345",
                        "stadt": "Berlin",
                        "adresse": "Musterstrasse 2, 12345 Berlin",
                        "email": "d@example.org",
                        "telefon": "030-55",
                        "kontakt_name": "Kontakt D",
                        "contacts": [{"name": "Kontakt D", "rolle": "Leitung", "telefon": "030-55", "email": "d@example.org"}],
                        "praeparat_assignments": [{"name": "Audit P", "sollbestand": 4}],
                    }
                ],
            }
        )

        router = DataAccessRouter(
            local_db=desktop,
            operating_mode=OperatingMode.HYBRID_SYNC,
            api_client=_ClientApiAdapter(client=client, token=token),
        )
        sync_service = DesktopSyncService(db=desktop, config=_InMemorySyncConfig(), router=router)
        cycle = sync_service.run_cycle(actor_username="admin")
        assert cycle.conflicts == 0
        assert cycle.rejected == 0
    finally:
        desktop.release_write_lease()
        desktop.conn.close()


def test_scope_non_admin_sync_pull_is_scoped(monkeypatch, tmp_path):
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=str(tmp_path / "backend.db"))
    client = TestClient(app)
    admin_token = _admin_token(client, "InitPass!12345")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    created = client.post("/depots", headers=admin_headers, json={"name": "Secret Depot", "adresse": "A", "telefon": "1", "email": "a@b.de"})
    assert created.status_code == 201

    _create_user(client, admin_token, username="scope_user", role="User", permissions=[])
    user_token = _user_token(client, "scope_user")
    pull = client.post(
        "/sync/pull",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"cursor": "0", "entities": ["depots"], "limit": 100},
    )
    assert pull.status_code == 200
    depots = [c for c in pull.json().get("changes", []) if c.get("entity") == "depots"]
    assert depots == []


def test_scope_non_admin_sync_push_respects_depot_acl(monkeypatch, tmp_path):
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=str(tmp_path / "backend.db"))
    client = TestClient(app)
    admin_token = _admin_token(client, "InitPass!12345")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    created = client.post("/depots", headers=admin_headers, json={"name": "Scoped Depot", "adresse": "X", "telefon": "1", "email": "x@y.de"})
    assert created.status_code == 201
    depot_id = int(created.json()["id"])

    _create_user(
        client,
        admin_token,
        username="ops_user",
        role="User",
        permissions=["masterdata_write"],
    )
    user_token = _user_token(client, "ops_user")
    push = client.post(
        "/sync/push",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "batch_id": "scope-audit-1",
            "changes": [
                {
                    "entity": "depots",
                    "operation": "update",
                    "payload": {"id": depot_id, "name": "Scoped Depot Updated", "adresse": "X", "telefon": "1", "email": "x@y.de"},
                    "client_change_id": "1",
                }
            ],
        },
    )
    assert push.status_code == 200
    body = push.json()
    assert len(body.get("accepted", [])) == 0
    assert len(body.get("rejected", [])) == 1


def test_conflict_retry_path_requeues_conflicts(monkeypatch, tmp_path):
    backend_db = str(tmp_path / "backend.db")
    desktop_db = str(tmp_path / "desktop.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=backend_db)
    client = TestClient(app)
    token = _admin_token(client, "InitPass!12345")
    headers = {"Authorization": f"Bearer {token}"}

    desktop = Database(desktop_db)
    try:
        router = DataAccessRouter(
            local_db=desktop,
            operating_mode=OperatingMode.HYBRID_SYNC,
            api_client=_ClientApiAdapter(client=client, token=token),
        )
        sync_service = DesktopSyncService(db=desktop, config=_InMemorySyncConfig(), router=router)

        create_depot = client.post("/depots", headers=headers, json={"name": "Conflict Depot", "adresse": "S1", "telefon": "1", "email": "c@x.de"})
        assert create_depot.status_code == 201
        depot_id = int(create_depot.json()["id"])
        assert sync_service.run_cycle(actor_username="admin").pulled >= 1

        assert client.delete(f"/depots/{depot_id}", headers=headers).status_code == 200
        desktop.update_depot(depot_id, "Conflict Depot Local", "L2", "2", "l@x.de")

        conflict_cycle = sync_service.run_cycle(actor_username="admin")
        assert conflict_cycle.conflicts >= 1

        retried = sync_service.retry_conflicts(limit=20)
        assert retried >= 1
        pending = desktop.list_pending_sync_outbox(limit=20)
        assert any(item["status"] in {"pending", "retry"} for item in pending)
    finally:
        desktop.release_write_lease()
        desktop.conn.close()


def test_sync_push_batch_idempotency(monkeypatch, tmp_path):
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=str(tmp_path / "backend.db"))
    client = TestClient(app)
    token = _admin_token(client, "InitPass!12345")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "batch_id": "idempotency-audit-batch",
        "changes": [
            {
                "entity": "praeparate",
                "operation": "create",
                "payload": {"name": "Idempotent P"},
                "client_change_id": "c1",
            }
        ],
    }
    first = client.post("/sync/push", headers=headers, json=payload)
    assert first.status_code == 200
    first_body = first.json()
    assert first_body.get("deduplicated") is False
    assert len(first_body.get("accepted", [])) == 1

    second = client.post("/sync/push", headers=headers, json=payload)
    assert second.status_code == 200
    second_body = second.json()
    assert second_body.get("deduplicated") is True
    assert len(second_body.get("accepted", [])) == 1


def test_identity_remap_after_create_push(monkeypatch, tmp_path):
    backend_db = str(tmp_path / "backend_identity.db")
    desktop_db = str(tmp_path / "desktop_identity.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=backend_db)
    client = TestClient(app)
    token = _admin_token(client, "InitPass!12345")
    headers = {"Authorization": f"Bearer {token}"}

    # Reserve server id=1 to force id mismatch.
    seed = client.post(
        "/depots",
        headers=headers,
        json={"name": "Seed Depot", "adresse": "S", "telefon": "1", "email": "seed@example.org"},
    )
    assert seed.status_code == 201
    assert int(seed.json()["id"]) == 1

    desktop = Database(desktop_db)
    try:
        api_adapter = _ClientApiAdapter(client=client, token=token)
        router = DataAccessRouter(local_db=desktop, operating_mode=OperatingMode.HYBRID_SYNC, api_client=api_adapter)
        sync_service = DesktopSyncService(db=desktop, config=_InMemorySyncConfig(), router=router)

        local_id = int(desktop.add_depot("Remap Depot", "Testweg 9", "040-99", "remap@example.org"))
        assert local_id == 1
        cycle = sync_service.run_cycle(actor_username="admin")
        assert cycle.pushed >= 1

        rows = [r for r in desktop.list_depots() if str(r["name"]) == "Remap Depot"]
        assert len(rows) == 1
        remapped_id = int(rows[0]["id"])
        assert remapped_id > 1
        assert remapped_id == 2
    finally:
        desktop.release_write_lease()
        desktop.conn.close()


def test_movement_name_fallback_rejects_ambiguous_names(monkeypatch, tmp_path):
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=str(tmp_path / "backend_move_amb.db"))
    client = TestClient(app)
    token = _admin_token(client, "InitPass!12345")
    headers = {"Authorization": f"Bearer {token}"}

    # Duplicate names create ambiguity for fallback.
    assert client.post("/depots", headers=headers, json={"name": "AmbDepot", "adresse": "A", "telefon": "1", "email": "a1@x.de"}).status_code == 201
    assert client.post("/depots", headers=headers, json={"name": "AmbDepot", "adresse": "B", "telefon": "2", "email": "a2@x.de"}).status_code == 201
    assert client.post("/praeparate", headers=headers, json={"name": "AmbPrae"}).status_code == 201
    assert client.post("/praeparate", headers=headers, json={"name": "AmbPrae"}).status_code == 201

    push = client.post(
        "/sync/push",
        headers=headers,
        json={
            "batch_id": "move-amb-1",
            "changes": [
                {
                    "entity": "bewegungen",
                    "operation": "create",
                    "payload": {
                        "depot_name": "AmbDepot",
                        "praeparat_name": "AmbPrae",
                        "typ": "Zugang",
                        "charge": "C-1",
                        "verfall": "2030-12-31",
                        "datum": "2026-05-02",
                        "anzahl": 2,
                    },
                    "client_change_id": "move1",
                }
            ],
        },
    )
    assert push.status_code == 200
    body = push.json()
    assert len(body.get("accepted", [])) == 0
    assert len(body.get("rejected", [])) == 1
    assert "nicht eindeutig" in str(body["rejected"][0].get("reason") or "").lower()
