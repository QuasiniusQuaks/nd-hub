"""SQLite data access for backend endpoints."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, date, datetime, timedelta
from typing import Any

ALLOWED_MOVEMENT_TYPES = {"Zugang", "Abgang", "Vernichtung"}


class SqliteRepository:
    """Small repository for backend API operations."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

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

    def list_depots(
        self,
        q: str = "",
        limit: int = 100,
        offset: int = 0,
        allowed_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        like = f"%{(q or '').strip()}%"
        safe_ids = sorted({int(item) for item in (allowed_ids or []) if int(item) > 0})
        ids_filter_sql = ""
        ids_params: tuple[Any, ...] = ()
        if safe_ids:
            placeholders = ",".join("?" for _ in safe_ids)
            ids_filter_sql = "".join([" AND depots.id IN (", placeholders, ")"])
            ids_params = tuple(safe_ids)
        with self._connect() as conn:
            sql_parts = [
                """
                SELECT depots.id, depots.name, depots.adresse, depots.strasse, depots.hausnummer, depots.postleitzahl, depots.stadt, depots.telefon, depots.email,
                       depots.institution_id, depots.latitude, depots.longitude, institutions.name AS institution_name
                FROM depots
                LEFT JOIN institutions ON institutions.id = depots.institution_id
                WHERE (
                      ? = '%%' OR
                      depots.name LIKE ? OR
                      COALESCE(depots.adresse, '') LIKE ? OR
                      COALESCE(depots.telefon, '') LIKE ? OR
                      COALESCE(depots.email, '') LIKE ?
                )
                """,
            ]
            if ids_filter_sql:
                sql_parts.append(ids_filter_sql)
            sql_parts.append("ORDER BY depots.name LIMIT ? OFFSET ?")
            rows = conn.execute(
                "".join(sql_parts),
                (like, like, like, like, like, *ids_params, safe_limit, safe_offset),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_praeparate(self, q: str = "", limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        like = f"%{(q or '').strip()}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller
                FROM praeparate
                WHERE ? = '%%' OR name LIKE ?
                ORDER BY name
                LIMIT ? OFFSET ?
                """,
                (like, like, safe_limit, safe_offset),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_praeparate_for_depot(self, depot_id: int) -> list[dict[str, Any]]:
        safe_depot_id = int(depot_id)
        with self._connect() as conn:
            assigned_rows = conn.execute(
                "SELECT praeparat_id FROM depot_praeparate WHERE depot_id = ?",
                (safe_depot_id,),
            ).fetchall()
            assigned_ids = {row["praeparat_id"] for row in assigned_rows}
            if not assigned_ids:
                rows = conn.execute(
                    "SELECT id, name FROM praeparate ORDER BY name",
                ).fetchall()
                return [dict(row) for row in rows]
            placeholders = ",".join("?" * len(assigned_ids))
            sql = "".join(
                [
                    "SELECT id, name FROM praeparate WHERE id IN (",
                    placeholders,
                    ") ORDER BY name",
                ]
            )
            rows = conn.execute(
                sql,
                tuple(sorted(assigned_ids)),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_depot_assignments(self, depot_id: int) -> list[dict[str, Any]]:
        safe_depot_id = int(depot_id)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    p.id AS praeparat_id,
                    p.name AS praeparat_name,
                    CASE WHEN dp.praeparat_id IS NULL THEN 0 ELSE 1 END AS assigned,
                    COALESCE(dp.sollbestand, 0) AS sollbestand
                FROM praeparate p
                LEFT JOIN depot_praeparate dp
                    ON dp.praeparat_id = p.id AND dp.depot_id = ?
                ORDER BY p.name
                """,
                (safe_depot_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def set_depot_assignments(self, depot_id: int, assignments: list[dict[str, Any]]) -> None:
        safe_depot_id = int(depot_id)
        with self._connect() as conn:
            cur = conn.cursor()
            depot_exists = cur.execute(
                "SELECT id FROM depots WHERE id = ?",
                (safe_depot_id,),
            ).fetchone()
            if depot_exists is None:
                raise ValueError("Depot nicht gefunden.")
            cur.execute("DELETE FROM depot_praeparate WHERE depot_id = ?", (safe_depot_id,))
            for entry in assignments:
                praeparat_id = int(entry["praeparat_id"])
                sollbestand = int(entry.get("sollbestand", 0))
                if sollbestand < 0:
                    raise ValueError("Sollbestand darf nicht negativ sein.")
                prae_exists = cur.execute(
                    "SELECT id FROM praeparate WHERE id = ?",
                    (praeparat_id,),
                ).fetchone()
                if prae_exists is None:
                    raise ValueError(f"Praeparat existiert nicht: {praeparat_id}")
                cur.execute(
                    """
                    INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand)
                    VALUES (?, ?, ?)
                    """,
                    (safe_depot_id, praeparat_id, sollbestand),
                )
            conn.commit()

    def get_depot_assignment(self, depot_id: int, praeparat_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, depot_id, praeparat_id, sollbestand
                FROM depot_praeparate
                WHERE depot_id = ? AND praeparat_id = ?
                """,
                (int(depot_id), int(praeparat_id)),
            ).fetchone()
            return dict(row) if row else None

    def get_depot_assignment_by_id(self, assignment_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, depot_id, praeparat_id, sollbestand
                FROM depot_praeparate
                WHERE id = ?
                """,
                (int(assignment_id),),
            ).fetchone()
            return dict(row) if row else None

    def upsert_depot_assignment(self, depot_id: int, praeparat_id: int, sollbestand: int = 0) -> int:
        safe_depot_id = int(depot_id)
        safe_praeparat_id = int(praeparat_id)
        safe_soll = max(0, int(sollbestand))
        with self._connect() as conn:
            cur = conn.cursor()
            depot_exists = cur.execute(
                "SELECT id FROM depots WHERE id = ?",
                (safe_depot_id,),
            ).fetchone()
            if depot_exists is None:
                raise ValueError("Depot nicht gefunden.")
            prae_exists = cur.execute(
                "SELECT id FROM praeparate WHERE id = ?",
                (safe_praeparat_id,),
            ).fetchone()
            if prae_exists is None:
                raise ValueError("Praeparat nicht gefunden.")
            existing = cur.execute(
                "SELECT id FROM depot_praeparate WHERE depot_id = ? AND praeparat_id = ?",
                (safe_depot_id, safe_praeparat_id),
            ).fetchone()
            if existing is None:
                cur.execute(
                    """
                    INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand)
                    VALUES (?, ?, ?)
                    """,
                    (safe_depot_id, safe_praeparat_id, safe_soll),
                )
                conn.commit()
                return int(cur.lastrowid)
            assignment_id = int(existing["id"] if isinstance(existing, sqlite3.Row) else existing[0])
            cur.execute(
                "UPDATE depot_praeparate SET sollbestand = ? WHERE id = ?",
                (safe_soll, assignment_id),
            )
            conn.commit()
            return assignment_id

    def delete_depot_assignment(self, depot_id: int, praeparat_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM depot_praeparate WHERE depot_id = ? AND praeparat_id = ?",
                (int(depot_id), int(praeparat_id)),
            )
            conn.commit()
            return cur.rowcount > 0

    def create_depot(
        self,
        name: str,
        adresse: str | None = None,
        strasse: str | None = None,
        hausnummer: str | None = None,
        postleitzahl: str | None = None,
        stadt: str | None = None,
        telefon: str | None = None,
        email: str | None = None,
        institution_id: int | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> int:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Depot-Name darf nicht leer sein.")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO depots (name, adresse, strasse, hausnummer, postleitzahl, stadt, telefon, email, institution_id, latitude, longitude)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    safe_name,
                    self._compose_adresse(adresse, strasse, hausnummer, postleitzahl, stadt),
                    (strasse or "").strip() or None,
                    (hausnummer or "").strip() or None,
                    (postleitzahl or "").strip() or None,
                    (stadt or "").strip() or None,
                    (telefon or "").strip() or None,
                    (email or "").strip() or None,
                    int(institution_id) if institution_id is not None else None,
                    float(latitude) if latitude is not None else None,
                    float(longitude) if longitude is not None else None,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def get_depot_name(self, depot_id: int) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT name FROM depots WHERE id = ?",
                (int(depot_id),),
            ).fetchone()
            if row is None:
                return None
            return str(row["name"]) if row["name"] is not None else None

    def get_depot(self, depot_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT depots.id, depots.name, depots.adresse, depots.strasse, depots.hausnummer, depots.postleitzahl, depots.stadt, depots.telefon, depots.email,
                       depots.institution_id, depots.latitude, depots.longitude, institutions.name AS institution_name
                FROM depots
                LEFT JOIN institutions ON institutions.id = depots.institution_id
                WHERE depots.id = ?
                """,
                (int(depot_id),),
            ).fetchone()
            return dict(row) if row else None

    def update_depot(
        self,
        depot_id: int,
        name: str,
        adresse: str | None = None,
        strasse: str | None = None,
        hausnummer: str | None = None,
        postleitzahl: str | None = None,
        stadt: str | None = None,
        telefon: str | None = None,
        email: str | None = None,
        institution_id: int | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> bool:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Depot-Name darf nicht leer sein.")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE depots
                SET name = ?, adresse = ?, strasse = ?, hausnummer = ?, postleitzahl = ?, stadt = ?, telefon = ?, email = ?, institution_id = ?, latitude = ?, longitude = ?
                WHERE id = ?
                """,
                (
                    safe_name,
                    self._compose_adresse(adresse, strasse, hausnummer, postleitzahl, stadt),
                    (strasse or "").strip() or None,
                    (hausnummer or "").strip() or None,
                    (postleitzahl or "").strip() or None,
                    (stadt or "").strip() or None,
                    (telefon or "").strip() or None,
                    (email or "").strip() or None,
                    int(institution_id) if institution_id is not None else None,
                    float(latitude) if latitude is not None else None,
                    float(longitude) if longitude is not None else None,
                    int(depot_id),
                ),
            )
            conn.commit()
            return cur.rowcount > 0

    def list_institutions(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, name, adresse, strasse, hausnummer, postleitzahl, stadt, latitude, longitude
                FROM institutions
                ORDER BY name
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def get_institution(self, institution_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, name, adresse, strasse, hausnummer, postleitzahl, stadt, latitude, longitude
                FROM institutions
                WHERE id = ?
                """,
                (int(institution_id),),
            ).fetchone()
            return dict(row) if row else None

    def get_onboarding_status(self) -> dict[str, Any]:
        with self._connect() as conn:
            cur = conn.cursor()
            institutions = int(cur.execute("SELECT COUNT(*) FROM institutions").fetchone()[0] or 0)
            depots = int(cur.execute("SELECT COUNT(*) FROM depots").fetchone()[0] or 0)
            praeparate = int(cur.execute("SELECT COUNT(*) FROM praeparate").fetchone()[0] or 0)
        requires_onboarding = depots == 0 or praeparate == 0
        return {
            "requires_onboarding": bool(requires_onboarding),
            "counts": {
                "institutions": institutions,
                "depots": depots,
                "praeparate": praeparate,
            },
        }

    def create_institution(
        self,
        name: str,
        adresse: str | None = None,
        strasse: str | None = None,
        hausnummer: str | None = None,
        postleitzahl: str | None = None,
        stadt: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> int:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Institutionsname darf nicht leer sein.")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO institutions (name, adresse, strasse, hausnummer, postleitzahl, stadt, latitude, longitude)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    safe_name,
                    self._compose_adresse(adresse, strasse, hausnummer, postleitzahl, stadt),
                    (strasse or "").strip() or None,
                    (hausnummer or "").strip() or None,
                    (postleitzahl or "").strip() or None,
                    (stadt or "").strip() or None,
                    float(latitude) if latitude is not None else None,
                    float(longitude) if longitude is not None else None,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def create_onboarding_setup(
        self,
        institution: dict[str, Any],
        praeparate: list[dict[str, Any]],
        depots: list[dict[str, Any]],
    ) -> dict[str, Any]:
        safe_name = str((institution or {}).get("name") or "").strip()
        if not safe_name:
            raise ValueError("Institutionsname darf nicht leer sein.")
        if not praeparate:
            raise ValueError("Mindestens ein Praeparat ist erforderlich.")
        if not depots:
            raise ValueError("Mindestens ein Notfalldepot ist erforderlich.")

        seen_praeparate: set[str] = set()
        normalized_praeparate: list[dict[str, Any]] = []
        for item in praeparate:
            item_name = str((item or {}).get("name") or "").strip()
            if not item_name:
                raise ValueError("Praeparat-Name darf nicht leer sein.")
            key = item_name.lower()
            if key in seen_praeparate:
                raise ValueError(f"Praeparat doppelt angegeben: {item_name}")
            seen_praeparate.add(key)
            normalized_praeparate.append(
                {
                    "name": item_name,
                    "wirkstoff": str((item or {}).get("wirkstoff") or "").strip() or None,
                    "darreichungsform": str((item or {}).get("darreichungsform") or "").strip() or None,
                    "staerke": str((item or {}).get("staerke") or "").strip() or None,
                    "einheit": str((item or {}).get("einheit") or "").strip() or None,
                    "pzn": str((item or {}).get("pzn") or "").strip() or None,
                    "hersteller": str((item or {}).get("hersteller") or "").strip() or None,
                }
            )

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("BEGIN")
            try:
                cur.execute(
                    """
                    INSERT INTO institutions (name, adresse, strasse, hausnummer, postleitzahl, stadt, latitude, longitude)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        safe_name,
                        self._compose_adresse(
                            str((institution or {}).get("adresse") or "").strip() or None,
                            str((institution or {}).get("strasse") or "").strip() or None,
                            str((institution or {}).get("hausnummer") or "").strip() or None,
                            str((institution or {}).get("postleitzahl") or "").strip() or None,
                            str((institution or {}).get("stadt") or "").strip() or None,
                        ),
                        str((institution or {}).get("strasse") or "").strip() or None,
                        str((institution or {}).get("hausnummer") or "").strip() or None,
                        str((institution or {}).get("postleitzahl") or "").strip() or None,
                        str((institution or {}).get("stadt") or "").strip() or None,
                        float(institution["latitude"]) if (institution or {}).get("latitude") is not None else None,
                        float(institution["longitude"]) if (institution or {}).get("longitude") is not None else None,
                    ),
                )
                institution_id = int(cur.lastrowid)

                praeparat_ids_by_name: dict[str, int] = {}
                for item in normalized_praeparate:
                    cur.execute(
                        """
                        INSERT INTO praeparate (name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item["name"],
                            item["wirkstoff"],
                            item["darreichungsform"],
                            item["staerke"],
                            item["einheit"],
                            item["pzn"],
                            item["hersteller"],
                        ),
                    )
                    praeparat_ids_by_name[str(item["name"]).lower()] = int(cur.lastrowid)

                created_depots: list[dict[str, Any]] = []
                for depot in depots:
                    depot_name = str((depot or {}).get("name") or "").strip()
                    if not depot_name:
                        raise ValueError("Depot-Name darf nicht leer sein.")
                    cur.execute(
                        """
                        INSERT INTO depots (name, adresse, strasse, hausnummer, postleitzahl, stadt, telefon, email, institution_id, latitude, longitude)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            depot_name,
                            self._compose_adresse(
                                str((depot or {}).get("adresse") or "").strip() or None,
                                str((depot or {}).get("strasse") or "").strip() or None,
                                str((depot or {}).get("hausnummer") or "").strip() or None,
                                str((depot or {}).get("postleitzahl") or "").strip() or None,
                                str((depot or {}).get("stadt") or "").strip() or None,
                            ),
                            str((depot or {}).get("strasse") or "").strip() or None,
                            str((depot or {}).get("hausnummer") or "").strip() or None,
                            str((depot or {}).get("postleitzahl") or "").strip() or None,
                            str((depot or {}).get("stadt") or "").strip() or None,
                            str((depot or {}).get("telefon") or "").strip() or None,
                            str((depot or {}).get("email") or "").strip() or None,
                            institution_id,
                            float(depot["latitude"]) if (depot or {}).get("latitude") is not None else None,
                            float(depot["longitude"]) if (depot or {}).get("longitude") is not None else None,
                        ),
                    )
                    depot_id = int(cur.lastrowid)
                    assignments = list((depot or {}).get("assignments") or [])
                    if not assignments:
                        raise ValueError(f"Depot '{depot_name}' hat keine Praeparate-Zuordnung.")
                    seen_assignment: set[int] = set()
                    assignment_count = 0
                    for assignment in assignments:
                        praeparat_name = str((assignment or {}).get("praeparat_name") or "").strip()
                        praeparat_id = praeparat_ids_by_name.get(praeparat_name.lower())
                        if not praeparat_id:
                            raise ValueError(
                                f"Unbekanntes Praeparat in Zuordnung fuer Depot '{depot_name}': {praeparat_name}"
                            )
                        if praeparat_id in seen_assignment:
                            continue
                        seen_assignment.add(praeparat_id)
                        sollbestand = int((assignment or {}).get("sollbestand", 0) or 0)
                        if sollbestand < 0:
                            raise ValueError("Sollbestand darf nicht negativ sein.")
                        cur.execute(
                            """
                            INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand)
                            VALUES (?, ?, ?)
                            """,
                            (depot_id, praeparat_id, sollbestand),
                        )
                        assignment_count += 1
                    if assignment_count == 0:
                        raise ValueError(f"Depot '{depot_name}' hat keine gueltige Praeparate-Zuordnung.")
                    created_depots.append({"id": depot_id, "name": depot_name, "assignments": assignment_count})

                conn.commit()
                return {
                    "institution_id": institution_id,
                    "praeparate_count": len(normalized_praeparate),
                    "depots": created_depots,
                }
            except Exception:
                conn.rollback()
                raise

    def update_institution(
        self,
        institution_id: int,
        name: str,
        adresse: str | None = None,
        strasse: str | None = None,
        hausnummer: str | None = None,
        postleitzahl: str | None = None,
        stadt: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> bool:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Institutionsname darf nicht leer sein.")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE institutions
                SET name = ?, adresse = ?, strasse = ?, hausnummer = ?, postleitzahl = ?, stadt = ?, latitude = ?, longitude = ?
                WHERE id = ?
                """,
                (
                    safe_name,
                    self._compose_adresse(adresse, strasse, hausnummer, postleitzahl, stadt),
                    (strasse or "").strip() or None,
                    (hausnummer or "").strip() or None,
                    (postleitzahl or "").strip() or None,
                    (stadt or "").strip() or None,
                    float(latitude) if latitude is not None else None,
                    float(longitude) if longitude is not None else None,
                    int(institution_id),
                ),
            )
            conn.commit()
            return cur.rowcount > 0

    def delete_institution(self, institution_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.cursor()
            used = cur.execute(
                "SELECT COUNT(*) FROM depots WHERE institution_id = ?",
                (int(institution_id),),
            ).fetchone()[0]
            if int(used or 0) > 0:
                raise ValueError("Institution ist noch Depots zugeordnet.")
            cur.execute("DELETE FROM institutions WHERE id = ?", (int(institution_id),))
            conn.commit()
            return cur.rowcount > 0

    def set_user_depot_permission(self, username: str, depot_id: int, can_read: bool, can_write: bool) -> None:
        safe_username = (username or "").strip()
        if not safe_username:
            raise ValueError("Benutzername fehlt.")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO user_depot_permissions (username, depot_id, can_read, can_write)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(username, depot_id) DO UPDATE SET
                    can_read = excluded.can_read,
                    can_write = excluded.can_write
                """,
                (safe_username, int(depot_id), int(bool(can_read)), int(bool(can_write))),
            )
            conn.commit()

    def list_user_depot_permissions(self, username: str) -> list[dict[str, Any]]:
        safe_username = (username or "").strip()
        if not safe_username:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT udp.depot_id, udp.can_read, udp.can_write, depots.name AS depot_name
                FROM user_depot_permissions udp
                JOIN depots ON depots.id = udp.depot_id
                WHERE udp.username = ?
                ORDER BY depots.name
                """,
                (safe_username,),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_map_institutions_with_depots(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    institutions.id AS institution_id,
                    institutions.name AS institution_name,
                    institutions.adresse AS institution_adresse,
                    institutions.strasse AS institution_strasse,
                    institutions.hausnummer AS institution_hausnummer,
                    institutions.postleitzahl AS institution_postleitzahl,
                    institutions.stadt AS institution_stadt,
                    institutions.latitude AS institution_latitude,
                    institutions.longitude AS institution_longitude,
                    depots.id AS depot_id,
                    depots.name AS depot_name,
                    depots.adresse AS depot_adresse,
                    depots.strasse AS depot_strasse,
                    depots.hausnummer AS depot_hausnummer,
                    depots.postleitzahl AS depot_postleitzahl,
                    depots.stadt AS depot_stadt,
                    depots.latitude AS depot_latitude,
                    depots.longitude AS depot_longitude
                FROM institutions
                LEFT JOIN depots ON depots.institution_id = institutions.id
                ORDER BY institutions.name, depots.name
                """
            ).fetchall()
        grouped: dict[int, dict[str, Any]] = {}
        for row in rows:
            key = int(row["institution_id"])
            item = grouped.setdefault(
                key,
                {
                    "institution_id": key,
                    "institution_name": row["institution_name"],
                    "institution_adresse": row["institution_adresse"],
                    "institution_strasse": row["institution_strasse"],
                    "institution_hausnummer": row["institution_hausnummer"],
                    "institution_postleitzahl": row["institution_postleitzahl"],
                    "institution_stadt": row["institution_stadt"],
                    "latitude": row["institution_latitude"],
                    "longitude": row["institution_longitude"],
                    "depots": [],
                },
            )
            depot_id = row["depot_id"]
            if depot_id is not None:
                item["depots"].append(
                    {
                        "id": int(depot_id),
                        "name": row["depot_name"],
                        "adresse": row["depot_adresse"],
                        "strasse": row["depot_strasse"],
                        "hausnummer": row["depot_hausnummer"],
                        "postleitzahl": row["depot_postleitzahl"],
                        "stadt": row["depot_stadt"],
                        "latitude": row["depot_latitude"],
                        "longitude": row["depot_longitude"],
                    }
                )
        return list(grouped.values())

    def delete_depot(self, depot_id: int) -> bool:
        safe_id = int(depot_id)
        with self._connect() as conn:
            cur = conn.cursor()
            used = cur.execute(
                "SELECT COUNT(*) FROM bewegungen WHERE depot_id = ?",
                (safe_id,),
            ).fetchone()[0]
            if used > 0:
                raise ValueError("Depot kann nicht geloescht werden, da Bewegungen vorhanden sind.")
            cur.execute("DELETE FROM depots WHERE id = ?", (safe_id,))
            conn.commit()
            return cur.rowcount > 0

    def create_praeparat(
        self,
        name: str,
        wirkstoff: str | None = None,
        darreichungsform: str | None = None,
        staerke: str | None = None,
        einheit: str | None = None,
        pzn: str | None = None,
        hersteller: str | None = None,
    ) -> int:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Praeparat-Name darf nicht leer sein.")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO praeparate (name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    safe_name,
                    (wirkstoff or "").strip() or None,
                    (darreichungsform or "").strip() or None,
                    (staerke or "").strip() or None,
                    (einheit or "").strip() or None,
                    (pzn or "").strip() or None,
                    (hersteller or "").strip() or None,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def update_praeparat(
        self,
        praeparat_id: int,
        name: str,
        wirkstoff: str | None = None,
        darreichungsform: str | None = None,
        staerke: str | None = None,
        einheit: str | None = None,
        pzn: str | None = None,
        hersteller: str | None = None,
    ) -> bool:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Praeparat-Name darf nicht leer sein.")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE praeparate
                SET name = ?, wirkstoff = ?, darreichungsform = ?, staerke = ?, einheit = ?, pzn = ?, hersteller = ?
                WHERE id = ?
                """,
                (
                    safe_name,
                    (wirkstoff or "").strip() or None,
                    (darreichungsform or "").strip() or None,
                    (staerke or "").strip() or None,
                    (einheit or "").strip() or None,
                    (pzn or "").strip() or None,
                    (hersteller or "").strip() or None,
                    int(praeparat_id),
                ),
            )
            conn.commit()
            return cur.rowcount > 0

    def delete_praeparat(self, praeparat_id: int) -> bool:
        safe_id = int(praeparat_id)
        with self._connect() as conn:
            cur = conn.cursor()
            used = cur.execute(
                "SELECT COUNT(*) FROM bewegungen WHERE praeparat_id = ?",
                (safe_id,),
            ).fetchone()[0]
            if used > 0:
                raise ValueError("Praeparat kann nicht geloescht werden, da Bewegungen vorhanden sind.")
            cur.execute("DELETE FROM praeparate WHERE id = ?", (safe_id,))
            conn.commit()
            return cur.rowcount > 0

    def get_praeparat(self, praeparat_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller FROM praeparate WHERE id = ?",
                (int(praeparat_id),),
            ).fetchone()
            return dict(row) if row else None

    def list_kontakte(self, depot_id: int) -> list[dict[str, Any]]:
        safe_depot_id = int(depot_id)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, depot_id, name, rolle, telefon, email
                FROM kontakte
                WHERE depot_id = ?
                ORDER BY name, id
                """,
                (safe_depot_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def create_kontakt(
        self,
        depot_id: int,
        name: str,
        rolle: str | None = None,
        telefon: str | None = None,
        email: str | None = None,
    ) -> int:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Kontakt-Name darf nicht leer sein.")
        safe_depot_id = int(depot_id)
        with self._connect() as conn:
            cur = conn.cursor()
            depot_exists = cur.execute(
                "SELECT id FROM depots WHERE id = ?",
                (safe_depot_id,),
            ).fetchone()
            if depot_exists is None:
                raise ValueError("Depot nicht gefunden.")
            cur.execute(
                """
                INSERT INTO kontakte (depot_id, name, rolle, telefon, email)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    safe_depot_id,
                    safe_name,
                    (rolle or "").strip() or None,
                    (telefon or "").strip() or None,
                    (email or "").strip() or None,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def update_kontakt(
        self,
        kontakt_id: int,
        name: str,
        rolle: str | None = None,
        telefon: str | None = None,
        email: str | None = None,
    ) -> bool:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Kontakt-Name darf nicht leer sein.")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE kontakte
                SET name = ?, rolle = ?, telefon = ?, email = ?
                WHERE id = ?
                """,
                (
                    safe_name,
                    (rolle or "").strip() or None,
                    (telefon or "").strip() or None,
                    (email or "").strip() or None,
                    int(kontakt_id),
                ),
            )
            conn.commit()
            return cur.rowcount > 0

    def delete_kontakt(self, kontakt_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM kontakte WHERE id = ?", (int(kontakt_id),))
            conn.commit()
            return cur.rowcount > 0

    def get_kontakt(self, kontakt_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, depot_id, name, rolle, telefon, email FROM kontakte WHERE id = ?",
                (int(kontakt_id),),
            ).fetchone()
            return dict(row) if row else None

    def get_kontakte_by_depot_ids(self, depot_ids: list[int]) -> list[dict[str, Any]]:
        safe_ids = sorted({int(depot_id) for depot_id in depot_ids})
        if not safe_ids:
            return []
        placeholders = ",".join("?" for _ in safe_ids)
        sql = "".join(
            [
                """
                SELECT
                    k.id,
                    k.name,
                    k.rolle,
                    k.email,
                    d.name AS depot_name,
                    d.id AS depot_id
                FROM kontakte k
                JOIN depots d ON d.id = k.depot_id
                WHERE k.depot_id IN (""",
                placeholders,
                """)
                  AND COALESCE(k.email, '') <> ''
                ORDER BY d.name, k.name
                """,
            ]
        )
        with self._connect() as conn:
            rows = conn.execute(
                sql,
                tuple(safe_ids),
            ).fetchall()
            return [dict(row) for row in rows]

    def add_email_verlauf(
        self,
        betreff: str,
        nachricht: str,
        depot_names: str,
        emails: str,
        anzahl: int,
        versand_status: str = "draft",
        versand_kanal: str | None = None,
        versand_fehler: str | None = None,
    ) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO email_verlauf (
                    datum, betreff, nachricht, empfaenger_depots, empfaenger_emails,
                    anzahl_empfaenger, versand_status, versand_kanal, versand_fehler
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
                    (betreff or "").strip(),
                    nachricht or "",
                    depot_names or "",
                    emails or "",
                    int(anzahl),
                    (versand_status or "draft").strip() or "draft",
                    (versand_kanal or "").strip() or None,
                    (versand_fehler or "").strip() or None,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def get_email_verlauf(self, limit: int = 50) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 500))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id, datum, betreff, empfaenger_depots, anzahl_empfaenger,
                    COALESCE(versand_status, 'draft') AS versand_status,
                    COALESCE(versand_kanal, '') AS versand_kanal
                FROM email_verlauf
                ORDER BY datum DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_email_details(self, email_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    id, datum, betreff, nachricht, empfaenger_depots, empfaenger_emails, anzahl_empfaenger,
                    COALESCE(versand_status, 'draft') AS versand_status,
                    COALESCE(versand_kanal, '') AS versand_kanal,
                    COALESCE(versand_fehler, '') AS versand_fehler
                FROM email_verlauf
                WHERE id = ?
                """,
                (int(email_id),),
            ).fetchone()
            return dict(row) if row else None

    def update_email_delivery_status(
        self,
        email_id: int,
        versand_status: str,
        versand_kanal: str | None = None,
        versand_fehler: str | None = None,
    ) -> bool:
        safe_status = (versand_status or "").strip().lower()
        if safe_status not in {"draft", "sent", "send_failed"}:
            raise ValueError("Ungueltiger Versandstatus.")
        safe_channel = (versand_kanal or "").strip() or ("manual" if safe_status == "sent" else "draft")
        safe_error = (versand_fehler or "").strip() or None
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE email_verlauf
                SET versand_status = ?,
                    versand_kanal = ?,
                    versand_fehler = ?
                WHERE id = ?
                """,
                (safe_status, safe_channel, safe_error, int(email_id)),
            )
            conn.commit()
            return cur.rowcount > 0

    def list_bewegungen(
        self,
        limit: int = 100,
        offset: int = 0,
        q: str = "",
        typ: str | None = None,
        depot_id: int | None = None,
        depot_ids: list[int] | None = None,
        praeparat_id: int | None = None,
        has_attachment: bool | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 500))
        safe_offset = max(0, int(offset))
        like = f"%{(q or '').strip()}%"
        safe_typ = (typ or "").strip()
        safe_depot_id = int(depot_id) if depot_id is not None else 0
        safe_depot_ids = sorted({int(item) for item in (depot_ids or []) if int(item) > 0})
        safe_praeparat_id = int(praeparat_id) if praeparat_id is not None else 0
        only_with_attachment = bool(has_attachment) if has_attachment is not None else False
        safe_start_date = (start_date or "").strip()
        safe_end_date = (end_date or "").strip()
        ids_filter_sql = ""
        ids_params: tuple[Any, ...] = ()
        if safe_depot_ids:
            placeholders = ",".join("?" for _ in safe_depot_ids)
            ids_filter_sql = "".join([" AND depot_id IN (", placeholders, ")"])
            ids_params = tuple(safe_depot_ids)
        with self._connect() as conn:
            sql_parts = [
                """
                SELECT
                    id, depot_id, praeparat_id, typ, charge, verfall,
                    eingang_datum, ausgang_datum, empfaenger, anzahl,
                    datei_name, datei_groesse, datei_hochgeladen_am,
                    CASE WHEN COALESCE(datei_pfad, '') <> '' THEN 1 ELSE 0 END AS has_attachment
                FROM bewegungen
                WHERE (? = '%%' OR
                      COALESCE(charge, '') LIKE ? OR
                      COALESCE(verfall, '') LIKE ? OR
                      COALESCE(empfaenger, '') LIKE ?)
                  AND (? = '' OR typ = ?)
                  AND (? = 0 OR depot_id = ?)
                  AND (? = 0 OR praeparat_id = ?)
                  AND (? = 0 OR COALESCE(datei_pfad, '') <> '')
                  AND (? = '' OR COALESCE(eingang_datum, ausgang_datum, '') >= ?)
                  AND (? = '' OR COALESCE(eingang_datum, ausgang_datum, '') <= ?)
                """,
            ]
            if ids_filter_sql:
                sql_parts.append(ids_filter_sql)
            sql_parts.append("ORDER BY id DESC LIMIT ? OFFSET ?")
            rows = conn.execute(
                "".join(sql_parts),
                (
                    like,
                    like,
                    like,
                    like,
                    safe_typ,
                    safe_typ,
                    safe_depot_id,
                    safe_depot_id,
                    safe_praeparat_id,
                    safe_praeparat_id,
                    1 if only_with_attachment else 0,
                    safe_start_date,
                    safe_start_date,
                    safe_end_date,
                    safe_end_date,
                    *ids_params,
                    safe_limit,
                    safe_offset,
                ),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_bewegung(self, bewegung_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    id, depot_id, praeparat_id, typ, charge, verfall,
                    eingang_datum, ausgang_datum, empfaenger, anzahl,
                    datei_pfad, datei_name, datei_groesse, datei_hochgeladen_am
                FROM bewegungen
                WHERE id = ?
                """,
                (int(bewegung_id),),
            ).fetchone()
            return dict(row) if row else None

    def set_bewegung_attachment(
        self,
        bewegung_id: int,
        datei_pfad: str,
        datei_name: str,
        datei_groesse: int,
        uploaded_at: str,
    ) -> bool:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE bewegungen
                SET datei_pfad = ?, datei_name = ?, datei_groesse = ?, datei_hochgeladen_am = ?
                WHERE id = ?
                """,
                (
                    datei_pfad,
                    datei_name,
                    int(datei_groesse),
                    uploaded_at,
                    int(bewegung_id),
                ),
            )
            conn.commit()
            return cur.rowcount > 0

    def insert_bewegung(
        self,
        depot_id: int,
        praeparat_id: int,
        typ: str,
        charge: str,
        verfall: str,
        datum: str,
        anzahl: int,
        empfaenger: str | None = None,
    ) -> int:
        if typ not in ALLOWED_MOVEMENT_TYPES:
            raise ValueError(f"Ungueltiger Typ: {typ}")
        if not charge.strip():
            raise ValueError("Charge darf nicht leer sein.")
        if not verfall.strip():
            raise ValueError("Verfall darf nicht leer sein.")
        if not datum.strip():
            raise ValueError("Datum darf nicht leer sein.")
        if int(anzahl) <= 0:
            raise ValueError("Anzahl muss groesser als 0 sein.")

        eingang = datum if typ == "Zugang" else None
        ausgang = datum if typ in {"Abgang", "Vernichtung"} else None
        empfaenger_value = empfaenger.strip() if empfaenger else None

        with self._connect() as conn:
            cur = conn.cursor()
            depot_exists = cur.execute(
                "SELECT id FROM depots WHERE id = ?",
                (int(depot_id),),
            ).fetchone()
            if depot_exists is None:
                raise ValueError("Depot existiert nicht.")
            prae_exists = cur.execute(
                "SELECT id FROM praeparate WHERE id = ?",
                (int(praeparat_id),),
            ).fetchone()
            if prae_exists is None:
                raise ValueError("Praeparat existiert nicht.")
            assigned_rows = cur.execute(
                "SELECT praeparat_id FROM depot_praeparate WHERE depot_id = ?",
                (int(depot_id),),
            ).fetchall()
            if assigned_rows:
                assigned_ids = {row["praeparat_id"] for row in assigned_rows}
                if int(praeparat_id) not in assigned_ids:
                    raise ValueError("Praeparat ist diesem Depot nicht zugeordnet.")
            cur.execute(
                """
                INSERT INTO bewegungen (
                    depot_id, praeparat_id, charge, verfall, eingang_datum,
                    ausgang_datum, empfaenger, anzahl, typ
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(depot_id),
                    int(praeparat_id),
                    charge.strip(),
                    verfall.strip(),
                    eingang,
                    ausgang,
                    empfaenger_value,
                    int(anzahl),
                    typ,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def get_bewegungen_analyse(
        self,
        depot_ids: list[int] | None = None,
        praeparat_ids: list[int] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                d.name AS depot,
                p.name AS praeparat,
                b.typ AS typ,
                substr(COALESCE(b.eingang_datum, b.ausgang_datum, ''), 1, 7) AS monat,
                SUM(b.anzahl) AS anzahl
            FROM bewegungen b
            JOIN depots d ON d.id = b.depot_id
            JOIN praeparate p ON p.id = b.praeparat_id
            WHERE 1=1
        """
        params: list[Any] = []
        if depot_ids:
            placeholders = ",".join("?" for _ in depot_ids)
            sql += f" AND b.depot_id IN ({placeholders})"
            params.extend(int(item) for item in depot_ids)
        if praeparat_ids:
            placeholders = ",".join("?" for _ in praeparat_ids)
            sql += f" AND b.praeparat_id IN ({placeholders})"
            params.extend(int(item) for item in praeparat_ids)
        if start_date:
            sql += " AND COALESCE(b.eingang_datum, b.ausgang_datum) >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND COALESCE(b.eingang_datum, b.ausgang_datum) <= ?"
            params.append(end_date)
        sql += " GROUP BY d.name, p.name, b.typ, monat ORDER BY monat, d.name, p.name"
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
            return [dict(row) for row in rows]

    def get_bestandsentwicklung(
        self,
        depot_ids: list[int] | None = None,
        praeparat_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                d.name AS depot,
                p.name AS praeparat,
                dp.sollbestand AS sollbestand,
                COALESCE(SUM(
                    CASE
                        WHEN b.typ = 'Zugang' THEN b.anzahl
                        WHEN b.typ IN ('Abgang', 'Vernichtung') THEN -b.anzahl
                        ELSE 0
                    END
                ), 0) AS ist_bestand,
                COALESCE(SUM(
                    CASE
                        WHEN b.typ = 'Zugang' THEN b.anzahl
                        WHEN b.typ IN ('Abgang', 'Vernichtung') THEN -b.anzahl
                        ELSE 0
                    END
                ), 0) - dp.sollbestand AS differenz
            FROM depot_praeparate dp
            JOIN depots d ON d.id = dp.depot_id
            JOIN praeparate p ON p.id = dp.praeparat_id
            LEFT JOIN bewegungen b ON b.depot_id = dp.depot_id AND b.praeparat_id = dp.praeparat_id
            WHERE 1=1
        """
        params: list[Any] = []
        if depot_ids:
            placeholders = ",".join("?" for _ in depot_ids)
            sql += f" AND dp.depot_id IN ({placeholders})"
            params.extend(int(item) for item in depot_ids)
        if praeparat_ids:
            placeholders = ",".join("?" for _ in praeparat_ids)
            sql += f" AND dp.praeparat_id IN ({placeholders})"
            params.extend(int(item) for item in praeparat_ids)
        sql += " GROUP BY d.name, p.name, dp.sollbestand ORDER BY d.name, p.name"
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
            return [dict(row) for row in rows]

    def get_praeparat_ranking(
        self,
        depot_ids: list[int] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                p.name AS name,
                SUM(b.anzahl) AS anzahl
            FROM bewegungen b
            JOIN praeparate p ON p.id = b.praeparat_id
            WHERE b.typ IN ('Abgang', 'Vernichtung')
        """
        params: list[Any] = []
        if depot_ids:
            placeholders = ",".join("?" for _ in depot_ids)
            sql += f" AND b.depot_id IN ({placeholders})"
            params.extend(int(item) for item in depot_ids)
        if start_date:
            sql += " AND COALESCE(b.ausgang_datum, b.eingang_datum) >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND COALESCE(b.ausgang_datum, b.eingang_datum) <= ?"
            params.append(end_date)
        sql += " GROUP BY p.name ORDER BY anzahl DESC LIMIT ?"
        params.append(max(1, min(int(limit), 50)))
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
            return [dict(row) for row in rows]

    def get_depot_ranking(
        self,
        praeparat_ids: list[int] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                d.name AS name,
                SUM(b.anzahl) AS anzahl
            FROM bewegungen b
            JOIN depots d ON d.id = b.depot_id
            WHERE b.typ IN ('Abgang', 'Vernichtung')
        """
        params: list[Any] = []
        if praeparat_ids:
            placeholders = ",".join("?" for _ in praeparat_ids)
            sql += f" AND b.praeparat_id IN ({placeholders})"
            params.extend(int(item) for item in praeparat_ids)
        if start_date:
            sql += " AND COALESCE(b.ausgang_datum, b.eingang_datum) >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND COALESCE(b.ausgang_datum, b.eingang_datum) <= ?"
            params.append(end_date)
        sql += " GROUP BY d.name ORDER BY anzahl DESC LIMIT ?"
        params.append(max(1, min(int(limit), 50)))
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
            return [dict(row) for row in rows]

    def get_matrix_data(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    d.name AS depot,
                    p.name AS praeparat,
                    dp.sollbestand AS sollbestand,
                    COALESCE(SUM(
                        CASE
                            WHEN b.typ = 'Zugang' THEN b.anzahl
                            WHEN b.typ IN ('Abgang', 'Vernichtung') THEN -b.anzahl
                            ELSE 0
                        END
                    ), 0) AS ist_bestand
                FROM depot_praeparate dp
                JOIN depots d ON d.id = dp.depot_id
                JOIN praeparate p ON p.id = dp.praeparat_id
                LEFT JOIN bewegungen b ON b.depot_id = dp.depot_id AND b.praeparat_id = dp.praeparat_id
                GROUP BY d.name, p.name, dp.sollbestand
                ORDER BY d.name, p.name
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def get_verfall_prognose(
        self,
        depot_ids: list[int] | None = None,
        praeparat_ids: list[int] | None = None,
        horizon_months: int = 24,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                substr(b.verfall, 1, 7) AS verfall_monat,
                SUM(b.anzahl) AS anzahl
            FROM bewegungen b
            WHERE b.typ = 'Zugang'
              AND COALESCE(b.verfall, '') <> ''
        """
        params: list[Any] = []
        if depot_ids:
            placeholders = ",".join("?" for _ in depot_ids)
            sql += f" AND b.depot_id IN ({placeholders})"
            params.extend(int(item) for item in depot_ids)
        if praeparat_ids:
            placeholders = ",".join("?" for _ in praeparat_ids)
            sql += f" AND b.praeparat_id IN ({placeholders})"
            params.extend(int(item) for item in praeparat_ids)
        sql += " GROUP BY verfall_monat ORDER BY verfall_monat"
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
            # horizon_months currently handled in API for portability/readability
            _ = horizon_months
            return [dict(row) for row in rows]

    def get_dashboard_overview(
        self,
        limit_activity: int = 8,
        limit_expiry: int = 8,
        critical_days: int = 30,
    ) -> dict[str, Any]:
        safe_activity_limit = max(1, min(int(limit_activity), 50))
        safe_expiry_limit = max(1, min(int(limit_expiry), 50))
        safe_critical_days = max(1, min(int(critical_days), 365))
        with self._connect() as conn:
            depot_count = int(conn.execute("SELECT COUNT(*) FROM depots").fetchone()[0])
            praeparat_count = int(conn.execute("SELECT COUNT(*) FROM praeparate").fetchone()[0])
            bewegung_count = int(conn.execute("SELECT COUNT(*) FROM bewegungen").fetchone()[0])
            kritische_verfaelle = int(
                conn.execute(
                    """
                    SELECT COALESCE(SUM(anzahl), 0)
                    FROM bewegungen
                    WHERE typ = 'Zugang'
                      AND COALESCE(verfall, '') <> ''
                      AND date(verfall) <= date('now', ?)
                    """,
                    (f"+{safe_critical_days} day",),
                ).fetchone()[0]
                or 0
            )
            activity_rows = conn.execute(
                """
                SELECT
                    b.id,
                    b.typ,
                    b.charge,
                    b.verfall,
                    b.anzahl,
                    COALESCE(b.eingang_datum, b.ausgang_datum, '') AS datum,
                    d.name AS depot,
                    p.name AS praeparat
                FROM bewegungen b
                JOIN depots d ON d.id = b.depot_id
                JOIN praeparate p ON p.id = b.praeparat_id
                ORDER BY b.id DESC
                LIMIT ?
                """,
                (safe_activity_limit,),
            ).fetchall()
            expiry_rows = conn.execute(
                """
                SELECT
                    b.id,
                    d.name AS depot,
                    p.name AS praeparat,
                    b.charge,
                    b.verfall,
                    b.anzahl,
                    CAST(julianday(date(b.verfall)) - julianday(date('now')) AS INTEGER) AS tage_bis_verfall
                FROM bewegungen b
                JOIN depots d ON d.id = b.depot_id
                JOIN praeparate p ON p.id = b.praeparat_id
                WHERE b.typ = 'Zugang'
                  AND COALESCE(b.verfall, '') <> ''
                ORDER BY date(b.verfall) ASC, b.id ASC
                LIMIT ?
                """,
                (safe_expiry_limit,),
            ).fetchall()
            return {
                "kpis": {
                    "depots": depot_count,
                    "praeparate": praeparat_count,
                    "bewegungen": bewegung_count,
                    "kritisch_verfallend": kritische_verfaelle,
                },
                "recent_activity": [dict(row) for row in activity_rows],
                "expiry_preview": [dict(row) for row in expiry_rows],
            }

    def _build_verfall_filter_sql(
        self,
        depot_ids: list[int] | None,
        praeparat_ids: list[int] | None,
        search_text: str | None,
        category: str | None,
        critical_days: int,
        warning_days: int,
        attention_days: int,
    ) -> tuple[str, list[Any]]:
        sql = """
            FROM bewegungen b
            JOIN depots d ON d.id = b.depot_id
            JOIN praeparate p ON p.id = b.praeparat_id
            WHERE b.typ = 'Zugang'
              AND COALESCE(b.verfall, '') <> ''
        """
        params: list[Any] = []
        if depot_ids:
            placeholders = ",".join("?" for _ in depot_ids)
            sql += f" AND b.depot_id IN ({placeholders})"
            params.extend(int(item) for item in depot_ids)
        if praeparat_ids:
            placeholders = ",".join("?" for _ in praeparat_ids)
            sql += f" AND b.praeparat_id IN ({placeholders})"
            params.extend(int(item) for item in praeparat_ids)
        safe_query = (search_text or "").strip()
        if safe_query:
            like = f"%{safe_query}%"
            sql += """
              AND (
                    d.name LIKE ?
                 OR p.name LIKE ?
                 OR COALESCE(b.charge, '') LIKE ?
                 OR COALESCE(b.verfall, '') LIKE ?
              )
            """
            params.extend([like, like, like, like])

        safe_category = (category or "alle").strip().lower()
        safe_critical_days = max(1, int(critical_days))
        safe_warning_days = max(safe_critical_days + 1, int(warning_days))
        safe_attention_days = max(safe_warning_days + 1, int(attention_days))
        day_expr = "CAST(julianday(date(b.verfall)) - julianday(date('now')) AS INTEGER)"
        if safe_category == "kritisch":
            sql += f" AND ({day_expr}) <= ?"
            params.append(safe_critical_days)
        elif safe_category == "warnung":
            sql += f" AND ({day_expr}) > ? AND ({day_expr}) <= ?"
            params.extend([safe_critical_days, safe_warning_days])
        elif safe_category == "achtung":
            sql += f" AND ({day_expr}) > ? AND ({day_expr}) <= ?"
            params.extend([safe_warning_days, safe_attention_days])
        elif safe_category == "abgelaufen":
            sql += f" AND ({day_expr}) < 0"
        return sql, params

    def list_verfall_items(
        self,
        depot_ids: list[int] | None = None,
        praeparat_ids: list[int] | None = None,
        search_text: str | None = None,
        category: str | None = None,
        limit: int = 100,
        offset: int = 0,
        critical_days: int = 30,
        warning_days: int = 90,
        attention_days: int = 180,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 1000))
        safe_offset = max(0, int(offset))
        filter_sql, params = self._build_verfall_filter_sql(
            depot_ids=depot_ids,
            praeparat_ids=praeparat_ids,
            search_text=search_text,
            category=category,
            critical_days=critical_days,
            warning_days=warning_days,
            attention_days=attention_days,
        )
        query = f"""
            SELECT
                b.id,
                b.depot_id,
                b.praeparat_id,
                d.name AS depot,
                p.name AS praeparat,
                b.charge,
                b.verfall,
                b.anzahl,
                CAST(julianday(date(b.verfall)) - julianday(date('now')) AS INTEGER) AS tage_bis_verfall
            {filter_sql}
            ORDER BY date(b.verfall) ASC, d.name ASC, p.name ASC, b.id ASC
            LIMIT ? OFFSET ?
        """
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params + [safe_limit, safe_offset])).fetchall()
            return [dict(row) for row in rows]

    def count_verfall_items(
        self,
        depot_ids: list[int] | None = None,
        praeparat_ids: list[int] | None = None,
        search_text: str | None = None,
        category: str | None = None,
        critical_days: int = 30,
        warning_days: int = 90,
        attention_days: int = 180,
    ) -> int:
        filter_sql, params = self._build_verfall_filter_sql(
            depot_ids=depot_ids,
            praeparat_ids=praeparat_ids,
            search_text=search_text,
            category=category,
            critical_days=critical_days,
            warning_days=warning_days,
            attention_days=attention_days,
        )
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) {filter_sql}",
                tuple(params),
            ).fetchone()
            return int(row[0] if row else 0)

    def list_new_critical_expiry_events(
        self,
        since_iso: str | None = None,
        limit: int = 25,
        critical_days: int = 30,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 100))
        safe_critical_days = max(1, min(int(critical_days), 365))
        since_date = None
        if since_iso:
            text = str(since_iso).strip()
            if text:
                try:
                    since_date = datetime.fromisoformat(text.replace("Z", "+00:00")).date()
                except ValueError:
                    since_date = None
        today = date.today()
        with self._connect() as conn:
            sql = """
                SELECT
                    b.id,
                    d.name AS depot,
                    p.name AS praeparat,
                    b.charge,
                    b.verfall,
                    b.anzahl,
                    date(b.verfall, ?) AS critical_since,
                    CAST(julianday(date(b.verfall)) - julianday(date('now')) AS INTEGER) AS tage_bis_verfall
                FROM bewegungen b
                JOIN depots d ON d.id = b.depot_id
                JOIN praeparate p ON p.id = b.praeparat_id
                WHERE b.typ = 'Zugang'
                  AND COALESCE(b.verfall, '') <> ''
                  AND date(b.verfall) <= date('now', ?)
            """
            params: list[Any] = [f"-{safe_critical_days} day", f"+{safe_critical_days} day"]
            if since_date is not None:
                sql += " AND date(b.verfall, ?) > ?"
                params.extend([f"-{safe_critical_days} day", since_date.isoformat()])
            sql += " ORDER BY date(b.verfall) ASC, b.id ASC LIMIT ?"
            params.append(safe_limit)
            rows = [dict(row) for row in conn.execute(sql, tuple(params)).fetchall()]

        for row in rows:
            verfall_text = str(row.get("verfall") or "")
            try:
                verfall_day = datetime.strptime(verfall_text, "%Y-%m-%d").date()
                event_day = verfall_day - timedelta(days=safe_critical_days)
                row["event_at"] = datetime.combine(event_day, datetime.min.time(), tzinfo=UTC).isoformat()
            except ValueError:
                row["event_at"] = datetime.combine(today, datetime.min.time(), tzinfo=UTC).isoformat()
        return rows

    def log_audit(
        self,
        username: str,
        action: str,
        resource_type: str,
        resource_id: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> int:
        safe_username = (username or "").strip() or "unknown"
        safe_action = (action or "").strip()
        safe_resource = (resource_type or "").strip()
        if not safe_action:
            raise ValueError("Audit action darf nicht leer sein.")
        if not safe_resource:
            raise ValueError("Audit resource_type darf nicht leer sein.")
        details_json = json.dumps(details or {}, ensure_ascii=True)
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO api_audit_log (
                    timestamp, username, action, resource_type, resource_id, details
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    safe_username,
                    safe_action,
                    safe_resource,
                    int(resource_id) if resource_id is not None else None,
                    details_json,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def list_audit_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        q: str = "",
        action: str = "",
        resource_type: str = "",
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 500))
        safe_offset = max(0, int(offset))
        like = f"%{(q or '').strip()}%"
        safe_action = (action or "").strip()
        safe_resource = (resource_type or "").strip()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, timestamp, username, action, resource_type, resource_id, details
                FROM api_audit_log
                WHERE (? = '%%' OR
                      COALESCE(username, '') LIKE ? OR
                      COALESCE(details, '') LIKE ?)
                  AND (? = '' OR action = ?)
                  AND (? = '' OR resource_type = ?)
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (
                    like,
                    like,
                    like,
                    safe_action,
                    safe_action,
                    safe_resource,
                    safe_resource,
                    safe_limit,
                    safe_offset,
                ),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_sync_batch_result(self, batch_id: str) -> dict[str, Any] | None:
        safe_batch = (batch_id or "").strip()
        if not safe_batch:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT result_json FROM sync_push_batches WHERE batch_id = ?",
                (safe_batch,),
            ).fetchone()
        if not row:
            return None
        raw = row["result_json"] if isinstance(row, sqlite3.Row) else row[0]
        if not raw:
            return None
        try:
            payload = json.loads(str(raw))
            return payload if isinstance(payload, dict) else None
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    def save_sync_batch_result(self, batch_id: str, username: str, result: dict[str, Any]) -> None:
        safe_batch = (batch_id or "").strip()
        if not safe_batch:
            raise ValueError("batch_id darf nicht leer sein.")
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        result_json = json.dumps(result or {}, ensure_ascii=True)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sync_push_batches (batch_id, username, received_at, result_json)
                VALUES (?, ?, ?, ?)
                """,
                (safe_batch, (username or "").strip() or "unknown", timestamp, result_json),
            )
            conn.commit()

    def get_import_batch_result(self, batch_id: str) -> dict[str, Any] | None:
        safe_batch = (batch_id or "").strip()
        if not safe_batch:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT result_json FROM import_batches WHERE batch_id = ?",
                (safe_batch,),
            ).fetchone()
        if not row:
            return None
        raw = row["result_json"] if isinstance(row, sqlite3.Row) else row[0]
        if not raw:
            return None
        try:
            payload = json.loads(str(raw))
            return payload if isinstance(payload, dict) else None
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    def save_import_batch_result(self, batch_id: str, username: str, result: dict[str, Any]) -> None:
        safe_batch = (batch_id or "").strip()
        if not safe_batch:
            raise ValueError("batch_id darf nicht leer sein.")
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        result_json = json.dumps(result or {}, ensure_ascii=True)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO import_batches (batch_id, username, received_at, result_json)
                VALUES (?, ?, ?, ?)
                """,
                (safe_batch, (username or "").strip() or "unknown", timestamp, result_json),
            )
            conn.commit()

    def list_sync_audit_changes(
        self,
        cursor: int = 0,
        entities: list[str] | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        safe_cursor = max(0, int(cursor))
        safe_limit = max(1, min(int(limit), 1000))
        safe_entities = sorted({str(item).strip() for item in (entities or []) if str(item).strip()})
        with self._connect() as conn:
            if safe_entities:
                placeholders = ",".join("?" for _ in safe_entities)
                sql = "".join(
                    [
                        """
                        SELECT id, timestamp, username, action, resource_type, resource_id, details
                        FROM api_audit_log
                        WHERE id > ? AND resource_type IN (""",
                        placeholders,
                        """)
                        ORDER BY id ASC
                        LIMIT ?
                        """,
                    ]
                )
                rows = conn.execute(
                    sql,
                    (safe_cursor, *safe_entities, safe_limit + 1),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, timestamp, username, action, resource_type, resource_id, details
                    FROM api_audit_log
                    WHERE id > ?
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    (safe_cursor, safe_limit + 1),
                ).fetchall()

        has_more = len(rows) > safe_limit
        sliced = rows[:safe_limit]
        changes: list[dict[str, Any]] = []
        next_cursor = safe_cursor
        for row in sliced:
            row_dict = dict(row)
            next_cursor = int(row_dict["id"])
            details_text = row_dict.get("details")
            details: dict[str, Any] | None = None
            if isinstance(details_text, str) and details_text.strip():
                try:
                    parsed = json.loads(details_text)
                    if isinstance(parsed, dict):
                        details = parsed
                except (TypeError, ValueError, json.JSONDecodeError):
                    details = None
            changes.append(
                {
                    "change_id": int(row_dict["id"]),
                    "changed_at": str(row_dict.get("timestamp") or ""),
                    "actor": str(row_dict.get("username") or ""),
                    "operation": str(row_dict.get("action") or ""),
                    "entity": str(row_dict.get("resource_type") or ""),
                    "entity_id": row_dict.get("resource_id"),
                    "details": details,
                }
            )
        return {
            "changes": changes,
            "next_cursor": str(next_cursor),
            "has_more": has_more,
        }

    def get_latest_audit_cursor(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COALESCE(MAX(id), 0) AS max_id FROM api_audit_log").fetchone()
        if not row:
            return 0
        if isinstance(row, sqlite3.Row):
            return int(row["max_id"] or 0)
        return int(row[0] or 0)

    def get_sync_ops_stats(self) -> dict[str, Any]:
        with self._connect() as conn:
            batch_count_row = conn.execute("SELECT COUNT(*) AS c FROM sync_push_batches").fetchone()
            latest_batch_row = conn.execute(
                "SELECT batch_id, username, received_at FROM sync_push_batches ORDER BY received_at DESC LIMIT 1"
            ).fetchone()
            sync_change_row = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM api_audit_log
                WHERE COALESCE(details, '') LIKE '%"source": "sync_push"%'
                """
            ).fetchone()
            pending_outbox_row = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM sync_push_batches
                WHERE COALESCE(result_json, '') LIKE '%"deduplicated": false%'
                """
            ).fetchone()

        latest_batch = dict(latest_batch_row) if latest_batch_row else None
        return {
            "total_push_batches": int((batch_count_row["c"] if batch_count_row else 0) or 0),
            "total_audit_sync_changes": int((sync_change_row["c"] if sync_change_row else 0) or 0),
            "latest_push_batch": latest_batch,
            "non_deduplicated_batch_rows": int((pending_outbox_row["c"] if pending_outbox_row else 0) or 0),
            "latest_audit_cursor": self.get_latest_audit_cursor(),
        }

