"""OpenAPI path parity smoke for app factory modularization (Issue #96)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import create_app

# Frozen snapshot of paths present on main before Issue #96 extract.
# Update only when intentionally adding/removing API routes.
EXPECTED_OPENAPI_PATHS = {
    "/",
    "/admin/backup/create",
    "/admin/backup/download",
    "/admin/backup/download/{filename}",
    "/admin/backup/list",
    "/admin/backup/restore",
    "/audit-logs",
    "/auth/activity",
    "/auth/avatar",
    "/auth/change-password",
    "/auth/desktop-sync-token",
    "/auth/desktop-sync-token/revoke",
    "/auth/desktop-sync-tokens",
    "/auth/login",
    "/auth/logout",
    "/auth/me",
    "/bewegungen/",
    "/bewegungen/export.csv",
    "/bewegungen/{bewegung_id}/attachment",
    "/dashboard/overview",
    "/depots/",
    "/depots/{depot_id}",
    "/depots/{depot_id}/kontakte",
    "/depots/{depot_id}/praeparate",
    "/depots/{depot_id}/zuordnungen",
    "/emails/delivery/status",
    "/emails/drafts",
    "/emails/history",
    "/emails/history/{email_id}",
    "/emails/history/{email_id}/delivery-status",
    "/emails/recipients-preview",
    "/geo/geocode",
    "/health",
    "/imports/bewegungen/execute",
    "/imports/bewegungen/preview",
    "/imports/bewegungen/template",
    "/institutions",
    "/institutions/{institution_id}",
    "/kontakte/{kontakt_id}",
    "/map/institutions",
    "/notifications/verfall",
    "/onboarding/institution-setup",
    "/onboarding/status",
    "/permissions/catalog",
    "/praeparate/",
    "/praeparate/{praeparat_id}",
    "/reports/bestand",
    "/reports/bestand/export.csv",
    "/reports/bewegungen",
    "/reports/bewegungen/export.csv",
    "/reports/matrix",
    "/reports/matrix/export.csv",
    "/reports/ranking",
    "/reports/ranking/export.csv",
    "/reports/verfall",
    "/reports/verfall/export.csv",
    "/reports/{report_type}/export.pdf",
    "/reports/{report_type}/export.pptx",
    "/sync/ops/stats",
    "/sync/pull",
    "/sync/push",
    "/sync/status",
    "/users/",
    "/users/depot-permissions",
    "/users/{user_id}",
    "/users/{user_id}/activity",
    "/users/{user_id}/reset-password",
    "/users/{user_id}/unlock",
    "/users/{username}/depot-permissions",
    "/verfall/overview",
    "/verfall/overview/export.csv",
}


def test_openapi_paths_match_expected(tmp_path, monkeypatch):
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "OpenApi!12345")
    monkeypatch.setenv("ND_HUB_AUTO_BACKUP_HOURS", "0")
    app = create_app(db_path=str(tmp_path / "openapi.db"))
    client = TestClient(app)
    payload = client.get("/openapi.json")
    assert payload.status_code == 200
    actual = set(payload.json()["paths"].keys())
    missing = EXPECTED_OPENAPI_PATHS - actual
    extra = actual - EXPECTED_OPENAPI_PATHS
    assert not missing, f"missing paths: {sorted(missing)}"
    assert not extra, f"unexpected paths: {sorted(extra)}"
