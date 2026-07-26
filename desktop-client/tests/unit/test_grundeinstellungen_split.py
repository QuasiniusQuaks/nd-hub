"""Smoke tests for Grundeinstellungen package split (Issue #93)."""
from ui.pages.page_grundeinstellungen import backup_page, email_smtp_tab, security_tab, sync_tab
from ui.pages.page_grundeinstellungen.sync_tab import _require_http_scheme


def test_extracted_modules_expose_functions():
    assert callable(email_smtp_tab.create_email_smtp_tab)
    assert callable(backup_page.create_backup_tab)
    assert callable(backup_page.check_auto_backup)
    assert callable(sync_tab.create_sync_tab)
    assert callable(sync_tab.refresh_sync_status)
    assert callable(security_tab.create_security_tab)


def test_require_http_scheme_allows_http_https():
    assert _require_http_scheme("https://example.org/path") == "https://example.org/path"
    assert _require_http_scheme("http://localhost:8000") == "http://localhost:8000"


def test_require_http_scheme_rejects_other():
    try:
        _require_http_scheme("file:///tmp/x")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_hauptseite_source_binds_tab_modules():
    """Static check: orchestrator wires extracted modules (avoids Qt stub MRO)."""
    from pathlib import Path

    src = Path(__file__).resolve().parents[2] / "ui/pages/page_grundeinstellungen/_hauptseite.py"
    text = src.read_text(encoding="utf-8")
    assert "from . import backup_page, email_smtp_tab, security_tab, sync_tab" in text
    assert "create_email_smtp_tab = email_smtp_tab.create_email_smtp_tab" in text
    assert "create_backup_tab = backup_page.create_backup_tab" in text
    assert "create_sync_tab = sync_tab.create_sync_tab" in text
    assert "class GrundeinstellungenPage(QtWidgets.QWidget)" in text
