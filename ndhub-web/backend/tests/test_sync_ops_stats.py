from __future__ import annotations

from backend.app import create_app
from fastapi.testclient import TestClient


def test_sync_ops_stats_endpoint_reports_batches(monkeypatch, tmp_path):
    db_path = str(tmp_path / "sync_ops_stats.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    client = TestClient(app)

    login = client.post("/auth/login", json={"username": "admin", "password": "InitPass!12345"})
    assert login.status_code == 200
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    push_response = client.post(
        "/sync/push",
        headers=headers,
        json={
            "batch_id": "ops-stats-batch-1",
            "changes": [
                {
                    "entity": "depots",
                    "operation": "create",
                    "payload": {
                        "name": "Ops Depot",
                        "adresse": "Ops-Weg 1",
                        "telefon": "111",
                        "email": "ops@example.org",
                    },
                }
            ],
        },
    )
    assert push_response.status_code == 200
    assert len(push_response.json()["accepted"]) == 1

    stats_response = client.get("/sync/ops/stats", headers=headers)
    assert stats_response.status_code == 200
    payload = stats_response.json()
    assert payload["total_push_batches"] >= 1
    assert payload["latest_audit_cursor"] >= 1
    assert payload["requested_by"] == "admin"
    assert isinstance(payload.get("latest_push_batch"), dict)
