"""Schema DDL uses SQL literals, not f-strings (Issue #115)."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from backend.database import SqliteRepository

WEB_ROOT = Path(__file__).resolve().parents[2]
DESKTOP_ROOT = WEB_ROOT.parent / "desktop-client"
_FSTRING_DDL = re.compile(
    r"""execute\(\s*f['\"].*(?:ALTER TABLE|PRAGMA)""",
    re.IGNORECASE,
)
PROD_FILES = [
    WEB_ROOT / "backend" / "db" / "sqlite_schema.py",
    WEB_ROOT / "security_manager.py",
    DESKTOP_ROOT / "backend" / "database.py",
    DESKTOP_ROOT / "db_manager.py",
    DESKTOP_ROOT / "security_manager.py",
]


def test_prod_has_no_fstring_alter_or_pragma():
    missing = [p for p in PROD_FILES if not p.is_file()]
    assert missing == [], missing
    hits = []
    for path in PROD_FILES:
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            if _FSTRING_DDL.search(line):
                hits.append(f"{path.name}:{i}:{line.strip()}")
    assert hits == []


def test_sqlite_migrates_legacy_schema(tmp_path):
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
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
        CREATE TABLE email_verlauf (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datum TEXT,
            betreff TEXT,
            nachricht TEXT,
            empfaenger_depots TEXT,
            empfaenger_emails TEXT,
            anzahl_empfaenger INTEGER
        );
        """
    )
    conn.commit()
    conn.close()

    SqliteRepository(str(path))
    with sqlite3.connect(path) as migrated:
        def cols(table: str) -> set[str]:
            return {row[1] for row in migrated.execute(f"PRAGMA table_info({table})")}

        assert {"datei_pfad", "datei_name", "datei_groesse", "datei_hochgeladen_am"} <= cols("bewegungen")
        assert {"versand_status", "versand_kanal", "versand_fehler"} <= cols("email_verlauf")
        assert {"institution_id", "strasse", "hausnummer", "postleitzahl", "stadt"} <= cols("depots")
        assert {"strasse", "hausnummer", "postleitzahl", "stadt"} <= cols("institutions")
        assert {"wirkstoff", "darreichungsform", "pzn", "hersteller"} <= cols("praeparate")
