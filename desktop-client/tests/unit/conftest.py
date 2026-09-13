"""Pytest-Konfiguration für Desktop-Client Unit-Tests.

Auto-installiert den PySide6-Stub (damit Tests ohne libEGL/Qt laufen)
und stellt gemeinsame Fixtures bereit.

Issue #69 — conftest.py fehlte, Stub musste manuell importiert werden.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

# PySide6-Stub auto-installieren — MUSS vor jedem db_manager/security_manager Import erfolgen
sys.path.insert(0, str(Path(__file__).parent))
import _pyside6_stub  # noqa: F401  (side-effect: stub installiert)


def pytest_configure(config) -> None:
    # Issue #141: first admin is fail-closed without env. Unit tests that
    # construct SecurityManager/create_app inherit this default; tests that
    # assert the fail-closed path still delenv.
    os.environ.setdefault(
        "ND_HUB_INITIAL_ADMIN_PASSWORD",
        "TestAdmin!conftest-not-for-prod",
    )


@pytest.fixture
def temp_db_path() -> Iterator[str]:
    """Erstellt eine temporäre SQLite-Datei für Test-DBs.

    Cleanup inklusive WAL/SHM/Journal-Dateien.
    """
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
