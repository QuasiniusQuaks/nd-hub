"""SQLite repository mixins (Issue #110)."""

from __future__ import annotations

import sqlite3

ALLOWED_MOVEMENT_TYPES = {"Zugang", "Abgang", "Vernichtung"}


class SqliteSchemaMixin:
    def ensure_schema(self) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS depots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    adresse TEXT,
                    strasse TEXT,
                    hausnummer TEXT,
                    postleitzahl TEXT,
                    stadt TEXT,
                    telefon TEXT,
                    email TEXT,
                    institution_id INTEGER,
                    latitude REAL,
                    longitude REAL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS institutions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    adresse TEXT,
                    strasse TEXT,
                    hausnummer TEXT,
                    postleitzahl TEXT,
                    stadt TEXT,
                    latitude REAL,
                    longitude REAL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_depot_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    depot_id INTEGER NOT NULL,
                    can_read INTEGER NOT NULL DEFAULT 0,
                    can_write INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(username, depot_id),
                    FOREIGN KEY(depot_id) REFERENCES depots(id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS praeparate (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    wirkstoff TEXT,
                    darreichungsform TEXT,
                    staerke TEXT,
                    einheit TEXT,
                    pzn TEXT,
                    hersteller TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS depot_praeparate (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    depot_id INTEGER,
                    praeparat_id INTEGER,
                    sollbestand INTEGER DEFAULT 0,
                    FOREIGN KEY(depot_id) REFERENCES depots(id),
                    FOREIGN KEY(praeparat_id) REFERENCES praeparate(id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS bewegungen (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    depot_id INTEGER,
                    praeparat_id INTEGER,
                    charge TEXT,
                    verfall TEXT,
                    eingang_datum TEXT,
                    ausgang_datum TEXT,
                    empfaenger TEXT,
                    anzahl INTEGER,
                    typ TEXT CHECK(typ IN ('Zugang','Abgang','Vernichtung')),
                    datei_pfad TEXT,
                    datei_name TEXT,
                    datei_groesse INTEGER,
                    datei_hochgeladen_am TEXT,
                    FOREIGN KEY(depot_id) REFERENCES depots(id),
                    FOREIGN KEY(praeparat_id) REFERENCES praeparate(id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS kontakte (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    depot_id INTEGER,
                    name TEXT,
                    rolle TEXT,
                    telefon TEXT,
                    email TEXT,
                    FOREIGN KEY(depot_id) REFERENCES depots(id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS email_verlauf (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    datum TEXT,
                    betreff TEXT,
                    nachricht TEXT,
                    empfaenger_depots TEXT,
                    empfaenger_emails TEXT,
                    anzahl_empfaenger INTEGER,
                    versand_status TEXT DEFAULT 'draft',
                    versand_kanal TEXT,
                    versand_fehler TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS api_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    username TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id INTEGER,
                    details TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_push_batches (
                    batch_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    result_json TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS import_batches (
                    batch_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    result_json TEXT NOT NULL
                )
                """
            )
            self._ensure_bewegung_attachment_columns(cur)
            self._ensure_email_verlauf_columns(cur)
            self._ensure_institution_columns(cur)
            self._ensure_address_split_columns(cur)
            self._ensure_praeparat_columns(cur)
            conn.commit()

    def _ensure_bewegung_attachment_columns(self, cur: sqlite3.Cursor) -> None:
        rows = cur.execute("PRAGMA table_info(bewegungen)").fetchall()
        existing = {row[1] for row in rows}
        required_columns = {
            "datei_pfad": "TEXT",
            "datei_name": "TEXT",
            "datei_groesse": "INTEGER",
            "datei_hochgeladen_am": "TEXT",
        }
        for column_name, column_type in required_columns.items():
            if column_name in existing:
                continue
            cur.execute(f"ALTER TABLE bewegungen ADD COLUMN {column_name} {column_type}")

    def _ensure_email_verlauf_columns(self, cur: sqlite3.Cursor) -> None:
        rows = cur.execute("PRAGMA table_info(email_verlauf)").fetchall()
        existing = {row[1] for row in rows}
        required_columns = {
            "versand_status": "TEXT DEFAULT 'draft'",
            "versand_kanal": "TEXT",
            "versand_fehler": "TEXT",
        }
        for column_name, column_type in required_columns.items():
            if column_name in existing:
                continue
            cur.execute(f"ALTER TABLE email_verlauf ADD COLUMN {column_name} {column_type}")

    def _ensure_institution_columns(self, cur: sqlite3.Cursor) -> None:
        rows = cur.execute("PRAGMA table_info(depots)").fetchall()
        existing = {row[1] for row in rows}
        if "institution_id" not in existing:
            cur.execute("ALTER TABLE depots ADD COLUMN institution_id INTEGER")
        if "latitude" not in existing:
            cur.execute("ALTER TABLE depots ADD COLUMN latitude REAL")
        if "longitude" not in existing:
            cur.execute("ALTER TABLE depots ADD COLUMN longitude REAL")
        default_row = cur.execute("SELECT id FROM institutions ORDER BY id ASC LIMIT 1").fetchone()
        if default_row is None:
            cur.execute(
                "INSERT INTO institutions (name, adresse, latitude, longitude) VALUES (?, ?, ?, ?)",
                ("Standard-Institution", None, None, None),
            )
            default_id = int(cur.lastrowid)
        else:
            default_id = int(default_row[0])
        cur.execute(
            "UPDATE depots SET institution_id = ? WHERE institution_id IS NULL",
            (default_id,),
        )

    def _ensure_praeparat_columns(self, cur: sqlite3.Cursor) -> None:
        rows = cur.execute("PRAGMA table_info(praeparate)").fetchall()
        existing = {row[1] for row in rows}
        required_columns = {
            "wirkstoff": "TEXT",
            "darreichungsform": "TEXT",
            "staerke": "TEXT",
            "einheit": "TEXT",
            "pzn": "TEXT",
            "hersteller": "TEXT",
        }
        for column_name, column_type in required_columns.items():
            if column_name in existing:
                continue
            cur.execute(f"ALTER TABLE praeparate ADD COLUMN {column_name} {column_type}")

    def _ensure_address_split_columns(self, cur: sqlite3.Cursor) -> None:
        for table_name in ("depots", "institutions"):
            rows = cur.execute(f"PRAGMA table_info({table_name})").fetchall()
            existing = {row[1] for row in rows}
            required_columns = {
                "strasse": "TEXT",
                "hausnummer": "TEXT",
                "postleitzahl": "TEXT",
                "stadt": "TEXT",
            }
            for column_name, column_type in required_columns.items():
                if column_name in existing:
                    continue
                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

    def _compose_adresse(
        self,
        adresse: str | None = None,
        strasse: str | None = None,
        hausnummer: str | None = None,
        postleitzahl: str | None = None,
        stadt: str | None = None,
    ) -> str | None:
        explicit = (adresse or "").strip()
        if explicit:
            return explicit
        street_block = " ".join(part for part in [strasse or "", hausnummer or ""] if str(part).strip()).strip()
        city_block = " ".join(part for part in [postleitzahl or "", stadt or ""] if str(part).strip()).strip()
        composed = ", ".join(part for part in [street_block, city_block] if part).strip()
        return composed or None
