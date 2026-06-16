"""SQLite data access for backend endpoints."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta, timezone
import json
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
                    telefon TEXT,
                    email TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS praeparate (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT
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
                    anzahl_empfaenger INTEGER
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
            self._ensure_bewegung_attachment_columns(cur)
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

    def list_depots(self, q: str = "", limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        like = f"%{(q or '').strip()}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, name, adresse, telefon, email
                FROM depots
                WHERE ? = '%%' OR
                      name LIKE ? OR
                      COALESCE(adresse, '') LIKE ? OR
                      COALESCE(telefon, '') LIKE ? OR
                      COALESCE(email, '') LIKE ?
                ORDER BY name
                LIMIT ? OFFSET ?
                """,
                (like, like, like, like, like, safe_limit, safe_offset),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_praeparate(self, q: str = "", limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        like = f"%{(q or '').strip()}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, name
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
            rows = conn.execute(
                # Placeholders are exclusively '?' generated from the count of
                # already-validated integer IDs; no user input reaches the SQL.
                f"SELECT id, name FROM praeparate WHERE id IN ({placeholders}) ORDER BY name",  # nosec B608
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

    def create_depot(
        self,
        name: str,
        adresse: str | None = None,
        telefon: str | None = None,
        email: str | None = None,
    ) -> int:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Depot-Name darf nicht leer sein.")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO depots (name, adresse, telefon, email)
                VALUES (?, ?, ?, ?)
                """,
                (
                    safe_name,
                    (adresse or "").strip() or None,
                    (telefon or "").strip() or None,
                    (email or "").strip() or None,
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

    def update_depot(
        self,
        depot_id: int,
        name: str,
        adresse: str | None = None,
        telefon: str | None = None,
        email: str | None = None,
    ) -> bool:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Depot-Name darf nicht leer sein.")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE depots
                SET name = ?, adresse = ?, telefon = ?, email = ?
                WHERE id = ?
                """,
                (
                    safe_name,
                    (adresse or "").strip() or None,
                    (telefon or "").strip() or None,
                    (email or "").strip() or None,
                    int(depot_id),
                ),
            )
            conn.commit()
            return cur.rowcount > 0

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

    def create_praeparat(self, name: str) -> int:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Praeparat-Name darf nicht leer sein.")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO praeparate (name) VALUES (?)",
                (safe_name,),
            )
            conn.commit()
            return int(cur.lastrowid)

    def update_praeparat(self, praeparat_id: int, name: str) -> bool:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Praeparat-Name darf nicht leer sein.")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE praeparate SET name = ? WHERE id = ?",
                (safe_name, int(praeparat_id)),
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

    def get_kontakte_by_depot_ids(self, depot_ids: list[int]) -> list[dict[str, Any]]:
        safe_ids = sorted({int(depot_id) for depot_id in depot_ids})
        if not safe_ids:
            return []
        placeholders = ",".join("?" for _ in safe_ids)
        with self._connect() as conn:
            rows = conn.execute(
                # Placeholders are exclusively '?' generated from the count of
                # already-validated integer IDs; no user input reaches the SQL.
                f"""
                SELECT
                    k.id,
                    k.name,
                    k.rolle,
                    k.email,
                    d.name AS depot_name,
                    d.id AS depot_id
                FROM kontakte k
                JOIN depots d ON d.id = k.depot_id
                WHERE k.depot_id IN ({placeholders})
                  AND COALESCE(k.email, '') <> ''
                ORDER BY d.name, k.name
                """,  # nosec B608
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
    ) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO email_verlauf (
                    datum, betreff, nachricht, empfaenger_depots, empfaenger_emails, anzahl_empfaenger
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    (betreff or "").strip(),
                    nachricht or "",
                    depot_names or "",
                    emails or "",
                    int(anzahl),
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def get_email_verlauf(self, limit: int = 50) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 500))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, datum, betreff, empfaenger_depots, anzahl_empfaenger
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
                SELECT id, datum, betreff, nachricht, empfaenger_depots, empfaenger_emails, anzahl_empfaenger
                FROM email_verlauf
                WHERE id = ?
                """,
                (int(email_id),),
            ).fetchone()
            return dict(row) if row else None

    def list_bewegungen(
        self,
        limit: int = 100,
        offset: int = 0,
        q: str = "",
        typ: str | None = None,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 500))
        safe_offset = max(0, int(offset))
        like = f"%{(q or '').strip()}%"
        safe_typ = (typ or "").strip()
        with self._connect() as conn:
            rows = conn.execute(
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
                ORDER BY id DESC
                LIMIT ?
                OFFSET ?
                """,
                (like, like, like, like, safe_typ, safe_typ, safe_limit, safe_offset),
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
                row["event_at"] = datetime.combine(event_day, datetime.min.time(), tzinfo=timezone.utc).isoformat()
            except ValueError:
                row["event_at"] = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc).isoformat()
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
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
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

