from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import create_app


def _login(client: TestClient, username: str, password: str) -> dict:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()


def _admin_headers(client: TestClient) -> dict[str, str]:
    payload = _login(client, "admin", "InitPass!12345")
    return {"Authorization": f"Bearer {payload['token']}"}


def test_auth_requires_bearer_token(monkeypatch, tmp_path):
    db_path = str(tmp_path / "stability_auth_required.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    client = TestClient(app)

    missing = client.get("/auth/me")
    assert missing.status_code == 401
    assert missing.json().get("detail") == "Missing bearer token."

    invalid = client.get("/auth/me", headers={"Authorization": "Bearer definitely-invalid"})
    assert invalid.status_code == 401
    assert invalid.json().get("detail") == "Invalid or expired token."


def test_logout_revokes_token(monkeypatch, tmp_path):
    db_path = str(tmp_path / "stability_logout.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    client = TestClient(app)
    token_payload = _login(client, "admin", "InitPass!12345")
    headers = {"Authorization": f"Bearer {token_payload['token']}"}

    me_before = client.get("/auth/me", headers=headers)
    assert me_before.status_code == 200

    logout = client.post("/auth/logout", headers=headers)
    assert logout.status_code == 200
    assert logout.json().get("status") == "logged_out"

    me_after = client.get("/auth/me", headers=headers)
    assert me_after.status_code == 401
    assert me_after.json().get("detail") == "Invalid or expired token."


def test_session_token_invalid_after_app_restart(monkeypatch, tmp_path):
    db_path = str(tmp_path / "stability_restart.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")

    app_first = create_app(db_path=db_path)
    client_first = TestClient(app_first)
    first_login = _login(client_first, "admin", "InitPass!12345")
    stale_headers = {"Authorization": f"Bearer {first_login['token']}"}
    assert client_first.get("/auth/me", headers=stale_headers).status_code == 200

    # New app instance simulates process restart with fresh in-memory token store.
    app_second = create_app(db_path=db_path)
    client_second = TestClient(app_second)
    stale_check = client_second.get("/auth/me", headers=stale_headers)
    assert stale_check.status_code == 401
    assert stale_check.json().get("detail") == "Invalid or expired token."

    relogin = _login(client_second, "admin", "InitPass!12345")
    fresh_headers = {"Authorization": f"Bearer {relogin['token']}"}
    assert client_second.get("/auth/me", headers=fresh_headers).status_code == 200


def test_permission_enforcement_for_reports(monkeypatch, tmp_path):
    db_path = str(tmp_path / "stability_permissions.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    client = TestClient(app)
    admin_headers = _admin_headers(client)

    create_user = client.post(
        "/users",
        json={
            "username": "viewer_without_reports",
            "password": "StrongPass123"  # gitleaks:allow,
            "role": "User",
            "email": "viewer@example.org",
            "is_active": True,
            "permissions": ["masterdata_read", "movements_read"],
        },
        headers=admin_headers,
    )
    assert create_user.status_code == 201

    restricted_login = _login(client, "viewer_without_reports", "StrongPass123"  # gitleaks:allow)
    restricted_headers = {"Authorization": f"Bearer {restricted_login['token']}"}
    denied = client.get("/reports/matrix", headers=restricted_headers)
    assert denied.status_code == 403
    assert denied.json().get("detail") == "Berechtigung fehlt."
