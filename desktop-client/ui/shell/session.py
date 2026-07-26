"""MainWindow shell helpers (Issue #93)."""
from __future__ import annotations

import logging

from apple_theme import AppleTheme
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from ui.dialogs.embedded_dialog_host import exec_embedded_dialog
from ui.shell.constants import PageIndex

logger = logging.getLogger("ND-Hub")

def _setup_integrated_login(self) -> None:
    """Login als Overlay im Hauptfenster statt separatem Fenster."""
    self._login_attempts = 0
    self.login_overlay = QtWidgets.QWidget(self)
    self.login_overlay.setObjectName("login_overlay")

    overlay_layout = QtWidgets.QVBoxLayout(self.login_overlay)
    overlay_layout.setContentsMargins(24, 24, 24, 24)
    overlay_layout.addStretch()

    self._login_card_frame = QtWidgets.QFrame()
    self._login_card_frame.setObjectName("login_card")
    self._login_card_frame.setMaximumWidth(560)
    self._login_card_frame.setMinimumWidth(500)
    card_layout = QtWidgets.QVBoxLayout(self._login_card_frame)
    card_layout.setSpacing(14)

    self._login_title_label = QtWidgets.QLabel("Willkommen bei ND-Hub")
    card_layout.addWidget(self._login_title_label)

    self._login_subtitle_label = QtWidgets.QLabel(
        "Melden Sie sich mit Ihrem Benutzerkonto an, um "
        "Bestände, Bewegungen und Auswertungen sicher zu verwalten."
    )
    self._login_subtitle_label.setWordWrap(True)
    card_layout.addWidget(self._login_subtitle_label)

    self._login_hint_label = QtWidgets.QLabel(
        "Hinweis: Bei Problemen wenden Sie sich an einen Administrator."
    )
    self._login_hint_label.setWordWrap(True)
    card_layout.addWidget(self._login_hint_label)

    self.login_user_input = QtWidgets.QLineEdit()
    self.login_user_input.setPlaceholderText("Benutzername")
    self.login_user_input.setMinimumHeight(42)
    card_layout.addWidget(self.login_user_input)

    self.login_password_input = QtWidgets.QLineEdit()
    self.login_password_input.setPlaceholderText("Passwort")
    self.login_password_input.setEchoMode(QtWidgets.QLineEdit.Password)
    self.login_password_input.setMinimumHeight(42)
    card_layout.addWidget(self.login_password_input)

    self.login_error_label = QtWidgets.QLabel("")
    self.login_error_label.setWordWrap(True)
    card_layout.addWidget(self.login_error_label)

    self.login_submit_btn = QtWidgets.QPushButton("Anmelden")
    self.login_submit_btn.setObjectName("btn_save")
    self.login_submit_btn.setMinimumHeight(46)
    self.login_submit_btn.setDefault(True)
    self.login_submit_btn.setAutoDefault(True)
    card_layout.addWidget(self.login_submit_btn)

    overlay_layout.addWidget(self._login_card_frame, alignment=Qt.AlignHCenter)
    overlay_layout.addStretch()

    self.login_submit_btn.clicked.connect(self._perform_integrated_login)
    self.login_user_input.returnPressed.connect(self._perform_integrated_login)
    self.login_password_input.returnPressed.connect(self._perform_integrated_login)

    self._apply_chrome_overlay_styles()

    self.login_overlay.setGeometry(self.rect())
    self.login_overlay.raise_()
    self.login_overlay.show()
    self.login_user_input.setFocus()


def _perform_integrated_login(self) -> None:
    """Authentifiziert den Benutzer aus dem eingebetteten Login-Overlay."""
    username = self.login_user_input.text().strip()
    password = self.login_password_input.text()
    success, message = self.security.authenticate(username, password)

    if success:
        logger.info(
            "Benutzer '%s' angemeldet (Rolle: %s)",
            username,
            self.security.get_current_role(),
        )
        self.login_overlay.hide()
        self._handle_successful_login(username)
        self.show_toast(f"Willkommen, {username}.", "success")
        return

    self._login_attempts += 1
    remaining = 3 - self._login_attempts
    if remaining <= 0:
        QtWidgets.QMessageBox.critical(
            self,
            "Zugriff verweigert",
            "Maximale Anzahl an Anmeldeversuchen überschritten.",
        )
        QtWidgets.QApplication.quit()
        return

    self.login_error_label.setText(f"{message} Noch {remaining} Versuch(e) übrig.")
    self.login_password_input.clear()
    self.login_password_input.setFocus()


