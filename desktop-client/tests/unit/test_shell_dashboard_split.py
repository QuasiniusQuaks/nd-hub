"""Static/smoke tests for dashboard + shell split (Issue #93)."""
from pathlib import Path

import apple_dashboard as ad
import nd_hub
from ui.shell.constants import UI, VERSION, PageIndex

ROOT = Path(__file__).resolve().parents[2]


def test_apple_dashboard_shim_exports():
    assert callable(ad.create_card_widget)
    for name in (
        "AppleDashboard",
        "StatusBadge",
        "CompletionRing",
        "TrackingCard",
        "CollapsibleSection",
    ):
        assert hasattr(ad, name)


def test_nd_hub_public_api():
    assert nd_hub.VERSION == VERSION == "0.5"
    assert nd_hub.config is not None
    assert hasattr(nd_hub, "MainWindow")
    assert PageIndex.DASHBOARD == 0
    assert UI.SIDEBAR_WIDTH == 240


def test_mainwindow_source_binds_shell_modules():
    src = (ROOT / "ui/shell/main_window.py").read_text(encoding="utf-8")
    assert "class MainWindow(QtWidgets.QMainWindow)" in src
    assert "_init_ui = init_core._init_ui" in src
    assert "switch_to_page = pages.switch_to_page" in src
    assert "show_toast = feedback.show_toast" in src
    assert "_run_sync_cycle = sync_lifecycle._run_sync_cycle" in src


def test_dashboard_source_binds_section_modules():
    src = (ROOT / "ui/dashboard/page.py").read_text(encoding="utf-8")
    assert "class AppleDashboard(ResponsiveWidget)" in src
    assert "_setup_ui = page_setup._setup_ui" in src
    assert "_create_kpi_grid = sections_header._create_kpi_grid" in src
    assert "refresh_tracking = sections_tracking.refresh_tracking" in src
    assert "_apply_layout_mode = layout._apply_layout_mode" in src


def test_source_sizes_under_targets():
    assert sum(1 for _ in open(ROOT / "apple_dashboard.py", encoding="utf-8")) < 100
    assert sum(1 for _ in open(ROOT / "nd_hub.py", encoding="utf-8")) < 200
    haupt = ROOT / "ui/pages/page_grundeinstellungen/_hauptseite.py"
    assert sum(1 for _ in open(haupt, encoding="utf-8")) < 500


def test_shell_modules_exist():
    shell = ROOT / "ui/shell"
    for name in (
        "init_core.py",
        "sidebar.py",
        "feedback.py",
        "pages.py",
        "sync_lifecycle.py",
        "session.py",
        "verfall_refresh.py",
        "logging_setup.py",
    ):
        assert (shell / name).is_file()


def test_dashboard_modules_exist():
    dash = ROOT / "ui/dashboard"
    for name in (
        "widgets.py",
        "page.py",
        "page_setup.py",
        "layout.py",
        "sections_header.py",
        "sections_tracking.py",
        "sections_activities.py",
        "sections_verfall.py",
    ):
        assert (dash / name).is_file()
