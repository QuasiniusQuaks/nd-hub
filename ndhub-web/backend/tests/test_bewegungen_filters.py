from __future__ import annotations

import sqlite3

from backend.app import create_app
from fastapi.testclient import TestClient


def _seed_master_and_movements(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO depots (name, adresse, telefon, email) VALUES (?, ?, ?, ?)",
            ("Depot A", "A-Str", "111", "a@example.org"),
        )
        cur.execute(
            "INSERT INTO depots (name, adresse, telefon, email) VALUES (?, ?, ?, ?)",
            ("Depot B", "B-Str", "222", "b@example.org"),
        )
        cur.execute("INSERT INTO praeparate (name) VALUES (?)", ("Praeparat X",))
        cur.execute("INSERT INTO praeparate (name) VALUES (?)", ("Praeparat Y",))
        cur.execute(
            "INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand) VALUES (?, ?, ?)",
            (1, 1, 10),
        )
        cur.execute(
            "INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand) VALUES (?, ?, ?)",
            (2, 2, 10),
        )
        cur.execute(
            """
            INSERT INTO bewegungen (depot_id, praeparat_id, charge, verfall, eingang_datum, ausgang_datum, empfaenger, anzahl, typ)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (1, 1, "A-100", "2027-12-31", "2026-05-01", None, None, 5, "Zugang"),
        )
        cur.execute(
            """
            INSERT INTO bewegungen (depot_id, praeparat_id, charge, verfall, eingang_datum, ausgang_datum, empfaenger, anzahl, typ)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (2, 2, "B-200", "2027-12-30", None, "2026-05-02", "Station 9", 3, "Abgang"),
        )
        conn.commit()
    finally:
        conn.close()