def _show_confirmation_overlay(
    self,
    title: str,
    message: str,
    confirm_text: str,
    on_confirm,
    cancel_text: str = "Abbrechen",
    confirm_object_name: str = "btn_save",
) -> None:
    """Zeigt eine integrierte Bestätigungsabfrage im Hauptfenster."""
    self._hide_confirmation_overlay()

    c = AppleTheme.current_colors()
    dim = "rgba(15, 23, 42, 200)" if AppleTheme.is_dark_mode else "rgba(15, 23, 42, 170)"

    self.confirm_overlay = QtWidgets.QWidget(self)
    self.confirm_overlay.setObjectName("confirm_overlay")
    self.confirm_overlay.setStyleSheet(
        f"QWidget#confirm_overlay {{ background-color: {dim}; }}"
    )
    self.confirm_overlay.setGeometry(self.rect())

    overlay_layout = QtWidgets.QVBoxLayout(self.confirm_overlay)
    overlay_layout.setContentsMargins(24, 24, 24, 24)
    overlay_layout.addStretch()

    card = QtWidgets.QFrame()
    card.setObjectName("confirm_card")
    card.setMaximumWidth(480)
    card.setStyleSheet(
        f"QFrame#confirm_card {{"
        f"background-color: {c['bg_secondary']};"
        f"border: 1px solid {c['separator']};"
        f"border-radius: 12px;"
        f"padding: 20px;"
        f"}}"
    )
    card_layout = QtWidgets.QVBoxLayout(card)
    card_layout.setSpacing(12)

    title_label = QtWidgets.QLabel(title)
    title_label.setStyleSheet(
        f"font-size: 20px; font-weight: 700; color: {c['label']}; background: transparent;"
    )
    card_layout.addWidget(title_label)

    message_label = QtWidgets.QLabel(message)
    message_label.setWordWrap(True)
    message_label.setStyleSheet(
        f"font-size: 13px; color: {c['secondary_label']}; background: transparent;"
    )
    card_layout.addWidget(message_label)

    button_row = QtWidgets.QHBoxLayout()
    button_row.addStretch()

    cancel_btn = QtWidgets.QPushButton(cancel_text)
    cancel_btn.setObjectName("btn_secondary")
    cancel_btn.setMinimumHeight(40)
    cancel_btn.clicked.connect(self._hide_confirmation_overlay)
    button_row.addWidget(cancel_btn)

    confirm_btn = QtWidgets.QPushButton(confirm_text)
    confirm_btn.setObjectName(confirm_object_name)
    confirm_btn.setMinimumHeight(40)

    def _confirm_and_close():
        self._hide_confirmation_overlay()
        on_confirm()

    confirm_btn.clicked.connect(_confirm_and_close)
    button_row.addWidget(confirm_btn)
    card_layout.addLayout(button_row)

    overlay_layout.addWidget(card, alignment=Qt.AlignHCenter)
    overlay_layout.addStretch()

    self.confirm_overlay.raise_()
    self.confirm_overlay.show()


def _hide_confirmation_overlay(self) -> None:
    if hasattr(self, "confirm_overlay") and self.confirm_overlay is not None:
        self.confirm_overlay.hide()
        self.confirm_overlay.deleteLater()
        self.confirm_overlay = None


def _show_logout_choice_overlay(self) -> None:
    """Zeigt die Auswahl zwischen Benutzerwechsel und Beenden."""
    self._hide_confirmation_overlay()

    c = AppleTheme.current_colors()
    dim = "rgba(15, 23, 42, 200)" if AppleTheme.is_dark_mode else "rgba(15, 23, 42, 170)"

    self.confirm_overlay = QtWidgets.QWidget(self)
    self.confirm_overlay.setObjectName("confirm_overlay")
    self.confirm_overlay.setStyleSheet(
        f"QWidget#confirm_overlay {{ background-color: {dim}; }}"
    )
    self.confirm_overlay.setGeometry(self.rect())

    overlay_layout = QtWidgets.QVBoxLayout(self.confirm_overlay)
    overlay_layout.setContentsMargins(24, 24, 24, 24)
    overlay_layout.addStretch()

    card = QtWidgets.QFrame()
    card.setObjectName("confirm_card")
    card.setMaximumWidth(520)
    card.setStyleSheet(
        f"QFrame#confirm_card {{"
        f"background-color: {c['bg_secondary']};"
        f"border: 1px solid {c['separator']};"
        f"border-radius: 12px;"
        f"padding: 20px;"
        f"}}"
    )
    card_layout = QtWidgets.QVBoxLayout(card)
    card_layout.setSpacing(12)

    title_label = QtWidgets.QLabel("Abmelden")
    title_label.setStyleSheet(
        f"font-size: 20px; font-weight: 700; color: {c['label']}; background: transparent;"
    )
    card_layout.addWidget(title_label)

    message_label = QtWidgets.QLabel(
        "Möchten Sie den Benutzer wechseln oder das Programm beenden?"
    )
    message_label.setWordWrap(True)
    message_label.setStyleSheet(
        f"font-size: 13px; color: {c['secondary_label']}; background: transparent;"
    )
    card_layout.addWidget(message_label)

    button_row = QtWidgets.QHBoxLayout()
    button_row.addStretch()

    cancel_btn = QtWidgets.QPushButton("Abbrechen")
    cancel_btn.setObjectName("btn_secondary")
    cancel_btn.setMinimumHeight(40)
    cancel_btn.clicked.connect(self._hide_confirmation_overlay)
    button_row.addWidget(cancel_btn)

    switch_btn = QtWidgets.QPushButton("Benutzer wechseln")
    switch_btn.setObjectName("btn_save")
    switch_btn.setMinimumHeight(40)
    switch_btn.clicked.connect(self._execute_user_switch)
    button_row.addWidget(switch_btn)

    quit_btn = QtWidgets.QPushButton("Programm beenden")
    quit_btn.setObjectName("btn_delete")
    quit_btn.setMinimumHeight(40)
    quit_btn.clicked.connect(self._confirm_close)
    button_row.addWidget(quit_btn)

    card_layout.addLayout(button_row)
    overlay_layout.addWidget(card, alignment=Qt.AlignHCenter)
    overlay_layout.addStretch()

    self.confirm_overlay.raise_()
    self.confirm_overlay.show()

