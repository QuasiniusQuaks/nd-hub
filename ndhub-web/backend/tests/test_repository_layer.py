"""Tests for repository ABC + shared SQL dialect (Issue #70)."""

from __future__ import annotations

import os
import tempfile

from backend import sql_dialect as sql
from backend.database import SqliteRepository
from backend.mariadb_repository import MariaDbRepository
from backend.repository_abc import AbstractRepository
from backend.repository_factory import create_repository


def test_dialect_placeholders():
    assert sql.SQLITE.ph == "?"
    assert sql.MYSQL.ph == "%s"
    assert sql.SQLITE.format("id = {ph}") == "id = ?"
    assert sql.MYSQL.format("id = {ph}") == "id = %s"
    q = sql.SQLITE.format(sql.SQL_GET_DEPOT)
    assert "depots.id" in q and "?" in q and "%s" not in q
    q2 = sql.MYSQL.format(sql.SQL_GET_DEPOT)
    assert "%s" in q2 and "?" not in q2


def test_repository_inheritance():
    assert issubclass(SqliteRepository, AbstractRepository)
    assert issubclass(MariaDbRepository, AbstractRepository)


def test_factory_sqlite_and_shared_reads():
    td = tempfile.mkdtemp()
    path = os.path.join(td, "repo.db")
    repo = create_repository(db_path=path, db_engine="sqlite")
    assert isinstance(repo, AbstractRepository)
    assert isinstance(repo, SqliteRepository)

    depot_id = repo.create_depot("Depot-ABC", adresse="Str. 1")
    got = repo.get_depot(depot_id)
    assert got is not None
    assert got["name"] == "Depot-ABC"
    assert repo.get_depot_name(depot_id) == "Depot-ABC"

    prae_id = repo.create_praeparat("Praep-1")
    prae = repo.get_praeparat(prae_id)
    assert prae is not None
    assert prae["name"] == "Praep-1"
    names = {row["name"] for row in repo.list_praeparate(q="Praep")}
    assert "Praep-1" in names
