"""Hotspot exceptions are typed and logged (Issue #116)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOTSPOTS = [
    ROOT / "ui" / "pages" / "page_grundeinstellungen" / "backup_page.py",
    ROOT / "security_manager.py",
    ROOT.parent / "ndhub-web" / "security_manager.py",
    ROOT.parent / "shared" / "routers" / "admin_backup.py",
    ROOT / "ui" / "pages" / "analytics" / "_insights" / "pdf_report.py",
]
_SILENT_PASS = re.compile(r"except Exception(?:\s+as\s+\w+)?:\s*\n\s+pass\b", re.MULTILINE)


def test_hotspots_have_no_silent_exception_pass():
    missing = [p for p in HOTSPOTS if not p.is_file()]
    assert missing == []
    hits = []
    for path in HOTSPOTS:
        text = path.read_text(encoding="utf-8")
        if _SILENT_PASS.search(text):
            hits.append(path.name)
    assert hits == []


def test_backup_page_logs_instead_of_print():
    text = (ROOT / "ui" / "pages" / "page_grundeinstellungen" / "backup_page.py").read_text(
        encoding="utf-8"
    )
    assert "print(" not in text
    assert "logger.exception" in text
    assert "except Exception" not in text


def test_admin_backup_router_has_no_bare_exception():
    text = (ROOT.parent / "shared" / "routers" / "admin_backup.py").read_text(encoding="utf-8")
    assert "except Exception" not in text


def test_verify_backup_logs_invalid_file(tmp_path, caplog):
    from ui.pages.page_grundeinstellungen.backup_page import _verify_backup

    junk = tmp_path / "not-a-db.txt"
    junk.write_text("nope", encoding="utf-8")
    assert _verify_backup(object(), str(junk)) is False
    assert any("Verifikation" in rec.getMessage() for rec in caplog.records)
