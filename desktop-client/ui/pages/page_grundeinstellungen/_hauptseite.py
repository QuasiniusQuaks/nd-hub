"""Grundeinstellungen - Depots, Präparate, Zuordnungen, Ansprechpartner, Backup."""
import logging
import os
import shutil
import sqlite3
import sys
import time
from datetime import datetime
from urllib import error, request
from urllib.parse import urlparse

from apple_theme import AppleTheme
from core.data_access_layer import BackendApiClient, BackendSyncConfig, OperatingMode
from db_manager import DB, Database
from icon_manager import IconManager
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from security_manager import SecurityManager

from ui.utils import create_card_widget

# Sub-Module (extrahierte Klassen)
from .depots_tab import DepotsPage
from .kontakte_tab import KontaktePage
from .praeparate_tab import PraeparatePage


def _require_http_scheme(url: str) -> str:
    """Validiert dass die URL nur http/https verwendet (SSRF-Schutz)."""
    scheme = urlparse(url).scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError(f"URL scheme not allowed: {url}")
    return url


logger = logging.getLogger("ND-Hub")
from .audit_logs_tab import AuditLogsPage
from .user_management_tab import UserManagementPage
from .zuordnungen_tab import AssignmentPage


class GrundeinstellungenPage(QtWidgets.QWidget):
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

    def create_email_smtp_tab(self):
        """Tab: SMTP für direkten E-Mail-Versand aus der E-Mail-Seite."""
        tab = QtWidgets.QWidget()
        outer_layout = QtWidgets.QVBoxLayout(tab)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        outer_layout.addWidget(scroll)

        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        scroll.setWidget(content)

        c = AppleTheme.current_colors()
        card = create_card_widget()
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setSpacing(10)

        title = QtWidgets.QLabel("SMTP (Direktversand)")
        title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {c['label']};")
        card_layout.addWidget(title)

        info = QtWidgets.QLabel(
            "Hier konfigurieren Sie den Server für den direkten Versand per SMTP "
            "(Option „Sofort senden“ auf der Seite E-Mail-Kommunikation). "
            "Ohne diese Angaben bleibt der Versand ein Entwurf im Verlauf."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {c['secondary_label']}; font-size: 13px;")
        card_layout.addWidget(info)

        form = QtWidgets.QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)

        self.smtp_host_input = QtWidgets.QLineEdit()
        self.smtp_host_input.setPlaceholderText("z. B. smtp.example.com")
        form.addRow("Server (Host):", self.smtp_host_input)

        self.smtp_port_spin = QtWidgets.QSpinBox()
        self.smtp_port_spin.setRange(1, 65535)
        self.smtp_port_spin.setValue(587)
        form.addRow("Port:", self.smtp_port_spin)

        self.smtp_user_input = QtWidgets.QLineEdit()
        self.smtp_user_input.setPlaceholderText("Optional")
        form.addRow("Benutzername:", self.smtp_user_input)

        self.smtp_password_input = QtWidgets.QLineEdit()
        self.smtp_password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.smtp_password_input.setPlaceholderText("Optional")
        form.addRow("Passwort:", self.smtp_password_input)

        self.smtp_from_input = QtWidgets.QLineEdit()
        self.smtp_from_input.setPlaceholderText("absender@domain.de")
        form.addRow("Absender (E-Mail):", self.smtp_from_input)

        self.smtp_from_name_input = QtWidgets.QLineEdit()
        self.smtp_from_name_input.setPlaceholderText("z. B. ND-Hub")
        form.addRow("Absender (Name):", self.smtp_from_name_input)

        tls_row = QtWidgets.QHBoxLayout()
        self.smtp_tls_check = QtWidgets.QCheckBox("STARTTLS (Port 587)")
        self.smtp_tls_check.setChecked(True)
        self.smtp_ssl_check = QtWidgets.QCheckBox("SSL/SMTPS (Port 465)")
        tls_row.addWidget(self.smtp_tls_check)
        tls_row.addWidget(self.smtp_ssl_check)
        tls_row.addStretch()
        form.addRow("Verschlüsselung:", tls_row)

        card_layout.addLayout(form)

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_smtp_save = QtWidgets.QPushButton("SMTP speichern")
        self.btn_smtp_save.setIcon(IconManager.get_icon("save"))
        self.btn_smtp_save.setObjectName("btn_save")
        self.btn_smtp_save.setMinimumHeight(38)
        self.btn_smtp_test = QtWidgets.QPushButton("Verbindung testen")
        self.btn_smtp_test.setIcon(IconManager.get_icon("activity"))
        self.btn_smtp_test.setObjectName("btn_secondary")
        self.btn_smtp_test.setMinimumHeight(38)
        btn_row.addWidget(self.btn_smtp_save)
        btn_row.addWidget(self.btn_smtp_test)
        btn_row.addStretch()
        card_layout.addLayout(btn_row)

        self.smtp_status_label = QtWidgets.QLabel("")
        self.smtp_status_label.setWordWrap(True)
        self.smtp_status_label.setStyleSheet(f"font-size: 12px; color: {c['secondary_label']};")
        card_layout.addWidget(self.smtp_status_label)

        layout.addWidget(card)
        layout.addStretch()

        self.btn_smtp_save.clicked.connect(self.save_smtp_email_settings)
        self.btn_smtp_test.clicked.connect(self.test_smtp_email_settings)
        self.smtp_ssl_check.toggled.connect(self._on_smtp_ssl_toggled)
        self.smtp_tls_check.toggled.connect(self._on_smtp_tls_toggled)
        self.load_smtp_email_settings()
        return tab

    def _on_smtp_ssl_toggled(self, checked: bool):
        if checked and hasattr(self, "smtp_tls_check"):
            self.smtp_tls_check.blockSignals(True)
            self.smtp_tls_check.setChecked(False)
            self.smtp_tls_check.blockSignals(False)

    def _on_smtp_tls_toggled(self, checked: bool):
        if checked and hasattr(self, "smtp_ssl_check"):
            self.smtp_ssl_check.blockSignals(True)
            self.smtp_ssl_check.setChecked(False)
            self.smtp_ssl_check.blockSignals(False)

    def _collect_smtp_form_dict(self) -> dict:
        return {
            "host": self.smtp_host_input.text().strip(),
            "port": int(self.smtp_port_spin.value()),
            "username": self.smtp_user_input.text().strip(),
            "password": self.smtp_password_input.text(),
            "use_tls": self.smtp_tls_check.isChecked(),
            "use_ssl": self.smtp_ssl_check.isChecked(),
            "from_address": self.smtp_from_input.text().strip(),
            "from_name": self.smtp_from_name_input.text().strip(),
        }

    def load_smtp_email_settings(self):
        cfg = self.db.get_smtp_settings()
        self.smtp_host_input.setText(cfg.get("host", "") or "")
        self.smtp_port_spin.setValue(int(cfg.get("port") or 587))
        self.smtp_user_input.setText(cfg.get("username", "") or "")
        self.smtp_password_input.setText(cfg.get("password", "") or "")
        self.smtp_from_input.setText(cfg.get("from_address", "") or "")
        self.smtp_from_name_input.setText(cfg.get("from_name", "") or "")
        use_ssl = bool(cfg.get("use_ssl"))
        self.smtp_ssl_check.setChecked(use_ssl)
        self.smtp_tls_check.setChecked(bool(cfg.get("use_tls")) and not use_ssl)
        self.smtp_status_label.setText("Einstellungen geladen.")

    def save_smtp_email_settings(self):
        try:
            self.db.save_smtp_settings(self._collect_smtp_form_dict())
            self.smtp_status_label.setText("SMTP-Konfiguration gespeichert.")
            self._toast("SMTP-Einstellungen gespeichert.", "success")
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "SMTP", f"Speichern fehlgeschlagen:\n{exc}")

    def test_smtp_email_settings(self):
        self.smtp_status_label.setText("Teste Verbindung …")
        QtWidgets.QApplication.processEvents()
        ok, msg = self.db.test_smtp_connection(self._collect_smtp_form_dict())
        self.smtp_status_label.setText(msg)
        if ok:
            self._toast("SMTP-Test erfolgreich.", "success")
        else:
            QtWidgets.QMessageBox.warning(self, "SMTP-Test", msg)

    def create_backup_tab(self):
        """Erstellt den Backup-Tab"""
        tab = QtWidgets.QWidget()
        outer_layout = QtWidgets.QVBoxLayout(tab)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        outer_layout.addWidget(scroll)

        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        scroll.setWidget(content)

        # === Manuelles Backup ===
        backup_card = create_card_widget()
        backup_layout = QtWidgets.QVBoxLayout(backup_card)

        c = AppleTheme.current_colors()
        backup_title = QtWidgets.QLabel("Backup erstellen")
        backup_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {c['label']}; margin-bottom: 8px;")
        backup_layout.addWidget(backup_title)

        backup_info = QtWidgets.QLabel(
            "Erstellen Sie eine Sicherungskopie der gesamten Datenbank.\n"
            "Die Backup-Datei enthält alle Depots, Präparate, Bewegungen und Einstellungen."
        )
        backup_info.setWordWrap(True)
        backup_info.setStyleSheet(f"color: {c['secondary_label']}; font-size: 13px; margin-bottom: 12px;")
        backup_layout.addWidget(backup_info)

        backup_path_layout = QtWidgets.QHBoxLayout()
        backup_path_layout.addWidget(QtWidgets.QLabel("Backup-Ordner:"))
        self.backup_path_input = QtWidgets.QLineEdit()
        self.backup_path_input.setPlaceholderText("\\ND-Hub\\Backups")
        self.backup_path_input.setText(self.get_default_backup_path())
        backup_path_layout.addWidget(self.backup_path_input, 1)

        self.btn_browse_backup = QtWidgets.QPushButton(" Durchsuchen")
        self.btn_browse_backup.setIcon(IconManager.get_icon("folder"))
        self.btn_browse_backup.setObjectName("btn_secondary")
        backup_path_layout.addWidget(self.btn_browse_backup)
        backup_layout.addLayout(backup_path_layout)

        self.btn_create_backup = QtWidgets.QPushButton(" Backup jetzt erstellen")
        self.btn_create_backup.setIcon(IconManager.get_icon("refresh"))
        self.btn_create_backup.setObjectName("btn_save")
        self.btn_create_backup.setMinimumHeight(44)
        backup_layout.addWidget(self.btn_create_backup)

        layout.addWidget(backup_card)

        # === Auto-Backup ===
        auto_backup_card = create_card_widget()
        auto_backup_layout = QtWidgets.QVBoxLayout(auto_backup_card)

        c = AppleTheme.current_colors()
        auto_backup_title = QtWidgets.QLabel("Automatisches Backup")
        auto_backup_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {c['label']}; margin-bottom: 8px;")
        auto_backup_layout.addWidget(auto_backup_title)

        auto_backup_info = QtWidgets.QLabel(
            "Aktivieren Sie automatische Backups beim Programmstart.\n"
            "Es wird maximal ein Backup pro Tag erstellt."
        )
        auto_backup_info.setWordWrap(True)
        auto_backup_info.setStyleSheet(f"color: {c['secondary_label']}; font-size: 13px; margin-bottom: 12px;")
        auto_backup_layout.addWidget(auto_backup_info)

        self.check_auto_backup_enabled = QtWidgets.QCheckBox("Automatisches Backup beim Start aktivieren")
        self.check_auto_backup_enabled.setProperty("requires_write", True)
        auto_backup_setting = self.load_auto_backup_setting()
        self.check_auto_backup_enabled.setChecked(auto_backup_setting)
        self.check_auto_backup_enabled.toggled.connect(self.save_auto_backup_setting_from_bool)
        auto_backup_layout.addWidget(self.check_auto_backup_enabled)

        c = AppleTheme.current_colors()
        auto_backup_info2 = QtWidgets.QLabel("Backups werden im oben angegebenen Ordner gespeichert.")
        auto_backup_info2.setWordWrap(True)
        auto_backup_info2.setStyleSheet(f"color: {c['tertiary_label']}; font-size: 12px; font-style: italic; margin-top: 8px;")
        auto_backup_layout.addWidget(auto_backup_info2)

        layout.addWidget(auto_backup_card)

        # === NEU: Test-Daten zurücksetzen ===
        reset_card = create_card_widget()
        reset_layout = QtWidgets.QVBoxLayout(reset_card)

        c = AppleTheme.current_colors()
        reset_title = QtWidgets.QLabel("Test-Daten zurücksetzen")
        reset_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {c['label']}; margin-bottom: 8px;")
        reset_layout.addWidget(reset_title)

        reset_info = QtWidgets.QLabel(
            "Löscht alle Bewegungen und den E-Mail-Verlauf.\n"
            "Depots, Kontakte, Präparate und Sollbestände bleiben erhalten.\n"
            "Ideal zum Zurücksetzen nach Tests."
        )
        reset_info.setWordWrap(True)
        reset_info.setStyleSheet(f"color: {c['secondary_label']}; font-size: 13px; margin-bottom: 12px;")
        reset_layout.addWidget(reset_info)

        reset_warning = QtWidgets.QLabel(
            "ACHTUNG: Diese Aktion kann nicht rückgängig gemacht werden!\n"
            "Erstellen Sie vorher ein Backup."
        )
        reset_warning.setWordWrap(True)
        reset_warning.setStyleSheet(
            "background-color: #fff3cd; color: #856404; padding: 12px; "
            "border-radius: 6px; border: 1px solid #ffc107; font-weight: 500; margin-bottom: 12px;"
        )
        reset_layout.addWidget(reset_warning)

        self.btn_reset_data = QtWidgets.QPushButton("Test-Daten jetzt zurücksetzen")
        self.btn_reset_data.setIcon(IconManager.get_icon("delete"))
        self.btn_reset_data.setObjectName("btn_delete")
        self.btn_reset_data.setMinimumHeight(44)
        reset_layout.addWidget(self.btn_reset_data)

        layout.addWidget(reset_card)

        # === Wiederherstellung ===
        restore_card = create_card_widget()
        restore_layout = QtWidgets.QVBoxLayout(restore_card)

        c = AppleTheme.current_colors()
        restore_title = QtWidgets.QLabel("Backup wiederherstellen")
        restore_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {c['label']}; margin-bottom: 8px;")
        restore_layout.addWidget(restore_title)

        restore_warning = QtWidgets.QLabel(
            "ACHTUNG: Das Wiederherstellen eines Backups überschreibt ALLE aktuellen Daten!\n"
            "Erstellen Sie vorher unbedingt ein aktuelles Backup."
        )
        restore_warning.setWordWrap(True)
        restore_warning.setStyleSheet(
            f"background-color: {c['status_orange_bg']}; color: {c['status_orange']}; padding: 12px; "
            f"border-radius: 6px; border: 1px solid {c['status_orange']}; font-weight: 500; margin-bottom: 12px;"
        )
        restore_layout.addWidget(restore_warning)

        restore_path_layout = QtWidgets.QHBoxLayout()
        restore_path_layout.addWidget(QtWidgets.QLabel("Backup-Datei:"))
        self.restore_path_input = QtWidgets.QLineEdit()
        self.restore_path_input.setPlaceholderText("Backup-Datei auswählen...")
        self.restore_path_input.setReadOnly(True)
        restore_path_layout.addWidget(self.restore_path_input, 1)

        self.btn_browse_restore = QtWidgets.QPushButton(" Durchsuchen")
        self.btn_browse_restore.setIcon(IconManager.get_icon("folder"))
        self.btn_browse_restore.setObjectName("btn_secondary")
        restore_path_layout.addWidget(self.btn_browse_restore)
        restore_layout.addLayout(restore_path_layout)

        self.btn_restore_backup = QtWidgets.QPushButton(" Backup wiederherstellen")
        self.btn_restore_backup.setIcon(IconManager.get_icon("refresh_ccw"))
        self.btn_restore_backup.setObjectName("btn_delete")
        self.btn_restore_backup.setMinimumHeight(44)
        self.btn_restore_backup.setEnabled(False)
        restore_layout.addWidget(self.btn_restore_backup)

        layout.addWidget(restore_card)
        layout.addStretch()

        # Signals
        self.btn_browse_backup.clicked.connect(self.browse_backup_folder)
        self.btn_create_backup.clicked.connect(self.create_backup)
        self.btn_reset_data.clicked.connect(self.reset_test_data)  # NEU
        self.btn_browse_restore.clicked.connect(self.browse_restore_file)
        self.btn_restore_backup.clicked.connect(self.restore_backup)

        return tab

    def reset_test_data(self):
        """Setzt Test-Daten zurück mit Bestätigung"""
        if self._is_read_only_mode():
            QtWidgets.QMessageBox.warning(self, "Nur-Lesen Modus", "Zurücksetzen ist nur mit Schreibzugriff möglich.")
            return

        # Erste Bestätigung
        reply = QtWidgets.QMessageBox.warning(
            self,
            "Test-Daten zurücksetzen",
            "WARNUNG: Diese Aktion löscht unwiderruflich:\n\n"
            "  • Alle Bewegungen (Zugang/Abgang/Vernichtung)\n"
            "  • Den gesamten E-Mail-Verlauf\n\n"
            "Folgende Daten bleiben erhalten:\n\n"
            "  • Depots\n"
            "  • Kontakte\n"
            "  • Präparate\n"
            "  • Zuordnungen mit Sollbeständen\n\n"
            "Möchten Sie fortfahren?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        # Zweite Sicherheitsabfrage mit Texteingabe
        text, ok = QtWidgets.QInputDialog.getText(
            self,
            "Bestätigung erforderlich",
            "Bitte geben Sie 'ZURÜCKSETZEN' ein, um fortzufahren:",
            QtWidgets.QLineEdit.Normal,
            ""
        )

        if not ok or text.upper() != "ZURÜCKSETZEN":
            QtWidgets.QMessageBox.information(
                self,
                "Abgebrochen",
                "Reset wurde abgebrochen."
            )
            return

        # Backup erstellen (optional, aber empfohlen)
        backup_path = None
        try:
            import shutil
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db.path}.before_reset_{timestamp}"
            shutil.copy2(self.db.path, backup_path)
            backup_created = True
        except Exception as e:
            backup_created = False
            reply = QtWidgets.QMessageBox.warning(
                self,
                "Backup fehlgeschlagen",
                f"Backup konnte nicht erstellt werden:\n{e}\n\n"
                "Trotzdem fortfahren?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

        # Reset durchführen
        success, msg, stats = self.db.reset_test_data()

        if success:
            # Erfolgs-Nachricht mit Backup-Info
            full_msg = msg
            if backup_created and backup_path:
                full_msg += f"\n\n💾 Backup erstellt:\n{backup_path}"

            QtWidgets.QMessageBox.information(
                self,
                "Erfolgreich",
                full_msg
            )

        else:
            QtWidgets.QMessageBox.critical(
                self,
                "Fehler",
                msg
            )

    def get_default_backup_path(self):
        """Ermittelt den Standard-Backup-Pfad"""
        db_dir = os.path.dirname(self.db.path)
        backup_dir = os.path.join(db_dir, "Backups")
        return backup_dir

    def create_sync_tab(self):
        """Erstellt Monitoring-Tab fuer Outbox/Sync-Zustand."""
        tab = QtWidgets.QWidget()
        outer_layout = QtWidgets.QVBoxLayout(tab)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        outer_layout.addWidget(scroll)

        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        scroll.setWidget(content)

        settings_card = create_card_widget()
        settings_layout = QtWidgets.QVBoxLayout(settings_card)
        settings_layout.setSpacing(10)
        settings_title = QtWidgets.QLabel("Desktop-Sync Konfiguration")
        settings_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {AppleTheme.current_colors()['label']};")
        settings_layout.addWidget(settings_title)
        settings_info = QtWidgets.QLabel(
            "Konfigurieren Sie hier Betriebsmodus, Backend-URL und Token fuer den Hybrid-Sync."
        )
        settings_info.setWordWrap(True)
        settings_info.setStyleSheet(f"color: {AppleTheme.current_colors()['secondary_label']}; font-size: 13px;")
        settings_layout.addWidget(settings_info)

        form = QtWidgets.QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)
        self.sync_mode_combo = QtWidgets.QComboBox()
        self.sync_mode_combo.addItem("Nur lokal (local_only)", "local_only")
        self.sync_mode_combo.addItem("Hybrid Sync (hybrid_sync)", "hybrid_sync")
        self.sync_mode_combo.addItem("Nur Remote (remote_only)", "remote_only")
        form.addRow("Betriebsmodus:", self.sync_mode_combo)

        self.sync_backend_url_input = QtWidgets.QLineEdit()
        self.sync_backend_url_input.setPlaceholderText("http://127.0.0.1:8000")
        form.addRow("Backend-URL:", self.sync_backend_url_input)

        self.sync_backend_token_input = QtWidgets.QLineEdit()
        self.sync_backend_token_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.sync_backend_token_input.setPlaceholderText("Bearer Token aus Web-App")
        form.addRow("Backend-Token:", self.sync_backend_token_input)
        settings_layout.addLayout(form)

        settings_actions = QtWidgets.QVBoxLayout()
        settings_actions.setSpacing(8)
        self.btn_sync_save_config = QtWidgets.QPushButton("Sync-Konfiguration speichern")
        self.btn_sync_save_config.setIcon(IconManager.get_icon("save"))
        self.btn_sync_save_config.setObjectName("btn_save")
        self.btn_sync_save_config.setMinimumHeight(38)
        settings_actions.addWidget(self.btn_sync_save_config)
        self.btn_sync_test_connection = QtWidgets.QPushButton("Backend-Verbindung testen")
        self.btn_sync_test_connection.setIcon(IconManager.get_icon("activity"))
        self.btn_sync_test_connection.setObjectName("btn_secondary")
        self.btn_sync_test_connection.setMinimumHeight(38)
        settings_actions.addWidget(self.btn_sync_test_connection)
        settings_layout.addLayout(settings_actions)

        self.sync_config_status_label = QtWidgets.QLabel("")
        self.sync_config_status_label.setStyleSheet(f"font-size: 12px; color: {AppleTheme.current_colors()['secondary_label']};")
        self.sync_config_status_label.setWordWrap(True)
        settings_layout.addWidget(self.sync_config_status_label)
        layout.addWidget(settings_card)

        token_card = create_card_widget()
        token_layout = QtWidgets.QVBoxLayout(token_card)
        token_layout.setSpacing(8)
        token_title = QtWidgets.QLabel("Desktop-Sync Tokens")
        token_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {AppleTheme.current_colors()['label']};")
        token_layout.addWidget(token_title)
        token_info = QtWidgets.QLabel("Erzeugt und verwaltet API-Tokens fuer Desktop-Hybrid-Sync.")
        token_info.setWordWrap(True)
        token_info.setStyleSheet(f"color: {AppleTheme.current_colors()['secondary_label']}; font-size: 12px;")
        token_layout.addWidget(token_info)

        token_form = QtWidgets.QFormLayout()
        token_form.setContentsMargins(0, 0, 0, 0)
        token_form.setSpacing(8)
        self.sync_token_note_input = QtWidgets.QLineEdit()
        self.sync_token_note_input.setPlaceholderText("Notiz (optional)")
        token_form.addRow("Notiz:", self.sync_token_note_input)
        self.sync_token_hours_spin = QtWidgets.QSpinBox()
        self.sync_token_hours_spin.setRange(1, 24 * 30)
        self.sync_token_hours_spin.setValue(72)
        self.sync_token_hours_spin.setSuffix(" h")
        token_form.addRow("Gueltig:", self.sync_token_hours_spin)
        token_layout.addLayout(token_form)

        token_btn_row = QtWidgets.QHBoxLayout()
        self.btn_sync_create_token = QtWidgets.QPushButton("Token erzeugen")
        self.btn_sync_create_token.setObjectName("btn_save")
        self.btn_sync_create_token.setMinimumHeight(38)
        token_btn_row.addWidget(self.btn_sync_create_token)
        token_btn_row.addStretch()
        token_layout.addLayout(token_btn_row)

        self.sync_token_output = QtWidgets.QPlainTextEdit()
        self.sync_token_output.setReadOnly(True)
        self.sync_token_output.setPlaceholderText("Neuer Token wird hier angezeigt.")
        self.sync_token_output.setMinimumHeight(70)
        token_layout.addWidget(self.sync_token_output)

        self.table_sync_tokens = QtWidgets.QTableWidget()
        self.table_sync_tokens.setColumnCount(4)
        self.table_sync_tokens.setHorizontalHeaderLabels(["Token-ID", "Benutzer", "Ablauf", "Notiz"])
        self.table_sync_tokens.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_sync_tokens.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table_sync_tokens.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table_sync_tokens.setMinimumHeight(140)
        token_layout.addWidget(self.table_sync_tokens)

        token_actions = QtWidgets.QVBoxLayout()
        token_actions.setSpacing(8)
        self.btn_sync_refresh_tokens = QtWidgets.QPushButton("Tokens laden")
        self.btn_sync_refresh_tokens.setObjectName("btn_secondary")
        self.btn_sync_refresh_tokens.setMinimumHeight(38)
        token_actions.addWidget(self.btn_sync_refresh_tokens)
        self.btn_sync_revoke_token = QtWidgets.QPushButton("Ausgewaehlten Token widerrufen")
        self.btn_sync_revoke_token.setObjectName("btn_delete")
        self.btn_sync_revoke_token.setMinimumHeight(38)
        token_actions.addWidget(self.btn_sync_revoke_token)
        token_layout.addLayout(token_actions)
        layout.addWidget(token_card)

        card = create_card_widget()
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setSpacing(10)

        c = AppleTheme.current_colors()
        title = QtWidgets.QLabel("Synchronisation")
        title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {c['label']};")
        card_layout.addWidget(title)

        info = QtWidgets.QLabel(
            "Zeigt den Zustand der lokalen Sync-Outbox.\n"
            "Konflikte koennen erneut in die Retry-Warteschlange gestellt werden."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {c['secondary_label']}; font-size: 13px;")
        card_layout.addWidget(info)

        state_row = QtWidgets.QHBoxLayout()
        state_row.setSpacing(8)
        state_title = QtWidgets.QLabel("Status:")
        state_title.setStyleSheet(f"font-size: 13px; color: {c['secondary_label']};")
        state_row.addWidget(state_title)
        self.sync_state_badge = QtWidgets.QLabel("UNBEKANNT")
        self.sync_state_badge.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #ffffff; "
            "background-color: #6b7280; border-radius: 10px; padding: 2px 8px;"
        )
        state_row.addWidget(self.sync_state_badge)
        self.sync_state_hint = QtWidgets.QLabel("")
        self.sync_state_hint.setStyleSheet(f"font-size: 12px; color: {c['secondary_label']};")
        state_row.addWidget(self.sync_state_hint, 1)
        state_row.addStretch()
        card_layout.addLayout(state_row)

        self.sync_next_run_label = QtWidgets.QLabel("Auto-Sync: -")
        self.sync_next_run_label.setStyleSheet(f"font-size: 12px; color: {c['secondary_label']};")
        card_layout.addWidget(self.sync_next_run_label)

        self.sync_stats_label = QtWidgets.QLabel("-")
        self.sync_stats_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.sync_stats_label.setStyleSheet(f"font-size: 13px; color: {c['label']};")
        card_layout.addWidget(self.sync_stats_label)

        self.sync_remote_stats_label = QtWidgets.QLabel("Remote-Stats: -")
        self.sync_remote_stats_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.sync_remote_stats_label.setStyleSheet(f"font-size: 12px; color: {c['secondary_label']};")
        card_layout.addWidget(self.sync_remote_stats_label)

        actions = QtWidgets.QVBoxLayout()
        actions.setSpacing(8)
        self.btn_sync_refresh = QtWidgets.QPushButton("Status aktualisieren")
        self.btn_sync_refresh.setIcon(IconManager.get_icon("refresh_ccw"))
        self.btn_sync_refresh.setObjectName("btn_secondary")
        self.btn_sync_refresh.setMinimumHeight(38)
        actions.addWidget(self.btn_sync_refresh)

        self.btn_sync_retry_conflicts = QtWidgets.QPushButton("Konflikte erneut versuchen")
        self.btn_sync_retry_conflicts.setIcon(IconManager.get_icon("refresh_ccw"))
        self.btn_sync_retry_conflicts.setObjectName("btn_secondary")
        self.btn_sync_retry_conflicts.setMinimumHeight(38)
        actions.addWidget(self.btn_sync_retry_conflicts)

        self.btn_sync_run_now = QtWidgets.QPushButton("Jetzt synchronisieren")
        self.btn_sync_run_now.setIcon(IconManager.get_icon("activity"))
        self.btn_sync_run_now.setMinimumHeight(38)
        actions.addWidget(self.btn_sync_run_now)
        card_layout.addLayout(actions)

        layout.addWidget(card)
        layout.addStretch()

        self.btn_sync_refresh.clicked.connect(self.refresh_sync_status)
        self.btn_sync_retry_conflicts.clicked.connect(self.retry_sync_conflicts)
        self.btn_sync_run_now.clicked.connect(self.trigger_sync_now)
        self.btn_sync_save_config.clicked.connect(self.save_sync_configuration)
        self.btn_sync_test_connection.clicked.connect(self.test_sync_connection)
        self.btn_sync_create_token.clicked.connect(self.create_sync_token)
        self.btn_sync_refresh_tokens.clicked.connect(self.refresh_sync_tokens)
        self.btn_sync_revoke_token.clicked.connect(self.revoke_selected_sync_token)
        self.sync_schedule_timer = QtCore.QTimer(self)
        self.sync_schedule_timer.timeout.connect(self._update_sync_schedule_hint)
        self.sync_schedule_timer.start(1000)
        self.load_sync_configuration()
        self._update_sync_schedule_hint()
        self.refresh_sync_tokens()
        self._update_sync_tab_responsiveness()
        return tab

    def _update_sync_tab_responsiveness(self) -> None:
        if not hasattr(self, "sync_page"):
            return
        compact = self.sync_page.width() < 980

        if hasattr(self, "btn_sync_save_config"):
            self.btn_sync_save_config.setText("Speichern" if compact else "Sync-Konfiguration speichern")
        if hasattr(self, "btn_sync_test_connection"):
            self.btn_sync_test_connection.setText("Verbindung testen" if compact else "Backend-Verbindung testen")
        if hasattr(self, "btn_sync_create_token"):
            self.btn_sync_create_token.setText("Token erstellen" if compact else "Token erzeugen")
        if hasattr(self, "btn_sync_refresh_tokens"):
            self.btn_sync_refresh_tokens.setText("Tokens neu laden" if compact else "Tokens laden")
        if hasattr(self, "btn_sync_revoke_token"):
            self.btn_sync_revoke_token.setText("Token widerrufen" if compact else "Ausgewaehlten Token widerrufen")
        if hasattr(self, "btn_sync_refresh"):
            self.btn_sync_refresh.setText("Aktualisieren" if compact else "Status aktualisieren")
        if hasattr(self, "btn_sync_retry_conflicts"):
            self.btn_sync_retry_conflicts.setText("Konflikte retry" if compact else "Konflikte erneut versuchen")
        if hasattr(self, "btn_sync_run_now"):
            self.btn_sync_run_now.setText("Jetzt syncen" if compact else "Jetzt synchronisieren")

        if hasattr(self, "table_sync_tokens"):
            self.table_sync_tokens.horizontalHeader().setStretchLastSection(True)
            if compact:
                self.table_sync_tokens.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
                self.table_sync_tokens.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                self.table_sync_tokens.setColumnWidth(0, 190)
                self.table_sync_tokens.setColumnWidth(1, 120)
                self.table_sync_tokens.setColumnWidth(2, 145)
            else:
                self.table_sync_tokens.resizeColumnsToContents()

    def _get_host_config(self):
        host = self.window()
        return getattr(host, "config", None)

    def load_sync_configuration(self) -> None:
        config = self._get_host_config()
        if config is None:
            self.sync_config_status_label.setText("Konfiguration im Hauptfenster nicht verfuegbar.")
            return
        mode = str(getattr(config, "get_operating_mode", lambda: "local_only")() or "local_only").strip().lower()
        mode_index = self.sync_mode_combo.findData(mode)
        if mode_index < 0:
            mode_index = self.sync_mode_combo.findData("local_only")
        if mode_index >= 0:
            self.sync_mode_combo.setCurrentIndex(mode_index)
        self.sync_backend_url_input.setText(str(getattr(config, "get_backend_url", lambda: "")() or "").strip())
        self.sync_backend_token_input.setText(str(getattr(config, "get_backend_token", lambda: "")() or "").strip())
        self.sync_config_status_label.setText("Aktuelle Sync-Konfiguration geladen.")

    def save_sync_configuration(self) -> None:
        config = self._get_host_config()
        if config is None:
            QtWidgets.QMessageBox.warning(self, "Sync", "Konfiguration im Hauptfenster nicht verfuegbar.")
            return
        mode = str(self.sync_mode_combo.currentData() or "local_only").strip().lower()
        if mode not in {item.value for item in OperatingMode}:
            mode = "local_only"
        backend_url = self.sync_backend_url_input.text().strip()
        backend_token = self.sync_backend_token_input.text().strip()
        try:
            config.set_operating_mode(mode)
            config.set_backend_url(backend_url)
            config.set_backend_token(backend_token)
            host = self.window()
            if hasattr(host, "_init_data_access_layer"):
                host._init_data_access_layer()
            if hasattr(host, "_init_sync_service"):
                host._init_sync_service()
            if hasattr(host, "_refresh_sync_scheduler"):
                host._refresh_sync_scheduler()
            self.sync_config_status_label.setText("Konfiguration gespeichert. Sync-Service neu initialisiert.")
            self._toast("Sync-Konfiguration gespeichert.", "success")
            self.refresh_sync_status()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Sync", f"Konfiguration konnte nicht gespeichert werden:\n{exc}")

    def test_sync_connection(self) -> None:
        backend_url = self.sync_backend_url_input.text().strip()
        if not backend_url:
            self.sync_config_status_label.setText("Bitte zuerst eine Backend-URL eintragen.")
            return
        self.sync_config_status_label.setText("Pruefe Verbindung...")
        QtWidgets.QApplication.processEvents()
        token = self.sync_backend_token_input.text().strip()
        try:
            client = BackendApiClient(BackendSyncConfig(base_url=backend_url, access_token=token))
            healthy = client.check_health()
            if not healthy:
                self.sync_config_status_label.setText("Backend nicht erreichbar oder Healthcheck fehlgeschlagen.")
                return
            me_info = "-"
            if token:
                try:
                    req = request.Request(
                        _require_http_scheme(f"{backend_url.rstrip('/')}/auth/me"),
                        method="GET",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    with request.urlopen(req, timeout=4) as response:  # nosec B310: URL scheme validated by _require_http_scheme
                        if 200 <= response.status < 300:
                            me_info = "Token gueltig"
                except error.HTTPError as exc:
                    me_info = f"Token-Check fehlgeschlagen ({exc.code})"
                except Exception:
                    me_info = "Token-Check fehlgeschlagen"
            self.sync_config_status_label.setText(f"Backend erreichbar. {me_info}")
        except Exception as exc:
            self.sync_config_status_label.setText(f"Verbindungstest fehlgeschlagen: {exc}")

    def _build_api_client_from_inputs(self) -> BackendApiClient:
        backend_url = self.sync_backend_url_input.text().strip()
        token = self.sync_backend_token_input.text().strip()
        if not backend_url:
            raise RuntimeError("Backend-URL ist leer.")
        return BackendApiClient(BackendSyncConfig(base_url=backend_url, access_token=token))

    def refresh_sync_tokens(self) -> None:
        if not hasattr(self, "table_sync_tokens"):
            return
        self.table_sync_tokens.setRowCount(0)
        try:
            client = self._build_api_client_from_inputs()
            payload = client.list_sync_tokens()
            rows = payload.get("tokens") or payload.get("items") or []
            self.table_sync_tokens.setRowCount(len(rows))
            for r, row in enumerate(rows):
                token_id = str(row.get("id") or row.get("token_id") or "")
                username = str(row.get("username") or "")
                expires = str(row.get("expires_at") or row.get("expiresAt") or "-")
                note = str(row.get("note") or "")
                self.table_sync_tokens.setItem(r, 0, QtWidgets.QTableWidgetItem(token_id))
                self.table_sync_tokens.setItem(r, 1, QtWidgets.QTableWidgetItem(username))
                self.table_sync_tokens.setItem(r, 2, QtWidgets.QTableWidgetItem(expires))
                self.table_sync_tokens.setItem(r, 3, QtWidgets.QTableWidgetItem(note))
            self.table_sync_tokens.resizeColumnsToContents()
        except Exception as exc:
            self.sync_config_status_label.setText(f"Token-Liste konnte nicht geladen werden: {exc}")

    def create_sync_token(self) -> None:
        if self._is_read_only_mode():
            QtWidgets.QMessageBox.warning(self, "Nur-Lesen Modus", "Token-Erstellung ist nur mit Schreibzugriff moeglich.")
            return
        host = self.window()
        username = ""
        if hasattr(host, "security") and hasattr(host.security, "get_current_user"):
            username = str(host.security.get_current_user() or "")
        if not username:
            username = "desktop-client"
        try:
            client = self._build_api_client_from_inputs()
            payload = client.create_sync_token(
                username=username,
                expires_in_hours=int(self.sync_token_hours_spin.value()),
                note=self.sync_token_note_input.text().strip(),
            )
            token_value = str(payload.get("token") or payload.get("access_token") or "")
            self.sync_token_output.setPlainText(token_value or "Token wurde erstellt, aber nicht im Response geliefert.")
            self._toast("Sync-Token erstellt.", "success")
            self.refresh_sync_tokens()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Sync-Token", f"Token konnte nicht erstellt werden:\n{exc}")

    def revoke_selected_sync_token(self) -> None:
        row = self.table_sync_tokens.currentRow() if hasattr(self, "table_sync_tokens") else -1
        if row < 0:
            QtWidgets.QMessageBox.information(self, "Sync-Token", "Bitte zuerst einen Token auswaehlen.")
            return
        token_id_item = self.table_sync_tokens.item(row, 0)
        token_id = token_id_item.text().strip() if token_id_item else ""
        if not token_id:
            return
        try:
            client = self._build_api_client_from_inputs()
            client.revoke_sync_token(token_id=token_id)
            self._toast("Sync-Token widerrufen.", "info")
            self.refresh_sync_tokens()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Sync-Token", f"Token konnte nicht widerrufen werden:\n{exc}")

    def _is_read_only_mode(self) -> bool:
        return bool(getattr(self.db, "is_read_only_mode", lambda: False)())

    def _toast(self, message: str, level: str = "info") -> None:
        host = self.window()
        if hasattr(host, "show_toast"):
            host.show_toast(message, level)

    def refresh_sync_status(self) -> None:
        if not hasattr(self, "sync_stats_label"):
            return
        if not hasattr(self.db, "get_sync_outbox_stats"):
            self.sync_stats_label.setText("Outbox-Statistiken nicht verfuegbar.")
            self._set_sync_state_badge("UNBEKANNT", "#6b7280", "Keine Outbox-API vorhanden")
            return
        try:
            stats = self.db.get_sync_outbox_stats()
            counts = stats.get("counts", {})
            pending = int(counts.get("pending", 0))
            retry = int(counts.get("retry", 0))
            conflict = int(counts.get("conflict", 0))
            done = int(counts.get("done", 0))
            oldest = stats.get("oldest_pending_at")
            latest_success = stats.get("latest_success_at")
            latest_error = stats.get("latest_error") or {}
            lines = [
                f"Pending: {pending}",
                f"Retry: {retry}",
                f"Conflict: {conflict}",
                f"Done: {done}",
                f"Total: {int(counts.get('total', 0))}",
            ]
            if oldest:
                lines.append(f"Aeltester offener Eintrag: {oldest}")
            if latest_success:
                lines.append(f"Letzter erfolgreicher Sync: {latest_success}")
            if latest_error:
                error_status = str(latest_error.get("status") or "?").upper()
                error_at = str(latest_error.get("at") or "")
                error_message = str(latest_error.get("message") or "")
                if len(error_message) > 160:
                    error_message = f"{error_message[:157]}..."
                lines.append(f"Letzter Fehler [{error_status}] ({error_at}): {error_message}")
            self.sync_stats_label.setText("\n".join(lines))
            self._refresh_remote_sync_stats()
            if conflict > 0:
                self._set_sync_state_badge("KRITISCH", "#dc2626", "Konflikte vorhanden")
            elif retry > 0:
                self._set_sync_state_badge("WARNUNG", "#d97706", "Retry-Eintraege vorhanden")
            elif pending > 0:
                self._set_sync_state_badge("AKTIV", "#f59e0b", "Pending-Eintraege werden synchronisiert")
            elif done > 0:
                self._set_sync_state_badge("OK", "#16a34a", "Letzte Synchronisation erfolgreich")
            else:
                self._set_sync_state_badge("LEER", "#2563eb", "Noch keine Sync-Aktivitaet")
        except Exception as exc:
            self.sync_stats_label.setText(f"Fehler beim Laden der Sync-Statistik: {exc}")
            self._set_sync_state_badge("FEHLER", "#dc2626", "Status konnte nicht geladen werden")
        self._update_sync_schedule_hint()

    def _refresh_remote_sync_stats(self) -> None:
        if not hasattr(self, "sync_remote_stats_label"):
            return
        try:
            client = self._build_api_client_from_inputs()
            status_payload = client.get_sync_status()
            ops_payload = client.get_sync_ops_stats()
            status_text = str(status_payload.get("status") or status_payload.get("effective_mode") or "-")
            queued = int(status_payload.get("queued") or status_payload.get("pending") or 0)
            failed = int(status_payload.get("failed") or 0)
            pushed = int(ops_payload.get("pushed_total") or ops_payload.get("pushed") or 0)
            pulled = int(ops_payload.get("pulled_total") or ops_payload.get("pulled") or 0)
            self.sync_remote_stats_label.setText(
                f"Remote-Stats: status={status_text} queued={queued} failed={failed} pushed={pushed} pulled={pulled}"
            )
        except Exception:
            self.sync_remote_stats_label.setText("Remote-Stats: nicht verfuegbar")

    def _update_sync_schedule_hint(self) -> None:
        if not hasattr(self, "sync_next_run_label"):
            return
        def _set_hint(text: str, color_hex: str) -> None:
            self.sync_next_run_label.setText(text)
            self.sync_next_run_label.setStyleSheet(f"font-size: 12px; color: {color_hex}; font-weight: 600;")

        host = self.window()
        mode = OperatingMode.from_raw(self.sync_mode_combo.currentData() if hasattr(self, "sync_mode_combo") else "local_only")
        interval_seconds = 120
        if hasattr(host, "config"):
            try:
                interval_seconds = max(10, int(host.config.get_sync_interval_seconds()))
            except Exception:
                interval_seconds = 120
        if mode != OperatingMode.HYBRID_SYNC:
            _set_hint("Auto-Sync: pausiert (nur im Hybrid-Sync aktiv)", "#d97706")
            return
        sync_timer = getattr(host, "sync_timer", None)
        if sync_timer is None:
            _set_hint(f"Auto-Sync: Hybrid aktiv (Intervall {interval_seconds}s)", "#dc2626")
            return
        if not sync_timer.isActive():
            _set_hint(f"Auto-Sync: bereit (Intervall {interval_seconds}s, Timer pausiert)", "#d97706")
            return
        remaining_ms = int(sync_timer.remainingTime())
        if remaining_ms < 0:
            _set_hint(f"Auto-Sync: aktiv (Intervall {interval_seconds}s)", "#16a34a")
            return
        remaining_seconds = max(0, int((remaining_ms + 999) / 1000))
        _set_hint(
            f"Auto-Sync: aktiv - naechster Lauf in {remaining_seconds}s (Intervall {interval_seconds}s)",
            "#16a34a",
        )

    def _set_sync_state_badge(self, text: str, color_hex: str, hint: str) -> None:
        if hasattr(self, "sync_state_badge"):
            self.sync_state_badge.setText(text)
            self.sync_state_badge.setStyleSheet(
                "font-size: 11px; font-weight: 700; color: #ffffff; "
                f"background-color: {color_hex}; border-radius: 10px; padding: 2px 8px;"
            )
        if hasattr(self, "sync_state_hint"):
            self.sync_state_hint.setText(hint)

    def retry_sync_conflicts(self) -> None:
        if self._is_read_only_mode():
            QtWidgets.QMessageBox.warning(self, "Nur-Lesen Modus", "Konflikt-Retry ist nur mit Schreibzugriff moeglich.")
            return
        if not hasattr(self.db, "requeue_sync_outbox_conflicts"):
            QtWidgets.QMessageBox.warning(self, "Nicht verfuegbar", "Retry-Funktion ist in diesem Build nicht verfuegbar.")
            return
        try:
            moved = int(self.db.requeue_sync_outbox_conflicts(limit=200))
            self.refresh_sync_status()
            self._toast(f"{moved} Konflikt(e) in Retry verschoben.", "info")
            if moved > 0:
                self.trigger_sync_now()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Fehler", f"Konflikte konnten nicht in Retry verschoben werden:\n{exc}")

    def trigger_sync_now(self) -> None:
        host = self.window()
        if hasattr(host, "_run_sync_cycle"):
            try:
                host._run_sync_cycle()
                self.refresh_sync_status()
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Sync", f"Sync-Lauf konnte nicht gestartet werden:\n{exc}")
        else:
            QtWidgets.QMessageBox.information(self, "Sync", "Sync-Service ist in diesem Fenster nicht verfuegbar.")

    def browse_backup_folder(self):
        """Backup-Ordner auswählen"""
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Backup-Ordner auswählen", self.backup_path_input.text()
        )
        if folder:
            self.backup_path_input.setText(folder)

    def create_backup(self):
        """Erstellt ein Backup der Datenbank - INKL. WAL!"""
        if self._is_read_only_mode():
            QtWidgets.QMessageBox.warning(self, "Nur-Lesen Modus", "Backup erstellen ist nur mit Schreibzugriff möglich.")
            return
        backup_dir = self.backup_path_input.text().strip()

        if not backup_dir:
            QtWidgets.QMessageBox.warning(self, "Fehler", "Bitte einen Backup-Ordner angeben.")
            return

        try:
            # ✅ 1. WAL-Checkpoint: Alle Änderungen in Hauptdatei schreiben
            try:
                self.db.cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                self.db.conn.commit()
                print("WAL-Checkpoint durchgeführt")
            except Exception as e:
                print(f"⚠ WAL-Checkpoint Warnung: {e}")

            # ✅ 2. Ordner erstellen
            os.makedirs(backup_dir, exist_ok=True)

            # ✅ 3. Zeitstempel
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.db"
            backup_path = os.path.join(backup_dir, backup_filename)

            # ✅ 4. Backup erstellen (nur .db, da WAL bereits gemergt ist)
            shutil.copy2(self.db.path, backup_path)

            # ✅ 5. Backup verifizieren
            if self._verify_backup(backup_path):
                print(f"Backup erstellt und verifiziert: {backup_path}")

                # ✅ 6. Alte Backups aufräumen (max. 10 behalten)
                self._rotate_backups(backup_dir)

                # ✅ 7. Erfolg!
                filesize_kb = os.path.getsize(backup_path) / 1024
                QtWidgets.QMessageBox.information(
                    self,
                    "✅ Backup erstellt",
                    f"Backup erfolgreich erstellt:\n\n{backup_path}\n\n"
                    f"Dateigröße: {filesize_kb:.1f} KB"
                )
                self._toast("Backup erfolgreich erstellt.", "success")
            else:
                # Fehlerhaftes Backup löschen
                os.remove(backup_path)
                QtWidgets.QMessageBox.warning(
                    self, "Warnung",
                    "Backup wurde erstellt, aber die Verifikation ist fehlgeschlagen.\n"
                    "Das Backup wurde nicht gespeichert."
                )

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Fehler", f"Backup konnte nicht erstellt werden:\n\n{str(e)}"
            )
            print(f"✗ Backup-Fehler: {e}")
            import traceback
            traceback.print_exc()

    def browse_restore_file(self):
        """Backup-Datei zum Wiederherstellen auswählen"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Backup-Datei auswählen",
            self.backup_path_input.text(),
            "Datenbank-Dateien (*.db);;Alle Dateien (*)"
        )

        if file_path:
            self.restore_path_input.setText(file_path)
            self.btn_restore_backup.setEnabled(True)

    def restore_backup(self):
        """Backup zurückspielen - OHNE Dateien zu löschen (überschreiben stattdessen)

        Issue #7: Die schwere Arbeit (WAL-Checkpoint, File-Copy, Verifikation)
        läuft im UI-Thread, aber ``time.sleep`` wurde durch ``QApplication.
        processEvents()``-Polling ersetzt, damit die UI responsive bleibt.
        Für eine vollständige Auslagerung in einen Worker-Thread siehe
        ``BackupRestoreRunner`` (core/backup_worker.py) — das ist der
        Migrationspfad, falls der Restore jemals >5 Sekunden braucht.
        """
        if self._is_read_only_mode():
            QtWidgets.QMessageBox.warning(self, "Nur-Lesen Modus", "Backup-Wiederherstellung ist nur mit Schreibzugriff möglich.")
            return
        restore_file = self.restore_path_input.text().strip()

        if not restore_file or not os.path.exists(restore_file):
            QtWidgets.QMessageBox.warning(self, "Fehler", "Bitte eine gültige Backup-Datei auswählen.")
            return

        # Backup-Info anzeigen
        backup_size = os.path.getsize(restore_file) / 1024
        backup_time = datetime.fromtimestamp(os.path.getmtime(restore_file))
        current_size = os.path.getsize(self.db.path) / 1024

        # Backup verifizieren
        backup_verified = self._verify_backup(restore_file)
        verify_text = "Verifiziert" if backup_verified else "⚠ Nicht verifiziert (möglicherweise beschädigt)"

        if not backup_verified:
            reply = QtWidgets.QMessageBox.warning(
                self,
                "Warnung",
                "Die Backup-Datei konnte nicht verifiziert werden.\n"
                "Möglicherweise ist sie beschädigt.\n\n"
                "Trotzdem fortfahren?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

        # Bestätigung anfordern
        info_msg = (
            f"ACHTUNG: Alle aktuellen Daten werden überschrieben!\n\n"
            f"Backup-Datei: {os.path.basename(restore_file)}\n"
            f"Backup-Datum: {backup_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Backup-Größe: {backup_size:.1f} KB\n"
            f"Status: {verify_text}\n\n"
            f"Aktuelle DB-Größe: {current_size:.1f} KB\n\n"
            f"Ein Notfall-Backup wird vor dem Restore erstellt.\n\n"
            f"Möchten Sie fortfahren?"
        )

        reply = QtWidgets.QMessageBox.question(
            self,
            "Backup wiederherstellen",
            info_msg,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        emergency_backup = None

        try:
            logger.info("=" * 50)
            logger.info("BACKUP-WIEDERHERSTELLUNG GESTARTET")
            logger.info("=" * 50)

            # 1. WAL-Checkpoint
            logger.info("1. WAL-Checkpoint wird durchgeführt...")
            try:
                result = self.db.cur.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
                logger.info("   WAL-Checkpoint: %s", result)
                self.db.conn.commit()
            except Exception as e:
                logger.warning("   WAL-Checkpoint Fehler: %s", e)

            # 2. Cursor und Connection explizit schließen
            logger.info("2. Datenbank wird geschlossen...")
            try:
                if hasattr(self.db, 'cur') and self.db.cur:
                    self.db.cur.close()
                    self.db.cur = None
                    logger.info("   Cursor geschlossen")
            except Exception as e:
                logger.warning("   Cursor-Fehler: %s", e)

            try:
                if hasattr(self.db, 'conn') and self.db.conn:
                    self.db.conn.close()
                    self.db.conn = None
                    logger.info("   Connection geschlossen")
            except Exception as e:
                logger.warning("   Connection-Fehler: %s", e)

            # 3. Garbage Collection erzwingen
            import gc
            gc.collect()
            logger.info("   Garbage Collection durchgeführt")

            # 4. Pause für Windows File-System — ABER UI-responsive via processEvents
            logger.info("3. Warte auf File-System-Freigabe...")
            self._busy_sleep(2.0)  # 2 Sek warten, aber UI verarbeitet Events

            # 5. Notfall-Backup der aktuellen DB erstellen
            logger.info("4. Notfall-Backup wird erstellt...")
            emergency_backup = self.db.path + ".before_restore"
            if os.path.exists(self.db.path):
                # Altes Notfall-Backup löschen falls vorhanden
                if os.path.exists(emergency_backup):
                    try:
                        os.remove(emergency_backup)
                    except Exception as exc:
                        logger.warning("   Konnte altes Notfall-Backup nicht löschen: %s", exc)
                shutil.copy2(self.db.path, emergency_backup)
                logger.info("   Gesichert nach: %s", emergency_backup)

            # 6. WAL/SHM-Dateien löschen (diese MÜSSEN weg)
            logger.info("5. WAL/SHM-Dateien werden gelöscht...")
            wal_file = self.db.path + "-wal"
            shm_file = self.db.path + "-shm"
            journal_file = self.db.path + "-journal"

            for db_file in [wal_file, shm_file, journal_file]:
                if os.path.exists(db_file):
                    _deleted = False
                    for attempt in range(5):
                        try:
                            os.remove(db_file)
                            logger.info("   Gelöscht: %s", os.path.basename(db_file))
                            _deleted = True
                            break
                        except PermissionError:
                            if attempt < 4:
                                logger.warning("   Versuch %d/5: Warte...", attempt + 1)
                                self._busy_sleep(1.0)
                            else:
                                logger.warning(
                                    "   Konnte nicht gelöscht werden (wird beim Restore überschrieben): %s",
                                    os.path.basename(db_file),
                                )
                        except Exception as e:
                            logger.warning("   Fehler: %s", e)
                            break

            # 7. Hauptdatenbank ÜBERSCHREIBEN (nicht löschen!)
            logger.info("6. Backup wird wiederhergestellt (überschreibt alte Datei)...")

            # Mehrere Versuche zum Überschreiben
            restored = False
            restored_size = 0.0
            for attempt in range(10):
                try:
                    shutil.copy2(restore_file, self.db.path)
                    restored_size = os.path.getsize(self.db.path) / 1024
                    logger.info("   Wiederhergestellt: %.1f KB", restored_size)
                    restored = True
                    break
                except PermissionError:
                    if attempt < 9:
                        logger.warning("   Versuch %d/10: Datei noch gesperrt, warte...", attempt + 1)
                        self._busy_sleep(1.0)
                    else:
                        raise Exception("Datei konnte nach 10 Versuchen nicht überschrieben werden!")
                except Exception as e:
                    raise Exception(f"Fehler beim Überschreiben: {e}")

            if not restored:
                raise Exception("Restore fehlgeschlagen!")

            # 8. Verifizieren
            logger.info("7. Überprüfung...")
            if os.path.exists(self.db.path):
                logger.info("   Datei existiert: %s", self.db.path)
                if self._verify_backup(self.db.path):
                    logger.info("   Datenbank-Integrität OK")
                else:
                    logger.warning("   Integritäts-Check fehlgeschlagen")
            else:
                raise Exception("Wiederhergestellte Datei existiert nicht!")

            logger.info("=" * 50)
            logger.info("BACKUP-WIEDERHERSTELLUNG ABGESCHLOSSEN")
            logger.info("=" * 50)

            QtWidgets.QMessageBox.information(
                self,
                "✅ Wiederherstellung erfolgreich",
                f"Das Backup wurde erfolgreich wiederhergestellt.\n\n"
                f"Wiederhergestellt: {restored_size:.1f} KB\n"
                f"Original Backup: {backup_size:.1f} KB\n\n"
                f"Notfall-Backup: {emergency_backup}\n\n"
                f"Die Anwendung wird jetzt neu gestartet."
            )
            self._toast("Backup erfolgreich wiederhergestellt.", "success")

            # 9. Anwendung neu starten (im UI-Thread — Worker kann den Prozess nicht ersetzen)
            self.close()
            QtWidgets.QApplication.quit()
            os.execl(sys.executable, sys.executable, *sys.argv)  # nosec B606: self-restart without shell

        except Exception as e:
            logger.exception("FEHLER beim Restore: %s", e)

            # Bei Fehler: Datenbank wieder öffnen versuchen
            try:
                self.db.conn = sqlite3.connect(self.db.path, check_same_thread=False)
                self.db.cur = self.db.conn.cursor()
                logger.info("   Datenbankverbindung wiederhergestellt")
            except Exception as reconn_err:
                logger.error("   Verbindung konnte nicht wiederhergestellt werden: %s", reconn_err)

            error_msg = f"Backup-Wiederherstellung fehlgeschlagen:\n\n{str(e)}"
            if emergency_backup:
                error_msg += f"\n\nDie ursprüngliche Datenbank wurde gesichert unter:\n{emergency_backup}"
            error_msg += "\n\nPrüfen Sie die Konsole für Details!"

            QtWidgets.QMessageBox.critical(self, "❌ Fehler", error_msg)

    def _busy_sleep(self, seconds: float) -> None:
        """Schläft ``seconds`` Sekunden, lässt aber die UI-Event-Queue weiterlaufen.

        Issue #7: ``time.sleep`` blockiert den UI-Thread komplett. Diese
        Methode ist der minimal-invasive Fix: 50ms-Intervalle, in denen
        ``QApplication.processEvents()`` aufgerufen wird. Klicks und
        Repaints werden weiterhin verarbeitet.

        Für echte Async-Migration siehe ``core/backup_worker.py``.
        """
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            time.sleep(seconds)
            return
        elapsed = 0.0
        interval = 0.05
        while elapsed < seconds:
            app.processEvents()
            time.sleep(interval)
            elapsed += interval

    def _verify_backup(self, backup_path):
        """Verifiziert die Integrität einer Backup-Datei"""
        try:
            import sqlite3
            conn = sqlite3.connect(backup_path, timeout=10)
            result = conn.cursor().execute("PRAGMA integrity_check").fetchone()
            conn.close()
            return result[0] == "ok"
        except Exception as e:
            print(f"⚠ Backup-Verifikation fehlgeschlagen: {e}")
            return False

    def _rotate_backups(self, backup_dir, max_backups=10):
        """Löscht alte Backups, behält nur die neuesten"""
        try:
            # Alle backup_*.db Dateien finden
            import glob
            backups = glob.glob(os.path.join(backup_dir, "backup_*.db"))

            # Nach Änderungsdatum sortieren (neueste zuerst)
            backups.sort(key=lambda x: os.path.getmtime(x), reverse=True)

            # Alte Backups löschen
            deleted_count = 0
            for old_backup in backups[max_backups:]:
                try:
                    os.remove(old_backup)
                    deleted_count += 1
                    print(f"   Altes Backup gelöscht: {os.path.basename(old_backup)}")
                except Exception as e:
                    print(f"   ⚠ Konnte {os.path.basename(old_backup)} nicht löschen: {e}")

            if deleted_count > 0:
                print(f"   {deleted_count} alte(s) Backup(s) gelöscht")

        except Exception as e:
            print(f"⚠ Backup-Rotation fehlgeschlagen: {e}")

    def check_auto_backup(self):
        """Prüft und erstellt automatisches Backup beim Start"""
        if self._is_read_only_mode():
            return
        if not self.load_auto_backup_setting():
            print("Auto-Backup ist deaktiviert")
            return

        try:
            # Prüfen, ob heute bereits ein Backup erstellt wurde
            result = self.db.cur.execute(
                "SELECT wert FROM einstellungen WHERE schluessel = 'letztes_backup'"
            ).fetchone()

            heute = datetime.now().strftime("%Y-%m-%d")

            if result and result[0] == heute:
                print(f"Heute bereits ein Backup erstellt: {heute}")
                return

            # Auto-Backup erstellen
            backup_dir = self.get_default_backup_path()
            os.makedirs(backup_dir, exist_ok=True)

            # WAL-Checkpoint
            try:
                self.db.cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                self.db.conn.commit()
            except Exception as exc:
                print(f"WAL-Checkpoint fehlgeschlagen (ignoriert): {exc}")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"auto_backup_{timestamp}.db"
            backup_path = os.path.join(backup_dir, backup_filename)

            shutil.copy2(self.db.path, backup_path)

            # Datum speichern
            self.db.cur.execute("""
                INSERT OR REPLACE INTO einstellungen (schluessel, wert)
                VALUES ('letztes_backup', ?)
            """, (heute,))
            self.db.conn.commit()

            print(f"✅ Auto-Backup erstellt: {backup_path}")

            # Alte Auto-Backups aufräumen
            self._rotate_backups(backup_dir, max_backups=10)

        except Exception as e:
            print(f"Auto-Backup fehlgeschlagen: {e}")

    def load_auto_backup_setting(self):
        """Lädt die Auto-Backup-Einstellung"""
        try:
            result = self.db.cur.execute(
                "SELECT wert FROM einstellungen WHERE schluessel = 'auto_backup'"
            ).fetchone()

            if result:
                return result[0] == '1'
            return False
        except Exception as e:
            print(f"Fehler beim Laden der Auto-Backup-Einstellung: {e}")
            return False

    def save_auto_backup_setting_from_bool(self, checked):
        """Speichert die Auto-Backup-Einstellung (über toggled-Signal)"""
        if self._is_read_only_mode():
            return
        try:
            self.db.cur.execute("""
                INSERT OR REPLACE INTO einstellungen (schluessel, wert)
                VALUES ('auto_backup', ?)
            """, ('1' if checked else '0',))
            self.db.conn.commit()

            print(f"✅ Auto-Backup gespeichert: {'aktiviert' if checked else 'deaktiviert'}")
        except Exception as e:
            print(f"❌ Fehler beim Speichern: {e}")

    def create_security_tab(self):
            """Erstellt den Sicherheits-Info-Tab"""
            tab = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(tab)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(20)

            # Info-Card
            info_card = create_card_widget()
            info_layout = QtWidgets.QVBoxLayout(info_card)

            _c = AppleTheme.current_colors()
            info_title = QtWidgets.QLabel("🔐 Sicherheitsinformationen")
            info_title.setStyleSheet(
                f"font-size: 16px; font-weight: 600; color: {_c['label']}; margin-bottom: 8px;"
            )
            info_layout.addWidget(info_title)

            info_text = QtWidgets.QLabel(
                "Diese Anwendung ist durch ein rollenbasiertes Login-System geschützt.\n\n"
                "• Administrator: Voller Zugriff auf alle Funktionen\n"
                "• Benutzer: Zugriff auf Depots und Bewegungen\n\n"
                "Passwort ändern: Verwenden Sie den Button 'Passwort ändern' "
                "in der Sidebar.\n\n"
                "Benutzerverwaltung: Nur für Administratoren über '👥 Benutzerverwaltung' "
                "in der Sidebar verfügbar."
            )
            info_text.setStyleSheet(
                f"color: {_c['secondary_label']}; font-size: 13px; line-height: 1.8;"
            )
            info_text.setWordWrap(True)
            info_layout.addWidget(info_text)

            layout.addWidget(info_card)
            layout.addStretch()

            return tab

    def update_password_strength(self):
        """Aktualisiert die Anzeige der Passwortstärke"""
        password = self.new_password_input.text()

        if not password:
            self.password_strength_label.setText("Passwortstärke: -")
            tc = AppleTheme.current_colors()
            self.password_strength_label.setStyleSheet(
                f"color: {tc['tertiary_label']}; font-size: 12px;"
            )
            return

        # Berechne Stärke
        strength = 0
        feedback = []

        if len(password) >= 8:
            strength += 1
        else:
            feedback.append("mind. 8 Zeichen")

        if any(c.isupper() for c in password):
            strength += 1
        else:
            feedback.append("Großbuchstaben")

        if any(c.islower() for c in password):
            strength += 1
        else:
            feedback.append("Kleinbuchstaben")

        if any(c.isdigit() for c in password):
            strength += 1
        else:
            feedback.append("Zahlen")

        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            strength += 1
        else:
            feedback.append("Sonderzeichen")

        tc = AppleTheme.current_colors()
        # Anzeige basierend auf Stärke
        if strength <= 2:
            label = "Schwach"
            color = tc["red"]
            if feedback:
                label += f" (fehlt: {', '.join(feedback)})"
        elif strength == 3:
            label = "Mittel"
            color = tc["orange"]
        elif strength == 4:
            label = "Gut"
            color = tc["blue"]
        else:
            label = "Sehr stark"
            color = tc["green"]

        self.password_strength_label.setText(f"Passwortstärke: {label}")
        self.password_strength_label.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: 600;"
        )

    def toggle_password_visibility(self, checked):
        """Schaltet die Sichtbarkeit der Passwort-Felder um"""
        mode = QtWidgets.QLineEdit.Normal if checked else QtWidgets.QLineEdit.Password
        self.current_password_input.setEchoMode(mode)
        self.new_password_input.setEchoMode(mode)
        self.confirm_password_input.setEchoMode(mode)

    def change_password(self):
        """Ändert das Passwort für die Grundeinstellungen"""
        current = self.current_password_input.text()
        new = self.new_password_input.text()
        confirm = self.confirm_password_input.text()

        # Validierung
        if not current or not new or not confirm:
            QtWidgets.QMessageBox.warning(
                self,
                "Fehlende Eingabe",
                "Bitte füllen Sie alle Felder aus."
            )
            return

        # Aktuelles Passwort prüfen (nur wenn bereits eines gesetzt ist)
        stored_hash = self.load_password_hash()
        if stored_hash and not SecurityManager.verify_password(current, stored_hash):
            QtWidgets.QMessageBox.warning(
                self,
                "Falsches Passwort",
                "Das eingegebene aktuelle Passwort ist nicht korrekt."
            )
            return

        # Neues Passwort validieren
        if len(new) < 4:
            QtWidgets.QMessageBox.warning(
                self,
                "Passwort zu kurz",
                "Das neue Passwort muss mindestens 4 Zeichen lang sein.\n"
                "Empfohlen sind mindestens 8 Zeichen."
            )
            return

        if new != confirm:
            QtWidgets.QMessageBox.warning(
                self,
                "Passwörter stimmen nicht überein",
                "Das neue Passwort und die Wiederholung stimmen nicht überein."
            )
            return

        # Warnung bei schwachem Passwort
        if len(new) < 8:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Schwaches Passwort",
                "Das gewählte Passwort ist relativ kurz.\n"
                "Empfohlen sind mindestens 8 Zeichen.\n\n"
                "Möchten Sie trotzdem fortfahren?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

        # Passwort speichern
        try:
            new_hash = SecurityManager.hash_password(new)
            self.save_password_hash(new_hash)

            QtWidgets.QMessageBox.information(
                self,
                "Passwort geändert",
                "Das Passwort wurde erfolgreich geändert.\n\n"
                "Notieren Sie sich das neue Passwort an einem sicheren Ort!"
            )
            self._toast("Passwort gespeichert.", "success")

            # Felder leeren
            self.current_password_input.clear()
            self.new_password_input.clear()
            self.confirm_password_input.clear()
            self.password_strength_label.setText("Passwortstärke: -")
            tc = AppleTheme.current_colors()
            self.password_strength_label.setStyleSheet(
                f"color: {tc['tertiary_label']}; font-size: 12px;"
            )

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Fehler",
                f"Das Passwort konnte nicht gespeichert werden:\n{e}"
            )

    def load_password_hash(self):
        """Lädt den Passwort-Hash aus der Datenbank"""
        try:
            row = self.db.cur.execute(
                "SELECT wert FROM einstellungen WHERE schluessel = ?",
                (DB.SETTING_PASSWORD_HASH,)
            ).fetchone()
            return row[0] if row else None
        except Exception:
            return None

    def save_password_hash(self, password_hash):
        """Speichert den Passwort-Hash in der Datenbank"""
        self.db.cur.execute(
            "INSERT OR REPLACE INTO einstellungen (schluessel, wert) VALUES (?, ?)",
            (DB.SETTING_PASSWORD_HASH, password_hash)
        )
        self.db.conn.commit()


# # =============================================================================
