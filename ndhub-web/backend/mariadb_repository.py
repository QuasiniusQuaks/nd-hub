"""MariaDB repository with SQLite fallback for non-ported queries.

This module enables incremental runtime cutover:
- core CRUD/read flows run against MariaDB
- complex analytics/reporting can still delegate to SQLite fallback
- write operations are dual-written to fallback to avoid regressions
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from backend import sql_dialect as sql
from backend.config import MariaDbSettings
from backend.database import SqliteRepository
from backend.repository_abc import AbstractRepository

ALLOWED_MOVEMENT_TYPES = {"Zugang", "Abgang", "Vernichtung"}
logger = logging.getLogger(__name__)

from backend.db.mariadb_analytics import MariadbAnalyticsMixin
from backend.db.mariadb_bewegungen import MariadbBewegungenMixin
from backend.db.mariadb_depots import MariadbDepotsMixin
from backend.db.mariadb_email import MariadbEmailMixin
from backend.db.mariadb_institutions import MariadbInstitutionsMixin
from backend.db.mariadb_kontakte import MariadbKontakteMixin
from backend.db.mariadb_praeparate import MariadbPraeparateMixin
from backend.db.mariadb_sync import MariadbSyncMixin
from backend.db.mariadb_verfall import MariadbVerfallMixin


class MariaDbRepository(
    MariadbDepotsMixin,
    MariadbPraeparateMixin,
    MariadbInstitutionsMixin,
    MariadbKontakteMixin,
    MariadbEmailMixin,
    MariadbBewegungenMixin,
    MariadbAnalyticsMixin,
    MariadbVerfallMixin,
    MariadbSyncMixin,
    AbstractRepository,
):
    """Facade composed from domain mixins (Issue #110)."""

    _dialect = sql.MYSQL

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

    def __getattr__(self, name: str):
        """Delegate non-ported methods to SQLite fallback."""
        return getattr(self.fallback, name)
