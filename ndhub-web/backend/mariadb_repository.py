"""MariaDB repository with SQLite fallback for non-ported queries.

This module enables incremental runtime cutover:
- core CRUD/read flows run against MariaDB
- complex analytics/reporting can still delegate to SQLite fallback
- write operations are dual-written to fallback to avoid regressions
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, date
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from backend.config import MariaDbSettings
from backend.database import SqliteRepository

ALLOWED_MOVEMENT_TYPES = {"Zugang", "Abgang", "Vernichtung"}
logger = logging.getLogger(__name__)


class MariaDbRepository:
    """MariaDB-first repository with SQLite compatibility fallback."""

    def __init__(self, settings: MariaDbSettings, fallback: SqliteRepository, dual_write_sqlite: bool = True):
        self.settings = settings
        self.fallback = fallback
        self.dual_write_sqlite = bool(dual_write_sqlite)
        self._ensure_institution_tables()
        self._ensure_email_verlauf_columns()
        self._ensure_praeparat_columns()

    def _ensure_institution_tables(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS institutions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(255) NOT NULL UNIQUE,
                        adresse TEXT,
                        latitude DOUBLE NULL,
                        longitude DOUBLE NULL
                    )
                    """
                )
                cur.execute("ALTER TABLE depots ADD COLUMN IF NOT EXISTS institution_id INT NULL")
                cur.execute("ALTER TABLE depots ADD COLUMN IF NOT EXISTS strasse TEXT NULL")
                cur.execute("ALTER TABLE depots ADD COLUMN IF NOT EXISTS hausnummer VARCHAR(64) NULL")
                cur.execute("ALTER TABLE depots ADD COLUMN IF NOT EXISTS postleitzahl VARCHAR(16) NULL")
                cur.execute("ALTER TABLE depots ADD COLUMN IF NOT EXISTS stadt VARCHAR(255) NULL")
                cur.execute("ALTER TABLE depots ADD COLUMN IF NOT EXISTS latitude DOUBLE NULL")
                cur.execute("ALTER TABLE depots ADD COLUMN IF NOT EXISTS longitude DOUBLE NULL")
                cur.execute("ALTER TABLE institutions ADD COLUMN IF NOT EXISTS strasse TEXT NULL")
                cur.execute("ALTER TABLE institutions ADD COLUMN IF NOT EXISTS hausnummer VARCHAR(64) NULL")
                cur.execute("ALTER TABLE institutions ADD COLUMN IF NOT EXISTS postleitzahl VARCHAR(16) NULL")
                cur.execute("ALTER TABLE institutions ADD COLUMN IF NOT EXISTS stadt VARCHAR(255) NULL")
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_depot_permissions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(255) NOT NULL,
                        depot_id INT NOT NULL,
                        can_read TINYINT(1) NOT NULL DEFAULT 0,
                        can_write TINYINT(1) NOT NULL DEFAULT 0,
                        UNIQUE KEY uq_user_depot_permissions (username, depot_id)
                    )
                    """
                )
                cur.execute("SELECT id FROM institutions ORDER BY id ASC LIMIT 1")
                row = cur.fetchone()
                if not row:
                    cur.execute(
                        "INSERT INTO institutions (name, adresse, latitude, longitude) VALUES (%s, %s, %s, %s)",
                        ("Standard-Institution", None, None, None),
                    )
                    default_id = int(cur.lastrowid)
                else:
                    default_id = int(row["id"])
                cur.execute("UPDATE depots SET institution_id = %s WHERE institution_id IS NULL", (default_id,))
                conn.commit()

    def _connect(self):
        return pymysql.connect(
            host=self.settings.host,
            port=self.settings.port,
            user=self.settings.user,
            password=self.settings.password,
            database=self.settings.database,
            charset="utf8mb4",
            autocommit=False,
            cursorclass=DictCursor,
        )

    def _to_json(self, payload: dict[str, Any] | None) -> str | None:
        if payload is None:
            return None
        return json.dumps(payload, ensure_ascii=False)

    def _ensure_sync_batch_table(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sync_push_batches (
                        batch_id VARCHAR(128) PRIMARY KEY,
                        username VARCHAR(255) NOT NULL,
                        received_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        result_json LONGTEXT NOT NULL
                    )
                    """
                )
                conn.commit()

    def _ensure_import_batch_table(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS import_batches (
                        batch_id VARCHAR(128) PRIMARY KEY,
                        username VARCHAR(255) NOT NULL,
                        received_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        result_json LONGTEXT NOT NULL
                    )
                    """
                )
                conn.commit()

    def _ensure_email_verlauf_columns(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS email_verlauf (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        datum DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        betreff VARCHAR(512),
                        nachricht LONGTEXT,
                        empfaenger_depots TEXT,
                        empfaenger_emails LONGTEXT,
                        anzahl_empfaenger INT
                    )
                    """
                )
                cur.execute("ALTER TABLE email_verlauf ADD COLUMN IF NOT EXISTS versand_status VARCHAR(32) NULL")
                cur.execute("ALTER TABLE email_verlauf ADD COLUMN IF NOT EXISTS versand_kanal VARCHAR(64) NULL")
                cur.execute("ALTER TABLE email_verlauf ADD COLUMN IF NOT EXISTS versand_fehler TEXT NULL")
                conn.commit()

    def _ensure_praeparat_columns(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("ALTER TABLE praeparate ADD COLUMN IF NOT EXISTS wirkstoff TEXT NULL")
                cur.execute("ALTER TABLE praeparate ADD COLUMN IF NOT EXISTS darreichungsform TEXT NULL")
                cur.execute("ALTER TABLE praeparate ADD COLUMN IF NOT EXISTS staerke TEXT NULL")
                cur.execute("ALTER TABLE praeparate ADD COLUMN IF NOT EXISTS einheit TEXT NULL")
                cur.execute("ALTER TABLE praeparate ADD COLUMN IF NOT EXISTS pzn TEXT NULL")
                cur.execute("ALTER TABLE praeparate ADD COLUMN IF NOT EXISTS hersteller TEXT NULL")
                conn.commit()

    def _ensure_iso_date(self, value: date | str) -> str:
        if isinstance(value, date):
            return value.isoformat()
        return str(value)

    def _ensure_date(self, value: date | str) -> date:
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))

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

    def _mirror_write(self, method_name: str, *args, **kwargs) -> Any:
        if not self.dual_write_sqlite:
            return None
        method = getattr(self.fallback, method_name)
        try:
            return method(*args, **kwargs)
        except Exception as exc:
            logger.warning("SQLite mirror write failed for %s: %s", method_name, exc)
            return None

    # ---- core master data -------------------------------------------------
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
            placeholders = ",".join("%s" for _ in safe_ids)
            ids_filter_sql = "".join([" AND depots.id IN (", placeholders, ")"])
            ids_params = tuple(safe_ids)
        with self._connect() as conn:
            with conn.cursor() as cur:
                sql_parts = [
                    """
                    SELECT depots.id, depots.name, depots.adresse, depots.strasse, depots.hausnummer, depots.postleitzahl, depots.stadt, depots.telefon, depots.email,
                           depots.institution_id, depots.latitude, depots.longitude, institutions.name AS institution_name
                    FROM depots
                    LEFT JOIN institutions ON institutions.id = depots.institution_id
                    WHERE (
                          %s = '%%' OR
                          depots.name LIKE %s OR
                          COALESCE(depots.adresse, '') LIKE %s OR
                          COALESCE(depots.telefon, '') LIKE %s OR
                          COALESCE(depots.email, '') LIKE %s
                    )
                    """,
                ]
                if ids_filter_sql:
                    sql_parts.append(ids_filter_sql)
                sql_parts.append("ORDER BY depots.name LIMIT %s OFFSET %s")
                cur.execute(
                    "".join(sql_parts),
                    (like, like, like, like, like, *ids_params, safe_limit, safe_offset),
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]

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
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO depots (name, adresse, strasse, hausnummer, postleitzahl, stadt, telefon, email, institution_id, latitude, longitude)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                new_id = int(cur.lastrowid)
        self._mirror_write(
            "create_depot",
            name=safe_name,
            adresse=adresse,
            strasse=strasse,
            hausnummer=hausnummer,
            postleitzahl=postleitzahl,
            stadt=stadt,
            telefon=telefon,
            email=email,
            institution_id=institution_id,
            latitude=latitude,
            longitude=longitude,
        )
        return new_id

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
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE depots
                    SET name = %s, adresse = %s, strasse = %s, hausnummer = %s, postleitzahl = %s, stadt = %s, telefon = %s, email = %s, institution_id = %s, latitude = %s, longitude = %s
                    WHERE id = %s
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
                changed = cur.rowcount > 0
                conn.commit()
        self._mirror_write(
            "update_depot",
            depot_id=depot_id,
            name=safe_name,
            adresse=adresse,
            strasse=strasse,
            hausnummer=hausnummer,
            postleitzahl=postleitzahl,
            stadt=stadt,
            telefon=telefon,
            email=email,
            institution_id=institution_id,
            latitude=latitude,
            longitude=longitude,
        )
        return changed

    def delete_depot(self, depot_id: int) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS used_count FROM bewegungen WHERE depot_id = %s", (int(depot_id),))
                used = int(cur.fetchone()["used_count"])
                if used > 0:
                    raise ValueError("Depot kann nicht gelöscht werden, da Bewegungen vorhanden sind.")
                cur.execute("DELETE FROM depots WHERE id = %s", (int(depot_id),))
                changed = cur.rowcount > 0
                conn.commit()
        self._mirror_write("delete_depot", depot_id)
        return changed

    def get_depot_name(self, depot_id: int) -> str | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT name FROM depots WHERE id = %s", (int(depot_id),))
                row = cur.fetchone()
        return str(row["name"]) if row and row.get("name") is not None else None

    def get_depot(self, depot_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT depots.id, depots.name, depots.adresse, depots.strasse, depots.hausnummer, depots.postleitzahl, depots.stadt, depots.telefon, depots.email,
                           depots.institution_id, depots.latitude, depots.longitude, institutions.name AS institution_name
                    FROM depots
                    LEFT JOIN institutions ON institutions.id = depots.institution_id
                    WHERE depots.id = %s
                    """,
                    (int(depot_id),),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def list_institutions(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, adresse, strasse, hausnummer, postleitzahl, stadt, latitude, longitude
                    FROM institutions
                    ORDER BY name
                    """
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_onboarding_status(self) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM institutions")
                institutions = int((cur.fetchone() or {}).get("c") or 0)
                cur.execute("SELECT COUNT(*) AS c FROM depots")
                depots = int((cur.fetchone() or {}).get("c") or 0)
                cur.execute("SELECT COUNT(*) AS c FROM praeparate")
                praeparate = int((cur.fetchone() or {}).get("c") or 0)
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
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO institutions (name, adresse, strasse, hausnummer, postleitzahl, stadt, latitude, longitude)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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
                new_id = int(cur.lastrowid)
        self._mirror_write(
            "create_institution",
            name=safe_name,
            adresse=adresse,
            strasse=strasse,
            hausnummer=hausnummer,
            postleitzahl=postleitzahl,
            stadt=stadt,
            latitude=latitude,
            longitude=longitude,
        )
        return new_id

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
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        """
                    INSERT INTO institutions (name, adresse, strasse, hausnummer, postleitzahl, stadt, latitude, longitude)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
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
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                                VALUES (%s, %s, %s)
                                """,
                                (depot_id, praeparat_id, sollbestand),
                            )
                            assignment_count += 1
                        if assignment_count == 0:
                            raise ValueError(f"Depot '{depot_name}' hat keine gueltige Praeparate-Zuordnung.")
                        created_depots.append({"id": depot_id, "name": depot_name, "assignments": assignment_count})
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise

        self._mirror_write(
            "create_onboarding_setup",
            institution=institution,
            praeparate=praeparate,
            depots=depots,
        )
        return {
            "institution_id": institution_id,
            "praeparate_count": len(normalized_praeparate),
            "depots": created_depots,
        }

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
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE institutions
                    SET name = %s, adresse = %s, strasse = %s, hausnummer = %s, postleitzahl = %s, stadt = %s, latitude = %s, longitude = %s
                    WHERE id = %s
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
                changed = cur.rowcount > 0
                conn.commit()
        self._mirror_write(
            "update_institution",
            institution_id=institution_id,
            name=safe_name,
            adresse=adresse,
            strasse=strasse,
            hausnummer=hausnummer,
            postleitzahl=postleitzahl,
            stadt=stadt,
            latitude=latitude,
            longitude=longitude,
        )
        return changed

    def delete_institution(self, institution_id: int) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM depots WHERE institution_id = %s", (int(institution_id),))
                used = int((cur.fetchone() or {}).get("c") or 0)
                if used > 0:
                    raise ValueError("Institution ist noch Depots zugeordnet.")
                cur.execute("DELETE FROM institutions WHERE id = %s", (int(institution_id),))
                changed = cur.rowcount > 0
                conn.commit()
        self._mirror_write("delete_institution", institution_id)
        return changed

    def set_user_depot_permission(self, username: str, depot_id: int, can_read: bool, can_write: bool) -> None:
        safe_username = (username or "").strip()
        if not safe_username:
            raise ValueError("Benutzername fehlt.")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_depot_permissions (username, depot_id, can_read, can_write)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE can_read = VALUES(can_read), can_write = VALUES(can_write)
                    """,
                    (safe_username, int(depot_id), int(bool(can_read)), int(bool(can_write))),
                )
                conn.commit()
        self._mirror_write(
            "set_user_depot_permission",
            username=safe_username,
            depot_id=depot_id,
            can_read=can_read,
            can_write=can_write,
        )

    def list_user_depot_permissions(self, username: str) -> list[dict[str, Any]]:
        safe_username = (username or "").strip()
        if not safe_username:
            return []
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT udp.depot_id, udp.can_read, udp.can_write, depots.name AS depot_name
                    FROM user_depot_permissions udp
                    JOIN depots ON depots.id = udp.depot_id
                    WHERE udp.username = %s
                    ORDER BY depots.name
                    """,
                    (safe_username,),
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def list_map_institutions_with_depots(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
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
                )
                rows = cur.fetchall()
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
            if row.get("depot_id") is not None:
                item["depots"].append(
                    {
                        "id": int(row["depot_id"]),
                        "name": row.get("depot_name"),
                        "adresse": row.get("depot_adresse"),
                        "strasse": row.get("depot_strasse"),
                        "hausnummer": row.get("depot_hausnummer"),
                        "postleitzahl": row.get("depot_postleitzahl"),
                        "stadt": row.get("depot_stadt"),
                        "latitude": row.get("depot_latitude"),
                        "longitude": row.get("depot_longitude"),
                    }
                )
        return list(grouped.values())

    def list_praeparate(self, q: str = "", limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        like = f"%{(q or '').strip()}%"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller
                    FROM praeparate
                    WHERE %s = '%%' OR name LIKE %s
                    ORDER BY name
                    LIMIT %s OFFSET %s
                    """,
                    (like, like, safe_limit, safe_offset),
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]

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
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO praeparate (name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
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
                new_id = int(cur.lastrowid)
        self._mirror_write(
            "create_praeparat",
            name=safe_name,
            wirkstoff=wirkstoff,
            darreichungsform=darreichungsform,
            staerke=staerke,
            einheit=einheit,
            pzn=pzn,
            hersteller=hersteller,
        )
        return new_id

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
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE praeparate
                    SET name = %s, wirkstoff = %s, darreichungsform = %s, staerke = %s, einheit = %s, pzn = %s, hersteller = %s
                    WHERE id = %s
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
                changed = cur.rowcount > 0
                conn.commit()
        self._mirror_write(
            "update_praeparat",
            praeparat_id=praeparat_id,
            name=safe_name,
            wirkstoff=wirkstoff,
            darreichungsform=darreichungsform,
            staerke=staerke,
            einheit=einheit,
            pzn=pzn,
            hersteller=hersteller,
        )
        return changed

    def delete_praeparat(self, praeparat_id: int) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS used_count FROM bewegungen WHERE praeparat_id = %s", (int(praeparat_id),))
                used = int(cur.fetchone()["used_count"])
                if used > 0:
                    raise ValueError("Praeparat kann nicht gelöscht werden, da Bewegungen vorhanden sind.")
                cur.execute("DELETE FROM praeparate WHERE id = %s", (int(praeparat_id),))
                changed = cur.rowcount > 0
                conn.commit()
        self._mirror_write("delete_praeparat", praeparat_id)
        return changed

    def get_praeparat(self, praeparat_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller FROM praeparate WHERE id = %s",
                    (int(praeparat_id),),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def list_praeparate_for_depot(self, depot_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT praeparat_id FROM depot_praeparate WHERE depot_id = %s",
                    (int(depot_id),),
                )
                assigned_rows = cur.fetchall()
                assigned_ids = {int(row["praeparat_id"]) for row in assigned_rows}
                if not assigned_ids:
                    cur.execute("SELECT id, name FROM praeparate ORDER BY name")
                    return [dict(row) for row in cur.fetchall()]
                placeholders = ", ".join(["%s"] * len(assigned_ids))
                sql = "".join(
                    [
                        "SELECT id, name FROM praeparate WHERE id IN (",
                        placeholders,
                        ") ORDER BY name",
                    ]
                )
                cur.execute(sql, tuple(sorted(assigned_ids)))
                return [dict(row) for row in cur.fetchall()]

    def list_depot_assignments(self, depot_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        p.id AS praeparat_id,
                        p.name AS praeparat_name,
                        CASE WHEN dp.praeparat_id IS NULL THEN 0 ELSE 1 END AS assigned,
                        COALESCE(dp.sollbestand, 0) AS sollbestand
                    FROM praeparate p
                    LEFT JOIN depot_praeparate dp
                        ON dp.praeparat_id = p.id AND dp.depot_id = %s
                    ORDER BY p.name
                    """,
                    (int(depot_id),),
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def set_depot_assignments(self, depot_id: int, assignments: list[dict[str, Any]]) -> None:
        safe_depot_id = int(depot_id)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM depots WHERE id = %s", (safe_depot_id,))
                if cur.fetchone() is None:
                    raise ValueError("Depot nicht gefunden.")
                cur.execute("DELETE FROM depot_praeparate WHERE depot_id = %s", (safe_depot_id,))
                for entry in assignments:
                    praeparat_id = int(entry["praeparat_id"])
                    sollbestand = int(entry.get("sollbestand", 0))
                    if sollbestand < 0:
                        raise ValueError("Sollbestand darf nicht negativ sein.")
                    cur.execute("SELECT id FROM praeparate WHERE id = %s", (praeparat_id,))
                    if cur.fetchone() is None:
                        raise ValueError(f"Praeparat existiert nicht: {praeparat_id}")
                    cur.execute(
                        """
                        INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand)
                        VALUES (%s, %s, %s)
                        """,
                        (safe_depot_id, praeparat_id, sollbestand),
                    )
                conn.commit()
        self._mirror_write("set_depot_assignments", depot_id=safe_depot_id, assignments=assignments)

    # ---- contacts / email --------------------------------------------------
    def list_kontakte(self, depot_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, depot_id, name, rolle, telefon, email
                    FROM kontakte
                    WHERE depot_id = %s
                    ORDER BY name
                    """,
                    (int(depot_id),),
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def create_kontakt(self, depot_id: int, name: str, rolle: str | None = None, telefon: str | None = None, email: str | None = None) -> int:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Kontaktname darf nicht leer sein.")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO kontakte (depot_id, name, rolle, telefon, email)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        int(depot_id),
                        safe_name,
                        (rolle or "").strip() or None,
                        (telefon or "").strip() or None,
                        (email or "").strip() or None,
                    ),
                )
                conn.commit()
                new_id = int(cur.lastrowid)
        self._mirror_write("create_kontakt", depot_id=depot_id, name=safe_name, rolle=rolle, telefon=telefon, email=email)
        return new_id

    def update_kontakt(self, kontakt_id: int, name: str, rolle: str | None = None, telefon: str | None = None, email: str | None = None) -> bool:
        safe_name = (name or "").strip()
        if not safe_name:
            raise ValueError("Kontaktname darf nicht leer sein.")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE kontakte
                    SET name = %s, rolle = %s, telefon = %s, email = %s
                    WHERE id = %s
                    """,
                    (
                        safe_name,
                        (rolle or "").strip() or None,
                        (telefon or "").strip() or None,
                        (email or "").strip() or None,
                        int(kontakt_id),
                    ),
                )
                changed = cur.rowcount > 0
                conn.commit()
        self._mirror_write("update_kontakt", kontakt_id=kontakt_id, name=safe_name, rolle=rolle, telefon=telefon, email=email)
        return changed

    def delete_kontakt(self, kontakt_id: int) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM kontakte WHERE id = %s", (int(kontakt_id),))
                changed = cur.rowcount > 0
                conn.commit()
        self._mirror_write("delete_kontakt", kontakt_id)
        return changed

    def get_kontakt(self, kontakt_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, depot_id, name, rolle, telefon, email FROM kontakte WHERE id = %s",
                    (int(kontakt_id),),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def get_kontakte_by_depot_ids(self, depot_ids: list[int]) -> list[dict[str, Any]]:
        if not depot_ids:
            return []
        placeholders = ", ".join(["%s"] * len(depot_ids))
        sql = "".join(
            [
                """
                SELECT k.id, k.depot_id, k.name, k.rolle, k.telefon, k.email, d.name AS depot_name
                FROM kontakte k
                JOIN depots d ON d.id = k.depot_id
                WHERE k.depot_id IN (""",
                placeholders,
                """) AND COALESCE(k.email, '') <> ''
                ORDER BY d.name, k.name
                """,
            ]
        )
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(int(item) for item in depot_ids))
                rows = cur.fetchall()
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
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO email_verlauf (
                        datum, betreff, nachricht, empfaenger_depots, empfaenger_emails,
                        anzahl_empfaenger, versand_status, versand_kanal, versand_fehler
                    )
                    VALUES (UTC_TIMESTAMP(), %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        betreff,
                        nachricht,
                        depot_names,
                        emails,
                        int(anzahl),
                        (versand_status or "draft").strip() or "draft",
                        (versand_kanal or "").strip() or None,
                        (versand_fehler or "").strip() or None,
                    ),
                )
                conn.commit()
                new_id = int(cur.lastrowid)
        self._mirror_write(
            "add_email_verlauf",
            betreff=betreff,
            nachricht=nachricht,
            depot_names=depot_names,
            emails=emails,
            anzahl=anzahl,
            versand_status=versand_status,
            versand_kanal=versand_kanal,
            versand_fehler=versand_fehler,
        )
        return new_id

    def get_email_verlauf(self, limit: int = 50) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 200))
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id, datum, betreff, empfaenger_depots, anzahl_empfaenger,
                        COALESCE(versand_status, 'draft') AS versand_status,
                        COALESCE(versand_kanal, '') AS versand_kanal
                    FROM email_verlauf
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (safe_limit,),
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_email_details(self, email_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id, datum, betreff, nachricht, empfaenger_depots, empfaenger_emails, anzahl_empfaenger,
                        COALESCE(versand_status, 'draft') AS versand_status,
                        COALESCE(versand_kanal, '') AS versand_kanal,
                        COALESCE(versand_fehler, '') AS versand_fehler
                    FROM email_verlauf
                    WHERE id = %s
                    """,
                    (int(email_id),),
                )
                row = cur.fetchone()
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
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE email_verlauf
                    SET versand_status = %s,
                        versand_kanal = %s,
                        versand_fehler = %s
                    WHERE id = %s
                    """,
                    (safe_status, safe_channel, safe_error, int(email_id)),
                )
                conn.commit()
                changed = cur.rowcount > 0
        self._mirror_write(
            "update_email_delivery_status",
            email_id=int(email_id),
            versand_status=safe_status,
            versand_kanal=safe_channel,
            versand_fehler=safe_error,
        )
        return changed

    # ---- movements ---------------------------------------------------------
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
        safe_limit = max(1, min(int(limit), 300))
        safe_offset = max(0, int(offset))
        like = f"%{(q or '').strip()}%"
        typ_filter = (typ or "").strip()
        safe_depot_id = int(depot_id) if depot_id is not None else 0
        safe_depot_ids = sorted({int(item) for item in (depot_ids or []) if int(item) > 0})
        safe_praeparat_id = int(praeparat_id) if praeparat_id is not None else 0
        only_with_attachment = bool(has_attachment) if has_attachment is not None else False
        safe_start_date = (start_date or "").strip()
        safe_end_date = (end_date or "").strip()
        ids_filter_sql = ""
        ids_params: tuple[Any, ...] = ()
        if safe_depot_ids:
            placeholders = ",".join("%s" for _ in safe_depot_ids)
            ids_filter_sql = "".join([" AND b.depot_id IN (", placeholders, ")"])
            ids_params = tuple(safe_depot_ids)
        with self._connect() as conn:
            with conn.cursor() as cur:
                sql_parts = [
                    """
                    SELECT
                        b.id,
                        b.depot_id,
                        d.name AS depot_name,
                        b.praeparat_id,
                        p.name AS praeparat_name,
                        b.charge,
                        b.verfall,
                        b.eingang_datum,
                        b.ausgang_datum,
                        b.empfaenger,
                        b.anzahl,
                        b.typ,
                        b.datei_pfad,
                        b.datei_name,
                        b.datei_groesse,
                        b.datei_hochgeladen_am
                    FROM bewegungen b
                    JOIN depots d ON d.id = b.depot_id
                    JOIN praeparate p ON p.id = b.praeparat_id
                    WHERE
                        (%s = '' OR b.typ = %s) AND
                        (%s = 0 OR b.depot_id = %s) AND
                        (%s = 0 OR b.praeparat_id = %s) AND
                        (%s = 0 OR COALESCE(b.datei_pfad, '') <> '') AND
                        (%s = '' OR COALESCE(b.eingang_datum, b.ausgang_datum, '') >= %s) AND
                        (%s = '' OR COALESCE(b.eingang_datum, b.ausgang_datum, '') <= %s) AND
                        (
                            %s = '%%' OR
                            d.name LIKE %s OR
                            p.name LIKE %s OR
                            COALESCE(b.charge, '') LIKE %s OR
                            COALESCE(b.empfaenger, '') LIKE %s
                        )
                    """,
                ]
                if ids_filter_sql:
                    sql_parts.append(ids_filter_sql)
                sql_parts.append("ORDER BY b.id DESC LIMIT %s OFFSET %s")
                cur.execute(
                    "".join(sql_parts),
                    (
                        typ_filter,
                        typ_filter,
                        safe_depot_id,
                        safe_depot_id,
                        safe_praeparat_id,
                        safe_praeparat_id,
                        1 if only_with_attachment else 0,
                        safe_start_date,
                        safe_start_date,
                        safe_end_date,
                        safe_end_date,
                        like,
                        like,
                        like,
                        like,
                        like,
                        *ids_params,
                        safe_limit,
                        safe_offset,
                    ),
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_bewegung(self, bewegung_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM bewegungen WHERE id = %s", (int(bewegung_id),))
                row = cur.fetchone()
        return dict(row) if row else None

    def set_bewegung_attachment(self, bewegung_id: int, datei_pfad: str, datei_name: str, datei_groesse: int, datei_hochgeladen_am: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE bewegungen
                    SET datei_pfad = %s,
                        datei_name = %s,
                        datei_groesse = %s,
                        datei_hochgeladen_am = %s
                    WHERE id = %s
                    """,
                    (datei_pfad, datei_name, int(datei_groesse), datei_hochgeladen_am, int(bewegung_id)),
                )
                conn.commit()
        self._mirror_write("set_bewegung_attachment", bewegung_id, datei_pfad, datei_name, datei_groesse, datei_hochgeladen_am)

    def insert_bewegung(
        self,
        depot_id: int,
        praeparat_id: int,
        typ: str,
        charge: str,
        verfall: date | str,
        datum: date | str,
        anzahl: int,
        empfaenger: str | None = None,
    ) -> int:
        movement_type = (typ or "").strip()
        if movement_type not in ALLOWED_MOVEMENT_TYPES:
            raise ValueError("Ungueltiger Bewegungstyp.")
        if int(anzahl) <= 0:
            raise ValueError("Anzahl muss groesser als 0 sein.")

        empfaenger_value = (empfaenger or "").strip() or None
        datum_iso = self._ensure_iso_date(datum)
        verfall_iso = self._ensure_iso_date(verfall)
        eingang_datum = datum_iso if movement_type == "Zugang" else None
        ausgang_datum = datum_iso if movement_type in {"Abgang", "Vernichtung"} else None

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM depots WHERE id = %s", (int(depot_id),))
                if cur.fetchone() is None:
                    raise ValueError("Depot nicht gefunden.")
                cur.execute("SELECT id FROM praeparate WHERE id = %s", (int(praeparat_id),))
                if cur.fetchone() is None:
                    raise ValueError("Praeparat nicht gefunden.")
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM depot_praeparate WHERE depot_id = %s",
                    (int(depot_id),),
                )
                assignment_count = int(cur.fetchone()["cnt"])
                if assignment_count > 0:
                    cur.execute(
                        """
                        SELECT COUNT(*) AS cnt
                        FROM depot_praeparate
                        WHERE depot_id = %s AND praeparat_id = %s
                        """,
                        (int(depot_id), int(praeparat_id)),
                    )
                    if int(cur.fetchone()["cnt"]) == 0:
                        raise ValueError("Praeparat ist diesem Depot nicht zugeordnet.")

                cur.execute(
                    """
                    INSERT INTO bewegungen (
                        depot_id, praeparat_id, charge, verfall,
                        eingang_datum, ausgang_datum, empfaenger, anzahl, typ
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        int(depot_id),
                        int(praeparat_id),
                        (charge or "").strip(),
                        verfall_iso,
                        eingang_datum,
                        ausgang_datum,
                        empfaenger_value,
                        int(anzahl),
                        movement_type,
                    ),
                )
                conn.commit()
                new_id = int(cur.lastrowid)
        self._mirror_write(
            "insert_bewegung",
            depot_id=depot_id,
            praeparat_id=praeparat_id,
            typ=typ,
            charge=charge,
            verfall=verfall_iso,
            datum=datum_iso,
            anzahl=anzahl,
            empfaenger=empfaenger,
        )
        return new_id

    # ---- analytics / dashboard / expiry -----------------------------------
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
                DATE_FORMAT(COALESCE(b.eingang_datum, b.ausgang_datum), '%%Y-%%m') AS monat,
                SUM(b.anzahl) AS anzahl
            FROM bewegungen b
            JOIN depots d ON d.id = b.depot_id
            JOIN praeparate p ON p.id = b.praeparat_id
            WHERE 1=1
        """
        params: list[Any] = []
        if depot_ids:
            placeholders = ",".join(["%s"] * len(depot_ids))
            sql += f" AND b.depot_id IN ({placeholders})"
            params.extend(int(item) for item in depot_ids)
        if praeparat_ids:
            placeholders = ",".join(["%s"] * len(praeparat_ids))
            sql += f" AND b.praeparat_id IN ({placeholders})"
            params.extend(int(item) for item in praeparat_ids)
        if start_date:
            sql += " AND COALESCE(b.eingang_datum, b.ausgang_datum) >= %s"
            params.append(start_date)
        if end_date:
            sql += " AND COALESCE(b.eingang_datum, b.ausgang_datum) <= %s"
            params.append(end_date)
        sql += " GROUP BY d.name, p.name, b.typ, monat ORDER BY monat, d.name, p.name"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
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
            placeholders = ",".join(["%s"] * len(depot_ids))
            sql += f" AND dp.depot_id IN ({placeholders})"
            params.extend(int(item) for item in depot_ids)
        if praeparat_ids:
            placeholders = ",".join(["%s"] * len(praeparat_ids))
            sql += f" AND dp.praeparat_id IN ({placeholders})"
            params.extend(int(item) for item in praeparat_ids)
        sql += " GROUP BY d.name, p.name, dp.sollbestand ORDER BY d.name, p.name"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
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
            placeholders = ",".join(["%s"] * len(depot_ids))
            sql += f" AND b.depot_id IN ({placeholders})"
            params.extend(int(item) for item in depot_ids)
        if start_date:
            sql += " AND COALESCE(b.ausgang_datum, b.eingang_datum) >= %s"
            params.append(start_date)
        if end_date:
            sql += " AND COALESCE(b.ausgang_datum, b.eingang_datum) <= %s"
            params.append(end_date)
        sql += " GROUP BY p.name ORDER BY anzahl DESC LIMIT %s"
        params.append(max(1, min(int(limit), 50)))
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
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
            placeholders = ",".join(["%s"] * len(praeparat_ids))
            sql += f" AND b.praeparat_id IN ({placeholders})"
            params.extend(int(item) for item in praeparat_ids)
        if start_date:
            sql += " AND COALESCE(b.ausgang_datum, b.eingang_datum) >= %s"
            params.append(start_date)
        if end_date:
            sql += " AND COALESCE(b.ausgang_datum, b.eingang_datum) <= %s"
            params.append(end_date)
        sql += " GROUP BY d.name ORDER BY anzahl DESC LIMIT %s"
        params.append(max(1, min(int(limit), 50)))
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_matrix_data(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
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
                    """,
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_verfall_prognose(
        self,
        depot_ids: list[int] | None = None,
        praeparat_ids: list[int] | None = None,
        horizon_months: int = 24,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                DATE_FORMAT(b.verfall, '%%Y-%%m') AS verfall_monat,
                SUM(b.anzahl) AS anzahl
            FROM bewegungen b
            WHERE b.typ = 'Zugang'
              AND COALESCE(b.verfall, '') <> ''
        """
        params: list[Any] = []
        if depot_ids:
            placeholders = ",".join(["%s"] * len(depot_ids))
            sql += f" AND b.depot_id IN ({placeholders})"
            params.extend(int(item) for item in depot_ids)
        if praeparat_ids:
            placeholders = ",".join(["%s"] * len(praeparat_ids))
            sql += f" AND b.praeparat_id IN ({placeholders})"
            params.extend(int(item) for item in praeparat_ids)
        sql += " GROUP BY verfall_monat ORDER BY verfall_monat"
        _ = horizon_months
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
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
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM depots")
                depot_count = int(cur.fetchone()["c"])
                cur.execute("SELECT COUNT(*) AS c FROM praeparate")
                praeparat_count = int(cur.fetchone()["c"])
                cur.execute("SELECT COUNT(*) AS c FROM bewegungen")
                bewegung_count = int(cur.fetchone()["c"])
                cur.execute(
                    """
                    SELECT COALESCE(SUM(anzahl), 0) AS c
                    FROM bewegungen
                    WHERE typ = 'Zugang'
                      AND COALESCE(verfall, '') <> ''
                      AND DATE(verfall) <= DATE_ADD(CURDATE(), INTERVAL %s DAY)
                    """,
                    (safe_critical_days,),
                )
                kritische_verfaelle = int(cur.fetchone()["c"] or 0)
                cur.execute(
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
                    LIMIT %s
                    """,
                    (safe_activity_limit,),
                )
                activity_rows = cur.fetchall()
                cur.execute(
                    """
                    SELECT
                        b.id,
                        d.name AS depot,
                        p.name AS praeparat,
                        b.charge,
                        b.verfall,
                        b.anzahl,
                        DATEDIFF(DATE(b.verfall), CURDATE()) AS tage_bis_verfall
                    FROM bewegungen b
                    JOIN depots d ON d.id = b.depot_id
                    JOIN praeparate p ON p.id = b.praeparat_id
                    WHERE b.typ = 'Zugang'
                      AND COALESCE(b.verfall, '') <> ''
                    ORDER BY DATE(b.verfall) ASC, b.id ASC
                    LIMIT %s
                    """,
                    (safe_expiry_limit,),
                )
                expiry_rows = cur.fetchall()
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
            placeholders = ",".join(["%s"] * len(depot_ids))
            sql += f" AND b.depot_id IN ({placeholders})"
            params.extend(int(item) for item in depot_ids)
        if praeparat_ids:
            placeholders = ",".join(["%s"] * len(praeparat_ids))
            sql += f" AND b.praeparat_id IN ({placeholders})"
            params.extend(int(item) for item in praeparat_ids)
        safe_query = (search_text or "").strip()
        if safe_query:
            like = f"%{safe_query}%"
            sql += """
              AND (
                    d.name LIKE %s
                 OR p.name LIKE %s
                 OR COALESCE(b.charge, '') LIKE %s
                 OR COALESCE(b.verfall, '') LIKE %s
              )
            """
            params.extend([like, like, like, like])

        safe_category = (category or "alle").strip().lower()
        safe_critical_days = max(1, int(critical_days))
        safe_warning_days = max(safe_critical_days + 1, int(warning_days))
        safe_attention_days = max(safe_warning_days + 1, int(attention_days))
        day_expr = "DATEDIFF(DATE(b.verfall), CURDATE())"
        if safe_category == "kritisch":
            sql += f" AND ({day_expr}) <= %s"
            params.append(safe_critical_days)
        elif safe_category == "warnung":
            sql += f" AND ({day_expr}) > %s AND ({day_expr}) <= %s"
            params.extend([safe_critical_days, safe_warning_days])
        elif safe_category == "achtung":
            sql += f" AND ({day_expr}) > %s AND ({day_expr}) <= %s"
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
                DATEDIFF(DATE(b.verfall), CURDATE()) AS tage_bis_verfall
            {filter_sql}
            ORDER BY DATE(b.verfall) ASC, d.name ASC, p.name ASC, b.id ASC
            LIMIT %s OFFSET %s
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params + [safe_limit, safe_offset]))
                rows = cur.fetchall()
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
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) AS c {filter_sql}", tuple(params))
                row = cur.fetchone()
        return int((row or {}).get("c", 0))

    def list_new_critical_expiry_events(
        self,
        since_iso: str | None = None,
        limit: int = 25,
        critical_days: int = 30,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 100))
        safe_critical_days = max(1, min(int(critical_days), 365))
        from datetime import datetime, timedelta

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
            with conn.cursor() as cur:
                sql = """
                    SELECT
                        b.id,
                        d.name AS depot,
                        p.name AS praeparat,
                        b.charge,
                        b.verfall,
                        b.anzahl,
                        DATE_SUB(DATE(b.verfall), INTERVAL %s DAY) AS critical_since,
                        DATEDIFF(DATE(b.verfall), CURDATE()) AS tage_bis_verfall
                    FROM bewegungen b
                    JOIN depots d ON d.id = b.depot_id
                    JOIN praeparate p ON p.id = b.praeparat_id
                    WHERE b.typ = 'Zugang'
                      AND COALESCE(b.verfall, '') <> ''
                      AND DATE(b.verfall) <= DATE_ADD(CURDATE(), INTERVAL %s DAY)
                """
                params: list[Any] = [safe_critical_days, safe_critical_days]
                if since_date is not None:
                    sql += " AND DATE_SUB(DATE(b.verfall), INTERVAL %s DAY) > %s"
                    params.extend([safe_critical_days, since_date.isoformat()])
                sql += " ORDER BY DATE(b.verfall) ASC, b.id ASC LIMIT %s"
                params.append(safe_limit)
                cur.execute(sql, tuple(params))
                rows = [dict(row) for row in cur.fetchall()]

        for row in rows:
            verfall_text = str(row.get("verfall") or "")
            try:
                verfall_day = datetime.strptime(verfall_text, "%Y-%m-%d").date()
                event_day = verfall_day - timedelta(days=safe_critical_days)
                row["event_at"] = datetime.combine(event_day, datetime.min.time(), tzinfo=UTC).isoformat()
            except ValueError:
                row["event_at"] = datetime.combine(today, datetime.min.time(), tzinfo=UTC).isoformat()
        return rows

    # ---- audit -------------------------------------------------------------
    def log_audit(
        self,
        username: str,
        action: str,
        resource_type: str,
        resource_id: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO api_audit_log (timestamp, username, action, resource_type, resource_id, details)
                    VALUES (UTC_TIMESTAMP(), %s, %s, %s, %s, %s)
                    """,
                    (
                        (username or "").strip() or "system",
                        (action or "").strip(),
                        (resource_type or "").strip(),
                        resource_id,
                        self._to_json(details),
                    ),
                )
                conn.commit()
        self._mirror_write("log_audit", username, action, resource_type, resource_id, details)

    def list_audit_logs(
        self,
        q: str = "",
        action: str = "",
        resource_type: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 300))
        safe_offset = max(0, int(offset))
        like = f"%{(q or '').strip()}%"
        action_filter = (action or "").strip()
        resource_filter = (resource_type or "").strip()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, timestamp, username, action, resource_type, resource_id, details
                    FROM api_audit_log
                    WHERE
                        (%s = '' OR action = %s) AND
                        (%s = '' OR resource_type = %s) AND
                        (
                            %s = '%%' OR
                            username LIKE %s OR
                            action LIKE %s OR
                            resource_type LIKE %s OR
                            COALESCE(details, '') LIKE %s
                        )
                    ORDER BY id DESC
                    LIMIT %s OFFSET %s
                    """,
                    (
                        action_filter,
                        action_filter,
                        resource_filter,
                        resource_filter,
                        like,
                        like,
                        like,
                        like,
                        like,
                        safe_limit,
                        safe_offset,
                    ),
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_sync_batch_result(self, batch_id: str) -> dict[str, Any] | None:
        safe_batch = (batch_id or "").strip()
        if not safe_batch:
            return None
        self._ensure_sync_batch_table()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT result_json FROM sync_push_batches WHERE batch_id = %s", (safe_batch,))
                row = cur.fetchone()
        if not row:
            return None
        raw = row.get("result_json")
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
        self._ensure_sync_batch_table()
        result_json = json.dumps(result or {}, ensure_ascii=False)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sync_push_batches (batch_id, username, received_at, result_json)
                    VALUES (%s, %s, UTC_TIMESTAMP(), %s)
                    ON DUPLICATE KEY UPDATE
                        username = VALUES(username),
                        received_at = UTC_TIMESTAMP(),
                        result_json = VALUES(result_json)
                    """,
                    (safe_batch, (username or "").strip() or "unknown", result_json),
                )
                conn.commit()

    def get_import_batch_result(self, batch_id: str) -> dict[str, Any] | None:
        safe_batch = (batch_id or "").strip()
        if not safe_batch:
            return None
        self._ensure_import_batch_table()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT result_json FROM import_batches WHERE batch_id = %s", (safe_batch,))
                row = cur.fetchone()
        if not row:
            return None
        raw = row.get("result_json")
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
        self._ensure_import_batch_table()
        result_json = json.dumps(result or {}, ensure_ascii=False)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT IGNORE INTO import_batches (batch_id, username, received_at, result_json)
                    VALUES (%s, %s, UTC_TIMESTAMP(), %s)
                    """,
                    (safe_batch, (username or "").strip() or "unknown", result_json),
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
            with conn.cursor() as cur:
                if safe_entities:
                    placeholders = ", ".join(["%s"] * len(safe_entities))
                    sql = "".join(
                        [
                            """
                            SELECT id, timestamp, username, action, resource_type, resource_id, details
                            FROM api_audit_log
                            WHERE id > %s AND resource_type IN (""",
                            placeholders,
                            """)
                            ORDER BY id ASC
                            LIMIT %s
                            """,
                        ]
                    )
                    cur.execute(sql, (safe_cursor, *safe_entities, safe_limit + 1))
                else:
                    cur.execute(
                        """
                        SELECT id, timestamp, username, action, resource_type, resource_id, details
                        FROM api_audit_log
                        WHERE id > %s
                        ORDER BY id ASC
                        LIMIT %s
                        """,
                        (safe_cursor, safe_limit + 1),
                    )
                rows = cur.fetchall()
        has_more = len(rows) > safe_limit
        sliced = rows[:safe_limit]
        changes: list[dict[str, Any]] = []
        next_cursor = safe_cursor
        for row in sliced:
            next_cursor = int(row.get("id") or safe_cursor)
            details_text = row.get("details")
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
                    "change_id": int(row.get("id") or 0),
                    "changed_at": str(row.get("timestamp") or ""),
                    "actor": str(row.get("username") or ""),
                    "operation": str(row.get("action") or ""),
                    "entity": str(row.get("resource_type") or ""),
                    "entity_id": row.get("resource_id"),
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
            with conn.cursor() as cur:
                cur.execute("SELECT COALESCE(MAX(id), 0) AS max_id FROM api_audit_log")
                row = cur.fetchone()
        return int((row or {}).get("max_id") or 0)

    def get_sync_ops_stats(self) -> dict[str, Any]:
        self._ensure_sync_batch_table()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM sync_push_batches")
                batch_count_row = cur.fetchone() or {}
                cur.execute(
                    """
                    SELECT batch_id, username, received_at
                    FROM sync_push_batches
                    ORDER BY received_at DESC
                    LIMIT 1
                    """
                )
                latest_batch_row = cur.fetchone()
                cur.execute(
                    """
                    SELECT COUNT(*) AS c
                    FROM api_audit_log
                    WHERE COALESCE(details, '') LIKE %s
                    """,
                    ('%"source": "sync_push"%',),
                )
                sync_change_row = cur.fetchone() or {}
                cur.execute(
                    """
                    SELECT COUNT(*) AS c
                    FROM sync_push_batches
                    WHERE COALESCE(result_json, '') LIKE %s
                    """,
                    ('%"deduplicated": false%',),
                )
                pending_outbox_row = cur.fetchone() or {}
        return {
            "total_push_batches": int(batch_count_row.get("c") or 0),
            "total_audit_sync_changes": int(sync_change_row.get("c") or 0),
            "latest_push_batch": dict(latest_batch_row) if latest_batch_row else None,
            "non_deduplicated_batch_rows": int(pending_outbox_row.get("c") or 0),
            "latest_audit_cursor": self.get_latest_audit_cursor(),
        }

    # ---- delegate complex endpoints for now --------------------------------
    def __getattr__(self, name: str):
        """Delegate non-ported methods to SQLite fallback."""
        return getattr(self.fallback, name)