# ============================================================
# EVENT HANDLERS
# ============================================================

def change_user_password(self) -> None:
    """Öffnet Dialog zum Passwort-Ändern"""
    if hasattr(self, "db") and self.db.is_read_only_mode():
        QtWidgets.QMessageBox.warning(self, "Nur-Lesen Modus", "Passwortänderung ist im Nur-Lesen Modus nicht möglich.")
        return
    from ui.dialogs.login_dialog import ChangePasswordDialog

    user_id = self.security.get_current_user_id()
    username = self.security.get_current_user()

    dialog = ChangePasswordDialog(username, self)
    accepted = exec_embedded_dialog(self, dialog) == QtWidgets.QDialog.Accepted
    if not accepted:
        dialog.deleteLater()
        return

    # Passwörter SOFORT lesen (Dialog ist vom Overlay entkoppelt).
    # Keine nested Dialoge im selben Call-Stack wie der gerade
    # geschlossene Embedded-Dialog (beobachteter Exit-139-Crash).
    try:
        old_pw, new_pw = dialog.get_passwords()
    finally:
        dialog.deleteLater()

    success, message = self.security.change_password(user_id, old_pw, new_pw)

    def _feedback(ok=success, msg=message):
        if ok:
            detail = msg + "\n\nIhr neues Passwort wurde gespeichert."
            QtWidgets.QMessageBox.information(self, "Erfolg", detail)
            self.show_toast("Passwort erfolgreich geändert.", "success")
        else:
            QtWidgets.QMessageBox.warning(self, "Fehler", msg)

    QtCore.QTimer.singleShot(0, _feedback)


def change_user_avatar(self) -> None:
    """Erlaubt dem Benutzer, ein Profilbild zu setzen."""
    if hasattr(self, "db") and self.db.is_read_only_mode():
        QtWidgets.QMessageBox.warning(self, "Nur-Lesen Modus", "Profilbild kann im Nur-Lesen Modus nicht geändert werden.")
        return
    user_id = self.security.get_current_user_id()
    if not user_id:
        return
    file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
        self,
        "Profilbild auswählen",
        "",
        "Bilder (*.png *.jpg *.jpeg *.webp *.bmp)",
    )
    if not file_path:
        return
    success, message = self.security.set_user_avatar(user_id, file_path)
    if success:
        self._update_user_avatar_display()
        QtWidgets.QMessageBox.information(self, "Profilbild", message)
        self.show_toast("Profilbild aktualisiert.", "success")
    else:
        QtWidgets.QMessageBox.warning(self, "Profilbild", message)


def remove_user_avatar(self) -> None:
    """Entfernt das Profilbild des aktuellen Benutzers."""
    if hasattr(self, "db") and self.db.is_read_only_mode():
        QtWidgets.QMessageBox.warning(self, "Nur-Lesen Modus", "Profilbild kann im Nur-Lesen Modus nicht entfernt werden.")
        return
    user_id = self.security.get_current_user_id()
    if not user_id:
        return
    success, message = self.security.clear_user_avatar(user_id)
    if success:
        self._update_user_avatar_display()
        QtWidgets.QMessageBox.information(self, "Profilbild", message)
        self.show_toast("Profilbild entfernt.", "success")
    else:
        QtWidgets.QMessageBox.warning(self, "Profilbild", message)


