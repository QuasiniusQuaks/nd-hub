import sqlite3
import io
import json
from datetime import date, timedelta

from fastapi.testclient import TestClient

from backend.app import create_app
from security_manager import SecurityManager


def _seed_master_data(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO depots (name, adresse, telefon, email) VALUES (?, ?, ?, ?)",
            ("Depot Nord", "Testweg 1", "123", "nord@example.org"),
        )
        cur.execute(
            "INSERT INTO praeparate (name) VALUES (?)",
            ("Praeparat A",),
        )
        cur.execute(
            "INSERT INTO praeparate (name) VALUES (?)",
            ("Praeparat B",),
        )
        cur.execute(
            "INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand) VALUES (?, ?, ?)",
            (1, 1, 10),
        )
        conn.commit()
    finally:
        conn.close()


def _seed_regular_user(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (username, password_hash, role, created_at, is_active)
            VALUES (?, ?, 'User', '2026-01-01 00:00:00', 1)
            """,
            ("readonly", SecurityManager.hash_password("UserPass!123")),
        )
        conn.commit()
    finally:
        conn.close()


def _seed_user_with_permissions(db_path: str, username: str, password: str, permissions: list[str]) -> None:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (username, password_hash, role, created_at, is_active, permissions)
            VALUES (?, ?, 'User', '2026-01-01 00:00:00', 1, ?)
            """,
            (
                username,
                SecurityManager.hash_password(password),
                json.dumps(permissions),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def test_health_and_login_flow(monkeypatch, tmp_path):
    db_path = str(tmp_path / "api.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_master_data(db_path)
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "InitPass!12345"},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    assert token

    headers = {"Authorization": f"Bearer {token}"}

    depots = client.get("/depots", headers=headers)
    assert depots.status_code == 200
    assert depots.json()[0]["name"] == "Depot Nord"

    praeparate = client.get("/praeparate", headers=headers)
    assert praeparate.status_code == 200
    assert praeparate.json()[0]["name"] == "Praeparat A"
    depot_praeparate = client.get("/depots/1/praeparate", headers=headers)
    assert depot_praeparate.status_code == 200
    assert [row["name"] for row in depot_praeparate.json()] == ["Praeparat A"]


def test_web_client_is_served(monkeypatch, tmp_path):
    db_path = str(tmp_path / "api_web.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    client = TestClient(app)

    index = client.get("/")
    assert index.status_code == 200
    assert "ND-Hub Web MVP" in index.text

    js = client.get("/web/app.js")
    assert js.status_code == 200
    assert "TOKEN_KEY" in js.text


def test_create_bewegung_requires_auth(monkeypatch, tmp_path):
    db_path = str(tmp_path / "api_auth.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    client = TestClient(app)

    response = client.get("/bewegungen")
    assert response.status_code == 401


def test_masterdata_crud(monkeypatch, tmp_path):
    db_path = str(tmp_path / "api_crud.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    client = TestClient(app)

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "InitPass!12345"},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_depot = client.post(
        "/depots",
        headers=headers,
        json={
            "name": "Depot Sued",
            "adresse": "Musterstrasse 9",
            "telefon": "555-01",
            "email": "sued@example.org",
        },
    )
    assert create_depot.status_code == 201
    depot_id = create_depot.json()["id"]

    update_depot = client.put(
        f"/depots/{depot_id}",
        headers=headers,
        json={
            "name": "Depot Sued Neu",
            "adresse": "Musterstrasse 10",
            "telefon": "555-02",
            "email": "sued-neu@example.org",
        },
    )
    assert update_depot.status_code == 200

    create_praeparat = client.post(
        "/praeparate",
        headers=headers,
        json={"name": "Praeparat B"},
    )
    assert create_praeparat.status_code == 201
    praeparat_id = create_praeparat.json()["id"]

    update_praeparat = client.put(
        f"/praeparate/{praeparat_id}",
        headers=headers,
        json={"name": "Praeparat B Plus"},
    )
    assert update_praeparat.status_code == 200

    depots = client.get("/depots", headers=headers)
    assert depots.status_code == 200
    assert any(row["name"] == "Depot Sued Neu" for row in depots.json())

    praeparate = client.get("/praeparate", headers=headers)
    assert praeparate.status_code == 200
    assert any(row["name"] == "Praeparat B Plus" for row in praeparate.json())

    delete_praeparat = client.delete(f"/praeparate/{praeparat_id}", headers=headers)
    assert delete_praeparat.status_code == 200

    delete_depot = client.delete(f"/depots/{depot_id}", headers=headers)
    assert delete_depot.status_code == 200

    audit_logs = client.get("/audit-logs?limit=20", headers=headers)
    assert audit_logs.status_code == 200
    actions = audit_logs.json()
    assert any(row["resource_type"] == "depot" and row["action"] == "create" for row in actions)
    assert any(row["resource_type"] == "praeparat" and row["action"] == "update" for row in actions)
    filtered = client.get(
        "/audit-logs?resource_type=depot&action=create&q=Depot",
        headers=headers,
    )
    assert filtered.status_code == 200
    filtered_rows = filtered.json()
    assert all(row["resource_type"] == "depot" for row in filtered_rows)


def test_non_admin_cannot_modify_masterdata(monkeypatch, tmp_path):
    db_path = str(tmp_path / "api_non_admin.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_regular_user(db_path)
    client = TestClient(app)

    login = client.post(
        "/auth/login",
        json={"username": "readonly", "password": "UserPass!123"},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_depot = client.post(
        "/depots",
        headers=headers,
        json={"name": "Nicht erlaubt"},
    )
    assert create_depot.status_code == 403

    audit_logs = client.get("/audit-logs", headers=headers)
    assert audit_logs.status_code == 403


def test_granular_permissions_are_enforced(monkeypatch, tmp_path):
    db_path = str(tmp_path / "api_permissions.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_master_data(db_path)
    _seed_user_with_permissions(db_path, "reporter", "ReporterPass!1", ["reports_view"])
    client = TestClient(app)

    login = client.post(
        "/auth/login",
        json={"username": "reporter", "password": "ReporterPass!1"},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    depots = client.get("/depots", headers=headers)
    assert depots.status_code == 403

    movements = client.get("/bewegungen", headers=headers)
    assert movements.status_code == 403

    reports = client.get("/reports/matrix", headers=headers)
    assert reports.status_code == 200


def test_permission_catalog_and_user_permissions_payload(monkeypatch, tmp_path):
    db_path = str(tmp_path / "api_permission_catalog.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    client = TestClient(app)

    admin_login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "InitPass!12345"},
    )
    assert admin_login.status_code == 200
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['token']}"}

    catalog = client.get("/permissions/catalog", headers=admin_headers)
    assert catalog.status_code == 200
    catalog_json = catalog.json()
    assert len(catalog_json["rows"]) >= 5
    assert len(catalog_json["templates"]) >= 2

    created = client.post(
        "/users",
        headers=admin_headers,
        json={
            "username": "templated_user",
            "password": "Templated!123",
            "role": "User",
            "permissions": ["reports_view", "movements_read"],
            "is_active": True,
        },
    )
    assert created.status_code == 201

    user_login = client.post(
        "/auth/login",
        json={"username": "templated_user", "password": "Templated!123"},
    )
    assert user_login.status_code == 200
    payload = user_login.json()
    assert "reports_view" in payload["permissions"]
    assert "movements_read" in payload["permissions"]


def test_invalid_date_in_bewegung_is_rejected(monkeypatch, tmp_path):
    db_path = str(tmp_path / "api_date_validation.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_master_data(db_path)
    client = TestClient(app)

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "InitPass!12345"},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    movement = client.post(
        "/bewegungen",
        headers=headers,
        json={
            "depot_id": 1,
            "praeparat_id": 1,
            "typ": "Zugang",
            "charge": "C-100",
            "verfall": "31-12-2027",
            "datum": "2026-04-22",
            "anzahl": 5,
            "empfaenger": None,
        },
    )
    assert movement.status_code == 422


def test_bewegung_rejects_unassigned_praeparat(monkeypatch, tmp_path):
    db_path = str(tmp_path / "api_assignment_validation.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_master_data(db_path)
    client = TestClient(app)

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "InitPass!12345"},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    movement = client.post(
        "/bewegungen",
        headers=headers,
        json={
            "depot_id": 1,
            "praeparat_id": 2,
            "typ": "Zugang",
            "charge": "C-200",
            "verfall": "2027-12-31",
            "datum": "2026-04-22",
            "anzahl": 5,
            "empfaenger": None,
        },
    )
    assert movement.status_code == 400
    assert "nicht zugeordnet" in movement.json()["detail"]


def test_bewegung_attachment_upload_and_download(monkeypatch, tmp_path):
    db_path = str(tmp_path / "api_attachment.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_master_data(db_path)
    client = TestClient(app)

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "InitPass!12345"},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    movement = client.post(
        "/bewegungen",
        headers=headers,
        json={
            "depot_id": 1,
            "praeparat_id": 1,
            "typ": "Zugang",
            "charge": "C-300",
            "verfall": "2027-12-31",
            "datum": "2026-04-22",
            "anzahl": 5,
            "empfaenger": None,
        },
    )
    assert movement.status_code == 201
    bewegung_id = movement.json()["id"]

    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload = client.post(
        f"/bewegungen/{bewegung_id}/attachment",
        headers=headers,
        files={"file": ("beleg.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload.status_code == 201

    bewegungen = client.get("/bewegungen", headers=headers)
    assert bewegungen.status_code == 200
    row = next(item for item in bewegungen.json() if item["id"] == bewegung_id)
    assert row["has_attachment"] == 1
    assert row["datei_name"] == "beleg.pdf"
    assert row["datei_groesse"] > 0

    inline_view = client.get(f"/bewegungen/{bewegung_id}/attachment", headers=headers)
    assert inline_view.status_code == 200
    assert inline_view.headers["content-type"].startswith("application/pdf")
    assert b"%PDF-1.4" in inline_view.content

    download = client.get(f"/bewegungen/{bewegung_id}/attachment?download=true", headers=headers)
    assert download.status_code == 200
    assert "attachment;" in download.headers.get("content-disposition", "")


def test_assignments_and_kontakte_crud(monkeypatch, tmp_path):
    db_path = str(tmp_path / "api_settings.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_master_data(db_path)
    client = TestClient(app)

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "InitPass!12345"},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    list_assignments = client.get("/depots/1/zuordnungen", headers=headers)
    assert list_assignments.status_code == 200
    assert any(row["praeparat_name"] == "Praeparat A" for row in list_assignments.json())
    assert any(row["praeparat_name"] == "Praeparat B" for row in list_assignments.json())

    update_assignments = client.put(
        "/depots/1/zuordnungen",
        headers=headers,
        json={
            "assignments": [
                {"praeparat_id": 2, "sollbestand": 11},
            ]
        },
    )
    assert update_assignments.status_code == 200

    assigned_after_update = client.get("/depots/1/praeparate", headers=headers)
    assert assigned_after_update.status_code == 200
    assert [row["id"] for row in assigned_after_update.json()] == [2]

    create_kontakt = client.post(
        "/depots/1/kontakte",
        headers=headers,
        json={
            "name": "Max Mustermann",
            "rolle": "Leitung",
            "telefon": "12345",
            "email": "max@example.org",
        },
    )
    assert create_kontakt.status_code == 201
    kontakt_id = create_kontakt.json()["id"]

    kontakte = client.get("/depots/1/kontakte", headers=headers)
    assert kontakte.status_code == 200
    assert any(row["id"] == kontakt_id and row["name"] == "Max Mustermann" for row in kontakte.json())

    update_kontakt = client.put(
        f"/kontakte/{kontakt_id}",
        headers=headers,
        json={
            "name": "Max M.",
            "rolle": "Backup",
            "telefon": "98765",
            "email": "maxm@example.org",
        },
    )
    assert update_kontakt.status_code == 200

    delete_kontakt = client.delete(f"/kontakte/{kontakt_id}", headers=headers)
    assert delete_kontakt.status_code == 200


def test_import_preview_execute_and_template(monkeypatch, tmp_path):
    db_path = str(tmp_path / "api_import.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_master_data(db_path)
    client = TestClient(app)

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "InitPass!12345"},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    csv_content = (
        "Depot,Praeparat,Typ,Charge,Verfall,Datum,Anzahl,Empfaenger\n"
        "Depot Nord,Praeparat A,Zugang,C-400,2027-12-31,2026-04-22,4,\n"
        "Depot Nord,Praeparat A,Abgang,C-401,2027-12-30,2026-04-23,2,Station 3\n"
    )
    preview = client.post(
        "/imports/bewegungen/preview",
        headers=headers,
        files={"file": ("bewegungen.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert preview.status_code == 200
    preview_json = preview.json()
    assert preview_json["valid_rows"] == 2
    assert preview_json["error_count"] == 0

    execute = client.post(
        "/imports/bewegungen/execute",
        headers=headers,
        files={"file": ("bewegungen.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert execute.status_code == 200
    execute_json = execute.json()
    assert execute_json["imported"] == 2
    assert execute_json["error_count"] == 0

    movements = client.get("/bewegungen", headers=headers)
    assert movements.status_code == 200
    charges = {row["charge"] for row in movements.json()}
    assert "C-400" in charges
    assert "C-401" in charges

    template = client.get("/imports/bewegungen/template", headers=headers)
    assert template.status_code == 200
    assert template.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_email_draft_flow_and_history(monkeypatch, tmp_path):
    db_path = str(tmp_path / "api_email.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_master_data(db_path)
    client = TestClient(app)

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "InitPass!12345"},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_kontakt = client.post(
        "/depots/1/kontakte",
        headers=headers,
        json={
            "name": "Mara Kontakt",
            "rolle": "Apotheke",
            "telefon": "555-123",
            "email": "mara@example.org",
        },
    )
    assert create_kontakt.status_code == 201

    preview = client.post(
        "/emails/recipients-preview",
        headers=headers,
        json={"depot_ids": [1]},
    )
    assert preview.status_code == 200
    assert preview.json()["count"] == 1

    create_draft = client.post(
        "/emails/drafts",
        headers=headers,
        json={
            "depot_ids": [1],
            "betreff": "Inventur-Check",
            "nachricht": "Bitte Bestand pruefen.",
        },
    )
    assert create_draft.status_code == 201
    draft_id = create_draft.json()["id"]
    assert create_draft.json()["recipient_count"] == 1

    history = client.get("/emails/history?limit=20", headers=headers)
    assert history.status_code == 200
    assert any(entry["id"] == draft_id for entry in history.json())

    details = client.get(f"/emails/history/{draft_id}", headers=headers)
    assert details.status_code == 200
    detail_json = details.json()
    assert detail_json["betreff"] == "Inventur-Check"
    assert "mara@example.org" in detail_json["empfaenger_emails"]


def test_reports_and_csv_exports(monkeypatch, tmp_path):
    db_path = str(tmp_path / "api_reports.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_master_data(db_path)
    client = TestClient(app)

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "InitPass!12345"},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    for payload in [
        {
            "depot_id": 1,
            "praeparat_id": 1,
            "typ": "Zugang",
            "charge": "R-001",
            "verfall": "2027-12-31",
            "datum": "2026-03-01",
            "anzahl": 10,
            "empfaenger": None,
        },
        {
            "depot_id": 1,
            "praeparat_id": 1,
            "typ": "Abgang",
            "charge": "R-002",
            "verfall": "2027-12-30",
            "datum": "2026-03-15",
            "anzahl": 3,
            "empfaenger": "Station X",
        },
    ]:
        movement = client.post("/bewegungen", headers=headers, json=payload)
        assert movement.status_code == 201

    bewegungen_report = client.get(
        "/reports/bewegungen?perspective=depot&ids=1&start_date=2026-01-01&end_date=2026-12-31",
        headers=headers,
    )
    assert bewegungen_report.status_code == 200
    assert bewegungen_report.json()["kpis"]["gesamt"] == 13

    bestand_report = client.get(
        "/reports/bestand?perspective=depot&ids=1",
        headers=headers,
    )
    assert bestand_report.status_code == 200
    assert len(bestand_report.json()["rows"]) >= 1

    ranking_report = client.get(
        "/reports/ranking?perspective=depot&ids=1&start_date=2026-01-01&end_date=2026-12-31",
        headers=headers,
    )
    assert ranking_report.status_code == 200
    assert len(ranking_report.json()["rows"]) >= 1

    matrix_report = client.get("/reports/matrix", headers=headers)
    assert matrix_report.status_code == 200
    assert len(matrix_report.json()["rows"]) >= 1

    verfall_report = client.get("/reports/verfall?perspective=depot&ids=1&horizon_months=24", headers=headers)
    assert verfall_report.status_code == 200
    assert len(verfall_report.json()["rows"]) >= 1

    bewegungen_csv = client.get(
        "/reports/bewegungen/export.csv?perspective=depot&ids=1&start_date=2026-01-01&end_date=2026-12-31",
        headers=headers,
    )
    assert bewegungen_csv.status_code == 200
    assert "text/csv" in bewegungen_csv.headers["content-type"]
    assert "Monat" in bewegungen_csv.text

    bewegungen_pdf = client.get(
        "/reports/bewegungen/export.pdf?perspective=depot&ids=1&start_date=2026-01-01&end_date=2026-12-31",
        headers=headers,
    )
    assert bewegungen_pdf.status_code in {200, 503}
    if bewegungen_pdf.status_code == 200:
        assert "application/pdf" in bewegungen_pdf.headers["content-type"]

    bewegungen_pptx = client.get(
        "/reports/bewegungen/export.pptx?perspective=depot&ids=1&start_date=2026-01-01&end_date=2026-12-31",
        headers=headers,
    )
    assert bewegungen_pptx.status_code in {200, 503}
    if bewegungen_pptx.status_code == 200:
        assert "application/vnd.openxmlformats-officedocument.presentationml.presentation" in bewegungen_pptx.headers["content-type"]


def test_dashboard_verfall_and_notifications_endpoints(monkeypatch, tmp_path):
    db_path = str(tmp_path / "api_dashboard_verfall.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_master_data(db_path)
    client = TestClient(app)

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "InitPass!12345"},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    near_expiry = (date.today() + timedelta(days=10)).isoformat()
    mid_expiry = (date.today() + timedelta(days=45)).isoformat()
    today = date.today().isoformat()
    for payload in [
        {
            "depot_id": 1,
            "praeparat_id": 1,
            "typ": "Zugang",
            "charge": "DASH-001",
            "verfall": near_expiry,
            "datum": today,
            "anzahl": 5,
            "empfaenger": None,
        },
        {
            "depot_id": 1,
            "praeparat_id": 1,
            "typ": "Zugang",
            "charge": "DASH-002",
            "verfall": mid_expiry,
            "datum": today,
            "anzahl": 3,
            "empfaenger": None,
        },
    ]:
        movement = client.post("/bewegungen", headers=headers, json=payload)
        assert movement.status_code == 201

    dashboard = client.get("/dashboard/overview", headers=headers)
    assert dashboard.status_code == 200
    dashboard_json = dashboard.json()
    assert dashboard_json["kpis"]["depots"] >= 1
    assert dashboard_json["kpis"]["praeparate"] >= 1
    assert len(dashboard_json["recent_activity"]) >= 1
    assert len(dashboard_json["expiry_preview"]) >= 1

    verfall_overview = client.get(
        "/verfall/overview?perspective=depot&ids=1&category=kritisch",
        headers=headers,
    )
    assert verfall_overview.status_code == 200
    rows = verfall_overview.json()["rows"]
    assert all(row["kategorie"] == "kritisch" for row in rows)

    verfall_csv = client.get(
        "/verfall/overview/export.csv?perspective=depot&ids=1&category=alle",
        headers=headers,
    )
    assert verfall_csv.status_code == 200
    assert "text/csv" in verfall_csv.headers["content-type"]
    assert "Kategorie" in verfall_csv.text

    notifications = client.get(
        "/notifications/verfall?since=2000-01-01T00:00:00Z&limit=20",
        headers=headers,
    )
    assert notifications.status_code == 200
    notifications_json = notifications.json()
    assert "next_since" in notifications_json
    assert notifications_json["counts"]["gesamt"] >= 1


def test_backup_admin_workflow(monkeypatch, tmp_path):
    db_path = str(tmp_path / "api_backup.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    monkeypatch.setenv("ND_HUB_AUTO_BACKUP_HOURS", "1")
    app = create_app(db_path=db_path)
    client = TestClient(app)

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "InitPass!12345"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    backup_list = client.get("/admin/backup/list", headers=headers)
    assert backup_list.status_code == 200
    rows = backup_list.json()["rows"]
    assert isinstance(rows, list)

    create_backup = client.post("/admin/backup/create", headers=headers)
    assert create_backup.status_code == 200
    filename = create_backup.json()["filename"]
    assert filename.startswith("ndhub_manual_")

    download_created = client.get(f"/admin/backup/download/{filename}", headers=headers)
    assert download_created.status_code == 200
    assert len(download_created.content) > 0

    restore = client.post(
        "/admin/backup/restore",
        headers=headers,
        files={"file": (filename, download_created.content, "application/octet-stream")},
    )
    assert restore.status_code == 200
    assert restore.json()["status"] == "restored"


def test_avatar_endpoints(monkeypatch, tmp_path):
    db_path = str(tmp_path / "api_avatar.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    client = TestClient(app)

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "InitPass!12345"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    me_before = client.get("/auth/me", headers=headers)
    assert me_before.status_code == 200
    assert me_before.json()["avatar_available"] is False

    upload = client.post(
        "/auth/avatar",
        headers=headers,
        files={"file": ("avatar.png", b"fakepng", "image/png")},
    )
    assert upload.status_code == 200

    get_avatar = client.get("/auth/avatar", headers=headers)
    assert get_avatar.status_code == 200
    assert "image" in get_avatar.headers.get("content-type", "")

    clear = client.delete("/auth/avatar", headers=headers)
    assert clear.status_code == 200

    me_after = client.get("/auth/me", headers=headers)
    assert me_after.status_code == 200
    assert me_after.json()["avatar_available"] is False

