"""Repository factory for web backend (Issue #70)."""

from __future__ import annotations

from backend.config import (
    resolve_db_engine,
    resolve_dual_write_sqlite,
    resolve_mariadb_settings,
    resolve_runtime_paths,
)
from backend.database import SqliteRepository
from backend.mariadb_repository import MariaDbRepository
from backend.repository_abc import AbstractRepository


def create_repository(
    *,
    db_path: str | None = None,
    db_engine: str | None = None,
) -> AbstractRepository:
    """Create SQLite or MariaDB repository from engine setting / ENV."""
    engine = (db_engine or resolve_db_engine(default="sqlite")).strip().lower()
    runtime = resolve_runtime_paths(db_path=db_path)
    database_path = str(runtime.database_path)
    sqlite_fallback = SqliteRepository(database_path)
    if engine == "mariadb":
        return MariaDbRepository(
            settings=resolve_mariadb_settings(),
            fallback=sqlite_fallback,
            dual_write_sqlite=resolve_dual_write_sqlite(default=True),
        )
    return sqlite_fallback