def _admin_headers(client: TestClient) -> dict[str, str]:
    login = client.post("/auth/login", json={"username": "admin", "password": "InitPass!12345"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['token']}"}


def test_bewegungen_supports_depot_filter(monkeypatch, tmp_path):
    db_path = str(tmp_path / "bewegungen_filter.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_master_and_movements(db_path)
    client = TestClient(app)
    headers = _admin_headers(client)

    all_rows = client.get("/bewegungen?limit=100&offset=0", headers=headers)
    assert all_rows.status_code == 200
    assert len(all_rows.json()) >= 2

    depot_a = client.get("/bewegungen?limit=100&offset=0&depot_id=1", headers=headers)
    assert depot_a.status_code == 200
    depot_a_rows = depot_a.json()
    assert len(depot_a_rows) == 1
    assert all(int(row["depot_id"]) == 1 for row in depot_a_rows)

    depot_b_abgang = client.get(
        "/bewegungen?limit=100&offset=0&depot_id=2&typ=Abgang",
        headers=headers,
    )
    assert depot_b_abgang.status_code == 200
    depot_b_rows = depot_b_abgang.json()
    assert len(depot_b_rows) == 1
    assert int(depot_b_rows[0]["depot_id"]) == 2
    assert depot_b_rows[0]["typ"] == "Abgang"


def test_bewegungen_supports_has_attachment_filter(monkeypatch, tmp_path):
    db_path = str(tmp_path / "bewegungen_attachment_filter.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_master_and_movements(db_path)
    client = TestClient(app)
    headers = _admin_headers(client)

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("UPDATE bewegungen SET datei_pfad = ?, datei_name = ? WHERE charge = ?", ("/tmp/test.pdf", "test.pdf", "A-100"))
        conn.commit()
    finally:
        conn.close()

    all_rows = client.get("/bewegungen?limit=100&offset=0", headers=headers)
    assert all_rows.status_code == 200
    assert len(all_rows.json()) >= 2

    with_pdf = client.get("/bewegungen?limit=100&offset=0&has_attachment=1", headers=headers)
    assert with_pdf.status_code == 200
    rows = with_pdf.json()
    assert len(rows) == 1
    assert rows[0]["charge"] == "A-100"
    assert rows[0]["has_attachment"] in {1, True}


def test_bewegungen_supports_praeparat_filter(monkeypatch, tmp_path):
    db_path = str(tmp_path / "bewegungen_praeparat_filter.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_master_and_movements(db_path)
    client = TestClient(app)
    headers = _admin_headers(client)

    only_praeparat_x = client.get("/bewegungen?limit=100&offset=0&praeparat_id=1", headers=headers)
    assert only_praeparat_x.status_code == 200
    rows_x = only_praeparat_x.json()
    assert len(rows_x) == 1
    assert all(int(row["praeparat_id"]) == 1 for row in rows_x)

    only_praeparat_y_abgang = client.get(
        "/bewegungen?limit=100&offset=0&praeparat_id=2&typ=Abgang",
        headers=headers,
    )
    assert only_praeparat_y_abgang.status_code == 200
    rows_y = only_praeparat_y_abgang.json()
    assert len(rows_y) == 1
    assert int(rows_y[0]["praeparat_id"]) == 2
    assert rows_y[0]["typ"] == "Abgang"


def test_bewegungen_supports_date_range_filter(monkeypatch, tmp_path):
    db_path = str(tmp_path / "bewegungen_date_filter.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_master_and_movements(db_path)
    client = TestClient(app)
    headers = _admin_headers(client)

    may_first = client.get(
        "/bewegungen?limit=100&offset=0&start_date=2026-05-01&end_date=2026-05-01",
        headers=headers,
    )
    assert may_first.status_code == 200
    rows_first = may_first.json()
    assert len(rows_first) == 1
    assert rows_first[0]["charge"] == "A-100"

    may_second = client.get(
        "/bewegungen?limit=100&offset=0&start_date=2026-05-02&end_date=2026-05-02",
        headers=headers,
    )
    assert may_second.status_code == 200
    rows_second = may_second.json()
    assert len(rows_second) == 1
    assert rows_second[0]["charge"] == "B-200"


def test_bewegungen_export_csv_respects_filters(monkeypatch, tmp_path):
    db_path = str(tmp_path / "bewegungen_export_filter.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_master_and_movements(db_path)
    client = TestClient(app)
    headers = _admin_headers(client)

    export = client.get(
        "/bewegungen/export.csv?depot_id=1&typ=Zugang&start_date=2026-05-01&end_date=2026-05-01",
        headers=headers,
    )
    assert export.status_code == 200
    assert "text/csv" in export.headers.get("content-type", "")
    csv_text = export.text
    assert "A-100" in csv_text
    assert "B-200" not in csv_text


def test_bewegung_attachment_upload_and_download_roundtrip(monkeypatch, tmp_path):
    db_path = str(tmp_path / "bewegungen_attachment_roundtrip.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_master_and_movements(db_path)
    client = TestClient(app)
    headers = _admin_headers(client)

    pdf_bytes = b"%PDF-1.4\n%Test\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload = client.post(
        "/bewegungen/1/attachment",
        files={"file": ("beleg.pdf", pdf_bytes, "application/pdf")},
        headers=headers,
    )
    assert upload.status_code == 201
    assert upload.json().get("status") == "attachment_saved"

    rows = client.get("/bewegungen?limit=100&offset=0&has_attachment=1", headers=headers)
    assert rows.status_code == 200
    with_attachment = rows.json()
    assert any(int(row.get("id") or 0) == 1 for row in with_attachment)

    opened = client.get("/bewegungen/1/attachment", headers=headers)
    assert opened.status_code == 200
    assert "application/pdf" in opened.headers.get("content-type", "")
    assert opened.content.startswith(b"%PDF")

    downloaded = client.get("/bewegungen/1/attachment?download=true", headers=headers)
    assert downloaded.status_code == 200
    disposition = downloaded.headers.get("content-disposition", "")
    assert "attachment" in disposition.lower()
    assert "beleg.pdf" in disposition


def test_bewegung_attachment_validation_and_missing_file_errors(monkeypatch, tmp_path):
    db_path = str(tmp_path / "bewegungen_attachment_errors.db")
    monkeypatch.setenv("ND_HUB_INITIAL_ADMIN_PASSWORD", "InitPass!12345")
    app = create_app(db_path=db_path)
    _seed_master_and_movements(db_path)
    client = TestClient(app)
    headers = _admin_headers(client)

    wrong_type = client.post(
        "/bewegungen/1/attachment",
        files={"file": ("not_pdf.txt", b"plain text", "text/plain")},
        headers=headers,
    )
    assert wrong_type.status_code == 400
    assert wrong_type.json().get("detail") == "Nur PDF-Dateien sind erlaubt."

    missing_attachment = client.get("/bewegungen/2/attachment", headers=headers)
    assert missing_attachment.status_code == 404
    assert missing_attachment.json().get("detail") == "Kein PDF-Anhang vorhanden."
