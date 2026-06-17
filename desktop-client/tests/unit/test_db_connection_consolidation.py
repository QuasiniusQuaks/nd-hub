"""Tests für Issue #18: Geteilte Database-Connection in VerfallManager + SecurityManager.

Szenario:
- VerfallManager(database=db) und SecurityManager(database=db) teilen
  Connection mit der Database-Instanz
- close() schließt NICHT die geliehene Connection
- Legacy-Aufruf (db_path=...) funktioniert weiterhin mit eigener Connection
- Bei geteilter Connection: Mutations in der Database sind in den Managern
  sichtbar (gleiche Connection, gleicher WAL-Stream)
"""
import os
import sqlite3
import sys
import tempfile
from typing import Iterator

import pytest

# PySide6-Stub für reine DB-Tests (Desktop-Client-Module importieren Qt top-level)
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _pyside6_stub  # noqa: F401  (side-effect: stub installiert)


@pytest.fixture
def temp_db_path() -> Iterator[str]:
    """Erstellt eine temporäre SQLite-Datei."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        yield path
    finally:
        for ext in ("", "-wal", "-shm", "-journal"):
            try:
                os.remove(path + ext)
            except OSError:
                pass


def test_legacy_verfallmanager_creates_own_connection(temp_db_path: str) -> None:
    """Legacy-Aufruf mit db_path erstellt eigene Connection."""
    from verfallmanager import VerfallManager
    vm = VerfallManager(temp_db_path)
    try:
        assert vm._owns_connection is True
        assert vm.db_path == temp_db_path
        assert vm.conn is not None
        assert vm.cur is not None
    finally:
        vm.close()


def test_legacy_securitymanager_creates_own_connection(temp_db_path: str) -> None:
    """Legacy-Aufruf mit db_path erstellt eigene Connection."""
    from security_manager import SecurityManager
    sm = SecurityManager(temp_db_path)
    try:
        assert sm._owns_connection is True
        assert sm.db_path == temp_db_path
    finally:
        sm.close()


def test_verfallmanager_raises_with_empty_db_path_and_no_database() -> None:
    """Wenn weder database noch echter db_path gegeben, TypeError.

    Mit db_path="" würde sqlite3.connect eine In-Memory-DB öffnen —
    das ist ein Bug, deshalb der explizite TypeError.
    """
    from verfallmanager import VerfallManager
    with pytest.raises(TypeError, match="db_path.*database"):
        VerfallManager(db_path="")


def test_securitymanager_raises_with_empty_db_path_and_no_database() -> None:
    from security_manager import SecurityManager
    with pytest.raises(TypeError, match="db_path.*database"):
        SecurityManager(db_path="")


def test_legacy_close_closes_own_connection(temp_db_path: str) -> None:
    """Legacy: close() schließt die eigene Connection."""
    from verfallmanager import VerfallManager
    vm = VerfallManager(temp_db_path)
    own_conn = vm.conn
    vm.close()
    # Connection sollte geschlossen sein — neue Query muss fehlschlagen
    with pytest.raises(sqlite3.ProgrammingError):
        own_conn.execute("SELECT 1")


def test_shared_close_does_not_close_borrowed_connection(temp_db_path: str) -> None:
    """Geteilt: close() schließt die geliehene Connection NICHT.

    Issue #18: Wenn die Connection von Database stammt, gehört sie
    Database — VerfallManager darf sie nicht schließen.
    """
    from db_manager import Database
    from verfallmanager import VerfallManager
    db = Database(temp_db_path)
    try:
        vm = VerfallManager(database=db)
        assert vm._owns_connection is False
        # Gleiche Connection-Objekte
        assert vm.conn is db.conn
        assert vm.cur is db.cur
        # close() auf VM: darf Database-Connection nicht killen
        vm.close()
        # Database-Connection muss noch funktionieren
        result = db.cur.execute("SELECT 1").fetchone()
        assert result[0] == 1
    finally:
        db.conn.close()


def test_shared_securitymanager_does_not_close_borrowed_connection(temp_db_path: str) -> None:
    """Symmetrisches Verhalten für SecurityManager."""
    from db_manager import Database
    from security_manager import SecurityManager
    db = Database(temp_db_path)
    try:
        sm = SecurityManager(database=db)
        assert sm._owns_connection is False
        assert sm.conn is db.conn
        sm.close()
        result = db.cur.execute("SELECT 1").fetchone()
        assert result[0] == 1
    finally:
        db.conn.close()


def test_shared_connection_writes_visible_in_database(temp_db_path: str) -> None:
    """Mutationen in VerfallManager (geteilt) sind in Database sichtbar.

    Issue #18: Das ist der Hauptvorteil — keine Lock-Contention, weil
    WAL-Schreibvorgänge auf der gleichen Connection serialisiert werden.
    """
    from db_manager import Database
    from verfallmanager import VerfallManager
    db = Database(temp_db_path)
    try:
        vm = VerfallManager(database=db)
        # Mutation via VM
        vm.cur.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, val TEXT)")
        vm.conn.commit()
        # Sichtbar in Database
        result = db.cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"
        ).fetchone()
        assert result is not None
        assert result[0] == "test_table"
    finally:
        db.conn.close()
