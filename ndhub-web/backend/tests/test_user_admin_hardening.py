from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import create_app


def _admin_headers(client: TestClient) -> dict[str, str]:
    login = client.post("/auth/login", json={"username": "admin", "password": "InitPass!12345"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['token']}"}


def _login_headers(client: TestClient, username: str, password: str) -> dict[str, str]:
    login = client.post("/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['token']}"}


def _get_user_id_by_name(client: TestClient, headers: dict[str, str], username: str) -> int:
    users = client.get("/users", headers=headers)
    assert users.status_code == 200
    for row in users.json():
        if str(row.get("username")) == username:
            return int(row["id"])
    raise AssertionError(f"user not found: {username}")


def _create_admin_user(client: TestClient, headers: dict[str, str], username: str) -> int:
    created = client.post(
        "/users",
        json={
            "username": username,
            "password": "StrongPass123",  # gitleaks:allow
            "role": "Admin",
            "email": f"{username}@example.org",
            "is_active": True,
            "permissions": [],
        },
        headers=headers,
    )
    assert created.status_code == 201
    return int(created.json()["id"])


def test_cannot_downgrade_last_active_admin(monkeypatch, tmp_path):
    db_path = str(tmp_path / "user_admin_last_admin.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    client = TestClient(app)
    admin_headers = _admin_headers(client)
    admin_id = _get_user_id_by_name(client, admin_headers, "admin")
    manager_user = client.post(
        "/users",
        json={
            "username": "manager",
            "password": "StrongPass123",  # gitleaks:allow
            "role": "User",
            "email": "manager@example.org",
            "is_active": True,
            "permissions": ["users_manage"],
        },
        headers=admin_headers,
    )
    assert manager_user.status_code == 201
    manager_headers = _login_headers(client, "manager", "StrongPass123")  # gitleaks:allow

    response = client.put(
        f"/users/{admin_id}",
        json={"role": "User"},
        headers=manager_headers,
    )
    assert response.status_code == 400
    assert response.json().get("detail") == "Letzter aktiver Admin darf nicht herabgestuft oder deaktiviert werden."


def test_can_downgrade_other_admin_when_not_last(monkeypatch, tmp_path):
    db_path = str(tmp_path / "user_admin_not_last.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    client = TestClient(app)
    headers = _admin_headers(client)
    target_id = _create_admin_user(client, headers, "admin2")

    response = client.put(
        f"/users/{target_id}",
        json={"role": "User"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json().get("role") == "User"


def test_cannot_self_deactivate_even_with_second_admin(monkeypatch, tmp_path):
    db_path = str(tmp_path / "user_admin_self_deactivate.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    client = TestClient(app)
    headers = _admin_headers(client)
    _create_admin_user(client, headers, "admin2")
    admin_id = _get_user_id_by_name(client, headers, "admin")

    response = client.put(
        f"/users/{admin_id}",
        json={"is_active": False},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json().get("detail") == "Sie können sich nicht selbst deaktivieren."
