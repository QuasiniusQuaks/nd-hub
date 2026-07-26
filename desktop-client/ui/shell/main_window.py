"""MainWindow orchestrator (Issue #93)."""
from __future__ import annotations

from PySide6 import QtWidgets

from . import feedback, init_core, pages, session, sidebar, sync_lifecycle, verfall_refresh


class MainWindow(QtWidgets.QMainWindow):
    """Hauptfenster der ND-Hub-Verwaltung."""

    __init__ = init_core.__init__
    _profile_startup = init_core._profile_startup
    _init_security = init_core._init_security
    _handle_successful_login = init_core._handle_successful_login
    _maybe_open_setup_wizard = init_core._maybe_open_setup_wizard
    open_setup_wizard_dialog = init_core.open_setup_wizard_dialog
    _init_database = init_core._init_database
    _init_data_access_layer = init_core._init_data_access_layer
    _init_sync_service = init_core._init_sync_service
    _init_multi_user_mode = init_core._init_multi_user_mode
    _init_managers = init_core._init_managers
    _init_window = init_core._init_window
    _set_window_icon = init_core._set_window_icon
    _init_ui = init_core._init_ui
    _create_sidebar = sidebar._create_sidebar
    _update_sidebar_width = sidebar._update_sidebar_width
    _create_logo_container = sidebar._create_logo_container
    _create_logo_label = sidebar._create_logo_label
    _add_navigation_buttons = sidebar._add_navigation_buttons
    _add_user_section = sidebar._add_user_section
    _apply_chrome_overlay_styles = sidebar._apply_chrome_overlay_styles
    toggle_theme = sidebar.toggle_theme
    _create_user_info_widget = sidebar._create_user_info_widget
    _refresh_user_sidebar_state = sidebar._refresh_user_sidebar_state
    _apply_write_mode_to_page = sidebar._apply_write_mode_to_page
    _update_user_avatar_display = sidebar._update_user_avatar_display
    _create_styled_button = sidebar._create_styled_button
    _create_logout_button = sidebar._create_logout_button
    create_sidebar_button = sidebar.create_sidebar_button
    on_sidebar_click = sidebar.on_sidebar_click
    set_active_button = sidebar.set_active_button
    _setup_feedback_layers = feedback._setup_feedback_layers
    _update_feedback_layer_geometry = feedback._update_feedback_layer_geometry
    _show_page_busy = feedback._show_page_busy
    _hide_page_busy = feedback._hide_page_busy
    _begin_busy_operation = feedback._begin_busy_operation
    _end_busy_operation = feedback._end_busy_operation
    show_toast = feedback.show_toast
    _remove_toast = feedback._remove_toast
    _reflow_toasts = feedback._reflow_toasts
    _init_pages = pages._init_pages
    _create_page_instance = pages._create_page_instance
    _ensure_page_loaded = pages._ensure_page_loaded
    switch_to_page = pages.switch_to_page
    _install_page_enhancements = pages._install_page_enhancements
    _mark_page_dirty = pages._mark_page_dirty
    _clear_page_dirty = pages._clear_page_dirty
    _page_has_unsaved_changes = pages._page_has_unsaved_changes
    _confirm_discard_unsaved_changes = pages._confirm_discard_unsaved_changes
    _init_timers = sync_lifecycle._init_timers
    _refresh_sync_scheduler = sync_lifecycle._refresh_sync_scheduler
    _heartbeat_write_lease = sync_lifecycle._heartbeat_write_lease
    _run_sync_cycle = sync_lifecycle._run_sync_cycle
    _on_sync_cycle_finished = sync_lifecycle._on_sync_cycle_finished
    _on_sync_cycle_failed = sync_lifecycle._on_sync_cycle_failed
    _on_sync_cycle_skipped = sync_lifecycle._on_sync_cycle_skipped
    _setup_integrated_login = session._setup_integrated_login
    _perform_integrated_login = session._perform_integrated_login
    _show_confirmation_overlay = session._show_confirmation_overlay
    _hide_confirmation_overlay = session._hide_confirmation_overlay
    _show_logout_choice_overlay = session._show_logout_choice_overlay
    change_user_password = session.change_user_password
    change_user_avatar = session.change_user_avatar
    remove_user_avatar = session.remove_user_avatar
    open_user_management = session.open_user_management
    force_logout = session.force_logout
    _execute_logout = session._execute_logout
    _execute_user_switch = session._execute_user_switch
    logout = session.logout
    closeEvent = session.closeEvent
    _confirm_close = session._confirm_close
    resizeEvent = session.resizeEvent
    keyPressEvent = session.keyPressEvent
    _get_verfall_data_hash = verfall_refresh._get_verfall_data_hash
    refresh_verfall_widgets = verfall_refresh.refresh_verfall_widgets
