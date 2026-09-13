"""SQLite data access for backend endpoints."""

from __future__ import annotations

import sqlite3

from backend import sql_dialect as sql
from backend.repository_abc import AbstractRepository

ALLOWED_MOVEMENT_TYPES = {"Zugang", "Abgang", "Vernichtung"}

from backend.db.sqlite_analytics import SqliteAnalyticsMixin
from backend.db.sqlite_bewegungen import SqliteBewegungenMixin
from backend.db.sqlite_depots import SqliteDepotsMixin
from backend.db.sqlite_email import SqliteEmailMixin
from backend.db.sqlite_institutions import SqliteInstitutionsMixin
from backend.db.sqlite_kontakte import SqliteKontakteMixin
from backend.db.sqlite_praeparate import SqlitePraeparateMixin
from backend.db.sqlite_schema import SqliteSchemaMixin
from backend.db.sqlite_sync import SqliteSyncMixin
from backend.db.sqlite_verfall import SqliteVerfallMixin


class SqliteRepository(
    SqliteSchemaMixin,
    SqliteDepotsMixin,
    SqlitePraeparateMixin,
    SqliteInstitutionsMixin,
    SqliteKontakteMixin,
    SqliteEmailMixin,
    SqliteBewegungenMixin,
    SqliteAnalyticsMixin,
    SqliteVerfallMixin,
    SqliteSyncMixin,
    AbstractRepository,
):
    """Facade composed from domain mixins (Issue #110)."""

    _dialect = sql.SQLITE

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn
