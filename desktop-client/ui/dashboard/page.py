"""AppleDashboard page orchestrator (Issue #93)."""
from __future__ import annotations

from PySide6.QtCore import Signal
from responsive_widgets import ResponsiveWidget

from . import (
    layout,
    page_setup,
    sections_activities,
    sections_header,
    sections_tracking,
    sections_verfall,
)


class AppleDashboard(ResponsiveWidget):
    """Apple-Style Dashboard mit responsivem Layout."""

    requestedPage = Signal(int)

    _apply_layout_mode = layout._apply_layout_mode
    refresh_theme = layout.refresh_theme
    _update_quick_actions_style = layout._update_quick_actions_style
    _create_header = sections_header._create_header
    _create_cards = sections_header._create_cards
    _create_overview_content = sections_header._create_overview_content
    _create_kpi_grid = sections_header._create_kpi_grid
    _create_kpi_card = sections_header._create_kpi_card
    _create_quick_actions = sections_header._create_quick_actions
    _create_verfall_section = sections_verfall._create_verfall_section
    show_verfall_details = sections_verfall.show_verfall_details
    _create_activities_section = sections_activities._create_activities_section
    refresh_activities = sections_activities.refresh_activities
    _create_tracking_section = sections_tracking._create_tracking_section
    _bulk_update_tracking = sections_tracking._bulk_update_tracking
    refresh_tracking = sections_tracking.refresh_tracking
    _save_tracking_change = sections_tracking._save_tracking_change
    _update_overall_progress = sections_tracking._update_overall_progress
    __init__ = page_setup.__init__
    _setup_ui = page_setup._setup_ui
