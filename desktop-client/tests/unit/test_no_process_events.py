"""No nested processEvents in backup/SMTP/sync/historie (Issue #114)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = [
    ROOT / "ui/pages/page_historie.py",
    ROOT / "ui/pages/page_grundeinstellungen/backup_page.py",
    ROOT / "ui/pages/page_grundeinstellungen/email_smtp_tab.py",
    ROOT / "ui/pages/page_grundeinstellungen/sync_tab.py",
    ROOT / "ui/shell/feedback.py",
]


def test_no_process_events_in_backup_smtp_sync_historie():
    hits = []
    for path in FORBIDDEN:
        text = path.read_text(encoding="utf-8")
        if ".processEvents(" in text:
            hits.append(str(path))
    assert hits == []
