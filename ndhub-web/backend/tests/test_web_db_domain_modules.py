"""Web DB domain mixins stay under the LOC gate (Issue #110)."""

from __future__ import annotations

from pathlib import Path

from backend.database import SqliteRepository
from backend.mariadb_repository import MariaDbRepository
from backend.repository_abc import AbstractRepository

DB = Path(__file__).resolve().parents[1] / "db"


def test_domain_modules_under_500_loc():
    files = list(DB.glob("*.py"))
    assert files
    for path in files:
        loc = len(path.read_text(encoding="utf-8").splitlines())
        assert loc <= 500, f"{path.name} is {loc} LOC"


def test_facades_under_500_loc():
    backend = Path(__file__).resolve().parents[1]
    for name in ("database.py", "mariadb_repository.py"):
        loc = len((backend / name).read_text(encoding="utf-8").splitlines())
        assert loc <= 500, f"{name} is {loc} LOC"


def test_sqlite_exposes_abstract_repository_methods():
    names = [n for n in dir(AbstractRepository) if not n.startswith("_")]
    missing = [n for n in names if not hasattr(SqliteRepository, n)]
    assert missing == []
    assert issubclass(SqliteRepository, AbstractRepository)
    assert issubclass(MariaDbRepository, AbstractRepository)
