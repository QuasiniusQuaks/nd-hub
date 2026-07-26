"""Grundeinstellungen - Depots, Präparate, Zuordnungen, Ansprechpartner, Backup."""
import logging

from db_manager import Database
from icon_manager import IconManager
from PySide6 import QtGui, QtWidgets
from PySide6.QtCore import Qt

from . import backup_page, email_smtp_tab, security_tab, sync_tab
from .audit_logs_tab import AuditLogsPage
from .depots_tab import DepotsPage
from .kontakte_tab import KontaktePage
from .praeparate_tab import PraeparatePage
from .user_management_tab import UserManagementPage
from .zuordnungen_tab import AssignmentPage

logger = logging.getLogger("ND-Hub")


class GrundeinstellungenPage(QtWidgets.QWidget):
    """Orchestrator: Tabs aus Submodulen gebunden (Issue #93, Qt-Stub-safe)."""

    create_email_smtp_tab = email_smtp_tab.create_email_smtp_tab
    _on_smtp_ssl_toggled = email_smtp_tab._on_smtp_ssl_toggled
    _on_smtp_tls_toggled = email_smtp_tab._on_smtp_tls_toggled
    _collect_smtp_form_dict = email_smtp_tab._collect_smtp_form_dict
    load_smtp_email_settings = email_smtp_tab.load_smtp_email_settings
    save_smtp_email_settings = email_smtp_tab.save_smtp_email_settings
    test_smtp_email_settings = email_smtp_tab.test_smtp_email_settings
    create_backup_tab = backup_page.create_backup_tab
    reset_test_data = backup_page.reset_test_data
    get_default_backup_path = backup_page.get_default_backup_path
    browse_backup_folder = backup_page.browse_backup_folder
    create_backup = backup_page.create_backup
    browse_restore_file = backup_page.browse_restore_file
    restore_backup = backup_page.restore_backup
    _busy_sleep = backup_page._busy_sleep
    _verify_backup = backup_page._verify_backup
    _rotate_backups = backup_page._rotate_backups
    check_auto_backup = backup_page.check_auto_backup
    load_auto_backup_setting = backup_page.load_auto_backup_setting
    save_auto_backup_setting_from_bool = backup_page.save_auto_backup_setting_from_bool
    create_sync_tab = sync_tab.create_sync_tab
    _update_sync_tab_responsiveness = sync_tab._update_sync_tab_responsiveness
    _get_host_config = sync_tab._get_host_config
    load_sync_configuration = sync_tab.load_sync_configuration
    save_sync_configuration = sync_tab.save_sync_configuration
    test_sync_connection = sync_tab.test_sync_connection
    _build_api_client_from_inputs = sync_tab._build_api_client_from_inputs
    refresh_sync_tokens = sync_tab.refresh_sync_tokens
    create_sync_token = sync_tab.create_sync_token
    revoke_selected_sync_token = sync_tab.revoke_selected_sync_token
    refresh_sync_status = sync_tab.refresh_sync_status
    _refresh_remote_sync_stats = sync_tab._refresh_remote_sync_stats
    _update_sync_schedule_hint = sync_tab._update_sync_schedule_hint
    _set_sync_state_badge = sync_tab._set_sync_state_badge
    retry_sync_conflicts = sync_tab.retry_sync_conflicts
    trigger_sync_now = sync_tab.trigger_sync_now
    create_security_tab = security_tab.create_security_tab
    update_password_strength = security_tab.update_password_strength
    toggle_password_visibility = security_tab.toggle_password_visibility
    change_password = security_tab.change_password
    load_password_hash = security_tab.load_password_hash
    save_password_hash = security_tab.save_password_hash

    def __init__(self, db: Database, security=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.security = security

        # WICHTIG: Einstellungen-Tabelle SOFORT erstellen
        self._ensure_einstellungen_table()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        header_layout = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Grundeinstellungen")
        title.setProperty("class", "page-title")

        header_layout.addWidget(title)
        header_layout.addStretch()
        if self.security and getattr(self.security, "is_admin", lambda: False)():
            btn_wizard = QtWidgets.QPushButton("Einrichtungswizard")
            btn_wizard.setObjectName("btn_secondary")
            btn_wizard.setMinimumHeight(36)

            def _open_wizard() -> None:
                host = self.window()
                if hasattr(host, "open_setup_wizard_dialog"):
                    host.open_setup_wizard_dialog()
                else:
                    from ui.dialogs.setup_wizard_dialog import SetupWizardDialog

                    SetupWizardDialog(host, self.db).exec()

            btn_wizard.clicked.connect(_open_wizard)
            header_layout.addWidget(btn_wizard)

        layout.addLayout(header_layout)

# ===== DIREKT DIE TABS ANZEIGEN (kein Lock mehr) =====

        # Tab-Widget mit den Bereichen
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setUsesScrollButtons(True)
        self.tabs.setElideMode(Qt.ElideRight)
        self.tabs.tabBar().setExpanding(False)

        # Tab 1: Depots
        self.depots_page = DepotsPage(self.db, security=self.security)
        self.tabs.addTab(self.depots_page, "Depots")
        self.tabs.setTabIcon(0, IconManager.get_icon("map"))

        # Tab 2: Präparate
        self.praeparate_page = PraeparatePage(self.db)
        self.tabs.addTab(self.praeparate_page, "Präparate")
        self.tabs.setTabIcon(1, IconManager.get_icon("pill"))

        # Tab 3: Zuordnungen
        self.assign_page = AssignmentPage(self.db)
        self.tabs.addTab(self.assign_page, "Zuordnungen")
        self.tabs.setTabIcon(2, IconManager.get_icon("activity"))

        # Tab 4: Ansprechpartner
        self.kontakte_page = KontaktePage(self.db)
        self.tabs.addTab(self.kontakte_page, "Ansprechpartner")
        self.tabs.setTabIcon(3, IconManager.get_icon("user"))

        # Tab 5: SMTP / Direktversand
        self.email_smtp_tab = self.create_email_smtp_tab()
        self.tabs.addTab(self.email_smtp_tab, "E-Mail-Versand")
        self.tabs.setTabIcon(4, IconManager.get_icon("mail"))

        # Tab 6: Backup & Wiederherstellung
        self.backup_page = self.create_backup_tab()
        self.tabs.addTab(self.backup_page, "Backup")
        self.tabs.setTabIcon(5, IconManager.get_icon("refresh_ccw"))

        # Tab 7: Sync-Monitoring
        self.sync_page = self.create_sync_tab()
        self.tabs.addTab(self.sync_page, "Sync")
        self.tabs.setTabIcon(6, IconManager.get_icon("activity"))

        # Tab 7: Benutzerverwaltung (nur Admin)
        if self.security and getattr(self.security, "is_admin", lambda: False)():
            self.user_management_page = UserManagementPage(self.security)
            self.tabs.addTab(self.user_management_page, "Benutzer")
            self.tabs.setTabIcon(self.tabs.count() - 1, IconManager.get_icon("user"))
            self.audit_logs_page = AuditLogsPage(lambda: getattr(self.window(), "config", None))
            self.tabs.addTab(self.audit_logs_page, "Audit")
            self.tabs.setTabIcon(self.tabs.count() - 1, IconManager.get_icon("clock"))

        # Tab 6: Sicherheit (optional, wenn du Verschlüsselung später willst)
        # self.security_page = self.create_security_tab()
        # self.tabs.addTab(self.security_page, "🔐 Sicherheit")

        self._tab_guard_active = False
        self._last_tab_index = self.tabs.currentIndex()
        self.tabs.currentChanged.connect(self._handle_tab_change_guard)

        layout.addWidget(self.tabs)

        # Prüfe Auto-Backup beim Laden
        self.check_auto_backup()
        self.refresh_sync_status()

    def refresh_theme(self) -> None:
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if w is not None and hasattr(w, "refresh_theme"):
                w.refresh_theme()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._update_sync_tab_responsiveness()

    def _handle_tab_change_guard(self, new_index: int):
        """Fragt bei ungespeicherten Änderungen vor internem Tab-Wechsel."""
        if self._tab_guard_active:
            return
        host = self.window()
        if hasattr(host, "_confirm_discard_unsaved_changes"):
            if not host._confirm_discard_unsaved_changes(self):
                self._tab_guard_active = True
                self.tabs.setCurrentIndex(self._last_tab_index)
                self._tab_guard_active = False
                return
        self._last_tab_index = new_index
        current_widget = self.tabs.widget(new_index)
        if current_widget is getattr(self, "sync_page", None):
            self.refresh_sync_status()

    def _ensure_einstellungen_table(self):
        """Stellt sicher, dass die Einstellungen-Tabelle existiert"""
        try:
            self.db.cur.execute("""
                CREATE TABLE IF NOT EXISTS einstellungen (
                    schluessel TEXT PRIMARY KEY,
                    wert TEXT
                )
            """)
            self.db.conn.commit()
        except Exception as e:
            print(f"Fehler beim Erstellen der Einstellungen-Tabelle: {e}")

    def _is_read_only_mode(self) -> bool:
        return bool(getattr(self.db, "is_read_only_mode", lambda: False)())

    def _toast(self, message: str, level: str = "info") -> None:
        host = self.window()
        if hasattr(host, "show_toast"):
            host.show_toast(message, level)