def open_user_management(self) -> None:
    """Öffnet integrierte Benutzerverwaltung in den Grundeinstellungen."""

    if not self.security.is_admin():
        QtWidgets.QMessageBox.warning(
            self,
            "Keine Berechtigung",
            "Nur Administratoren können auf die Benutzerverwaltung zugreifen."
        )
        return

    self.switch_to_page(PageIndex.GRUNDEINSTELLUNGEN)
    if not getattr(self, "page_grundeinstellungen", None):
        return

    tabs = getattr(self.page_grundeinstellungen, "tabs", None)
    if not tabs:
        return

    for idx in range(tabs.count()):
        if tabs.tabText(idx) == "Benutzer":
            tabs.setCurrentIndex(idx)
            return


def force_logout(self) -> None:
    """Meldet den Benutzer sofort ab und beendet die App (Zwang)"""
    username = self.security.get_current_user()
    if hasattr(self, "db"):
        self.db.release_write_lease()
    self.security.logout()
    logger.warning(f"Benutzer '{username}' zwangsabgemeldet (Zwingende Passwort-Richtlinie)")
    QtWidgets.QApplication.quit()


def _execute_logout(self) -> None:
    username = self.security.get_current_user()
    if hasattr(self, "db"):
        self.db.release_write_lease()
    self.security.logout()
    logger.info(f"Benutzer '{username}' abgemeldet")
    QtWidgets.QApplication.quit()


def _execute_user_switch(self) -> None:
    """Meldet aktuellen Benutzer ab und zeigt den Login-Screen."""
    username = self.security.get_current_user()
    if hasattr(self, "db"):
        self.db.release_write_lease()
    self.security.logout()
    logger.info(f"Benutzer '{username}' abgemeldet (Benutzerwechsel)")

    self._hide_confirmation_overlay()
    self._refresh_user_sidebar_state()
    self.switch_to_page(PageIndex.DASHBOARD)

    self._login_attempts = 0
    if hasattr(self, "login_user_input"):
        self.login_user_input.clear()
    if hasattr(self, "login_password_input"):
        self.login_password_input.clear()
    if hasattr(self, "login_error_label"):
        self.login_error_label.clear()

    if hasattr(self, "login_overlay"):
        self.login_overlay.setGeometry(self.rect())
        self.login_overlay.raise_()
        self.login_overlay.show()
    if hasattr(self, "login_user_input"):
        self.login_user_input.setFocus()


def logout(self) -> None:
    """Zeigt Auswahl für Benutzerwechsel oder Programmende."""
    current_page = self.stack.currentWidget() if hasattr(self, "stack") else None
    if current_page is not None and not self._confirm_discard_unsaved_changes(current_page):
        return
    self._show_logout_choice_overlay()


def closeEvent(self, event: QtGui.QCloseEvent) -> None:
    """Cleanup beim Schließen"""
    if getattr(self, "_allow_close", False):
        if hasattr(self, 'verfallmanager'):
            self.verfallmanager.close()
        if hasattr(self, "db"):
            self.db.release_write_lease()
        if hasattr(self, 'security'):
            self.security.logout()
            self.security.close()
        event.accept()
        return

    current_page = self.stack.currentWidget() if hasattr(self, "stack") else None
    if current_page is not None and not self._confirm_discard_unsaved_changes(current_page):
        event.ignore()
        return

    event.ignore()
    self._show_confirmation_overlay(
        title="Beenden",
        message="Möchten Sie die Anwendung wirklich beenden?",
        confirm_text="Beenden",
        on_confirm=self._confirm_close,
        confirm_object_name="btn_delete",
    )


def _confirm_close(self) -> None:
    self._hide_confirmation_overlay()
    self._allow_close = True
    self.close()


def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
    super().resizeEvent(event)
    self._update_sidebar_width(event.size().width())
    self._update_feedback_layer_geometry()
    if hasattr(self, "login_overlay"):
        self.login_overlay.setGeometry(self.rect())
    if hasattr(self, "confirm_overlay") and self.confirm_overlay is not None:
        self.confirm_overlay.setGeometry(self.rect())


def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
    """ESC schließt nur den eingebetteten Bestätigungs-Overlay."""
    if event.key() == Qt.Key_Escape and hasattr(self, "confirm_overlay") and self.confirm_overlay:
        self._hide_confirmation_overlay()
        event.ignore()
        return
    super().keyPressEvent(event)


# =============================================================================
# Pages





# =============================================================================
# Import-Seite (verbessert mit Excel-Dropdowns)
# =============================================================================


# =============================================================================
# E-Mail-Seite
# =============================================================================


# =============================================================================

