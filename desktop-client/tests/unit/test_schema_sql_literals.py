"""Desktop schema DDL uses SQL literals (Issue #115)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.database import SqliteRepository
from db_manager import Database


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def test_desktop_backend_migrates_bewegung_attachments(tmp_path):
    path = tmp_path / "legacy-backend.db"
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE bewegungen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            depot_id INTEGER,
            praeparat_id INTEGER,
            charge TEXT,
            verfall TEXT,
            eingang_datum TEXT,
            ausgang_datum TEXT,
            empfaenger TEXT,
            anzahl INTEGER,
            typ TEXT
        )
        """
    )
    conn.commit()
    conn.close()

    SqliteRepository(str(path))
    with sqlite3.connect(path) as migrated:
        assert {"datei_pfad", "datei_name", "datei_groesse", "datei_hochgeladen_am"} <= _cols(
            migrated, "bewegungen"
        )


def test_desktop_db_migrates_legacy_columns(temp_db_path):
    conn = sqlite3.connect(temp_db_path)
    conn.executescript(
        """
        CREATE TABLE depots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            adresse TEXT,
            telefon TEXT,
            email TEXT
        );
        CREATE TABLE institutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            adresse TEXT,
            latitude REAL,
            longitude REAL
        );
        CREATE TABLE praeparate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT
        );
        CREATE TABLE bewegungen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            depot_id INTEGER,
            praeparat_id INTEGER,
            charge TEXT,
            verfall TEXT,
            eingang_datum TEXT,
            ausgang_datum TEXT,
            empfaenger TEXT,
            anzahl INTEGER,
            typ TEXT
        );
        """
    )
    conn.commit()
    conn.close()

    db = Database(temp_db_path)
    try:
        assert {"institution_id", "strasse", "latitude", "longitude"} <= _cols(db.conn, "depots")
        assert {"strasse", "hausnummer", "postleitzahl", "stadt"} <= _cols(db.conn, "institutions")
        assert {"wirkstoff", "pzn", "hersteller"} <= _cols(db.conn, "praeparate")
        assert "datei_pfad" in _cols(db.conn, "bewegungen")
    finally:
        db.conn.close()
        Path(temp_db_path).unlink(missing_ok=True)


def test_query_only_on_off_literals(temp_db_path):
    db = Database(temp_db_path)
    try:
        db.set_query_only(True)
        try:
            db.cur.execute("CREATE TABLE t_ro_probe (id INTEGER)")
            raise AssertionError("query_only=ON must reject writes")
        except sqlite3.OperationalError:
            pass
        db.set_query_only(False)
        db.cur.execute("CREATE TABLE t_rw_probe (id INTEGER)")
        db.conn.commit()
        names = {row[0] for row in db.cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "t_rw_probe" in names
    finally:
        db.conn.close()
        Path(temp_db_path).unlink(missing_ok=True)
