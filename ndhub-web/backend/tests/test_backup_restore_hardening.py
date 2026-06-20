from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import create_app


def _admin_headers(client: TestClient) -> dict[str, str]:
    login = client.post("/auth/login", json={"username": "admin", "password": "InitPass!12345"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['token']}"}


def test_backup_list_exposes_restore_limits(monkeypatch, tmp_path):
    db_path = str(tmp_path / "backup_list.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    monkeypatch.setenv("ND_HUB_MAX_BACKUP_RESTORE_MB", "123")
    app = create_app(db_path=db_path)
    client = TestClient(app)
    headers = _admin_headers(client)

    response = client.get("/admin/backup/list?limit=10", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert int(payload["max_restore_size_mb"]) == 123
    assert payload["db_engine"] == "sqlite"
    assert isinstance(payload.get("rows"), list)


def test_backup_restore_rejects_non_sqlite_file(monkeypatch, tmp_path):
    db_path = str(tmp_path / "backup_restore_invalid.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    client = TestClient(app)
    headers = _admin_headers(client)

    restore = client.post(
        "/admin/backup/restore",
        files={"file": ("broken.db", b"not-a-sqlite-database", "application/octet-stream")},
        headers=headers,
    )
    assert restore.status_code == 400
    assert restore.json().get("detail") == "Backup-Datei ist keine gueltige SQLite-Datei."


def test_backup_restore_rejects_oversized_upload(monkeypatch, tmp_path):
    db_path = str(tmp_path / "backup_restore_too_large.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    monkeypatch.setenv("ND_HUB_MAX_BACKUP_RESTORE_MB", "1")
    app = create_app(db_path=db_path)
    client = TestClient(app)
    headers = _admin_headers(client)

    too_large = b"x" * (1024 * 1024 + 64)
    restore = client.post(
        "/admin/backup/restore",
        files={"file": ("large.db", too_large, "application/octet-stream")},
        headers=headers,
    )
    assert restore.status_code == 400
    assert "zu gross" in (restore.json().get("detail") or "")
