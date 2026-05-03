from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

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


def test_hybrid_sync_offline_write_then_push_and_pull_apply(monkeypatch, tmp_path):
    backend_db = str(tmp_path / "backend_sync.db")
    desktop_db = str(tmp_path / "desktop_sync.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")

    app = create_app(db_path=backend_db)
    client = TestClient(app)
    token = _admin_token(client, "InitPass!12345")
    headers = {"Authorization": f"Bearer {token}"}

    desktop = Database(desktop_db)
    try:
        api_adapter = _ClientApiAdapter(client=client, token=token)
        router = DataAccessRouter(local_db=desktop, operating_mode=OperatingMode.HYBRID_SYNC, api_client=api_adapter)
        sync_config = _InMemorySyncConfig()
        sync_service = DesktopSyncService(db=desktop, config=sync_config, router=router)

        # Offline/local write: erzeugt Outbox-Eintrag.
        desktop_depot_id = desktop.add_depot(
            "Offline Depot",
            "Testweg 7",
            "040-123",
            "offline@example.org",
        )
        assert desktop_depot_id is not None
        assert len(desktop.list_pending_sync_outbox(limit=20)) >= 1

        first_cycle = sync_service.run_cycle(actor_username="admin")
        assert first_cycle.pushed >= 1
        assert first_cycle.conflicts == 0
        assert len(desktop.list_pending_sync_outbox(limit=20)) == 0

        depots_from_server = client.get("/depots", headers=headers)
        assert depots_from_server.status_code == 200
        assert any(row["name"] == "Offline Depot" for row in depots_from_server.json())

        # Server-side write, die nur per Pull in den Desktop kommt.
        create_remote_praeparat = client.post(
            "/praeparate",
            headers=headers,
            json={"name": "Server Praeparat X"},
        )
        assert create_remote_praeparat.status_code == 201

        second_cycle = sync_service.run_cycle(actor_username="admin")
        assert second_cycle.pulled >= 1
        assert int(sync_config.get_sync_cursor()) > 0

        local_praeparate = desktop.list_praeparate()
        local_names = {str(row["name"]) for row in local_praeparate}
        assert "Server Praeparat X" in local_names
    finally:
        desktop.release_write_lease()
        desktop.conn.close()


def test_hybrid_sync_marks_outbox_conflict_for_delete_update_case(monkeypatch, tmp_path):
    backend_db = str(tmp_path / "backend_conflict.db")
    desktop_db = str(tmp_path / "desktop_conflict.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")

    app = create_app(db_path=backend_db)
    client = TestClient(app)
    token = _admin_token(client, "InitPass!12345")
    headers = {"Authorization": f"Bearer {token}"}

    desktop = Database(desktop_db)
    try:
        api_adapter = _ClientApiAdapter(client=client, token=token)
        router = DataAccessRouter(local_db=desktop, operating_mode=OperatingMode.HYBRID_SYNC, api_client=api_adapter)
        sync_config = _InMemorySyncConfig()
        sync_service = DesktopSyncService(db=desktop, config=sync_config, router=router)

        # Server erstellt Datensatz; Desktop holt ihn via Pull.
        create_depot = client.post(
            "/depots",
            headers=headers,
            json={
                "name": "Conflict Depot",
                "adresse": "Serverstr. 1",
                "telefon": "555-12",
                "email": "conflict@example.org",
            },
        )
        assert create_depot.status_code == 201
        depot_id = int(create_depot.json()["id"])

        initial_pull = sync_service.run_cycle(actor_username="admin")
        assert initial_pull.pulled >= 1

        # Server loescht den Datensatz, Desktop aendert danach lokal denselben Datensatz.
        delete_server = client.delete(f"/depots/{depot_id}", headers=headers)
        assert delete_server.status_code == 200

        desktop.update_depot(
            depot_id,
            "Conflict Depot Local Update",
            "Desktopweg 2",
            "555-99",
            "local@example.org",
        )
        pending = desktop.list_pending_sync_outbox(limit=20)
        assert any(item["entity_name"] == "depots" and item["operation"] == "update" for item in pending)
        target = next(item for item in pending if item["entity_name"] == "depots" and item["operation"] == "update")
        outbox_id = int(target["id"])

        conflict_cycle = sync_service.run_cycle(actor_username="admin")
        assert conflict_cycle.conflicts >= 1

        row = desktop.cur.execute(
            "SELECT status, last_error FROM sync_outbox WHERE id = ?",
            (outbox_id,),
        ).fetchone()
        assert row is not None
        assert str(row["status"]) == "conflict"
        assert "nicht gefunden" in str(row["last_error"] or "").lower()
    finally:
        desktop.release_write_lease()
        desktop.conn.close()
