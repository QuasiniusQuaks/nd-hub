"""Dialogs für Benutzerverwaltung (Add/Edit)."""
import re

from apple_theme import AppleTheme
from PySide6 import QtWidgets
from PySide6.QtCore import Qt

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AddUserDialog(QtWidgets.QDialog):
    def __init__(self, security_manager, parent=None):
        super().__init__(parent)
        self.security = security_manager
        self.setWindowTitle("Neuen Benutzer hinzufügen")
        self.setModal(True)
        self.setMinimumSize(480, 440)
        self._setup_ui()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        c = AppleTheme.current_colors()
        title = QtWidgets.QLabel("Neuen Benutzer erstellen")
        title.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {c['label']};")
        layout.addWidget(title)

        form = QtWidgets.QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self.username_input = QtWidgets.QLineEdit()
        self.username_input.setPlaceholderText("Eindeutiger Benutzername...")
        self.username_input.setMinimumHeight(36)
        form.addRow("Benutzername:", self.username_input)

        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setPlaceholderText("Passwort (mind. 8 Zeichen)...")
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password_input.setMinimumHeight(36)
        form.addRow("Passwort:", self.password_input)

        self.confirm_password_input = QtWidgets.QLineEdit()
        self.confirm_password_input.setPlaceholderText("Passwort wiederholen...")
        self.confirm_password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.confirm_password_input.setMinimumHeight(36)
        form.addRow("Bestätigung:", self.confirm_password_input)

        self.role_combo = QtWidgets.QComboBox()
        self.role_combo.addItems(["User", "Admin"])
        self.role_combo.setMinimumHeight(36)
        form.addRow("Rolle:", self.role_combo)

        self.email_input = QtWidgets.QLineEdit()
        self.email_input.setPlaceholderText("Optional...")
        self.email_input.setMinimumHeight(36)
        form.addRow("E-Mail:", self.email_input)

        layout.addLayout(form)

        info = QtWidgets.QLabel(
            "User: Kann Depots/Bewegungen verwalten\n"
            "Admin: Volle Rechte inkl. Benutzerverwaltung"
        )
        info.setStyleSheet(
            f"background-color: {c['bg_tertiary']}; padding: 10px; border-radius: 6px; "
            f"font-size: 12px; color: {c['secondary_label']};"
        )
        layout.addWidget(info)

        layout.addStretch()

        button_layout = QtWidgets.QHBoxLayout()
        self.btn_cancel = QtWidgets.QPushButton("Abbrechen")
        self.btn_cancel.setMinimumHeight(40)
        self.btn_cancel.setObjectName("btn_secondary")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_create = QtWidgets.QPushButton("Benutzer erstellen")
        self.btn_create.setMinimumHeight(40)
        self.btn_create.setObjectName("btn_add")
        self.btn_create.clicked.connect(self.accept)

        button_layout.addWidget(self.btn_cancel)
        button_layout.addWidget(self.btn_create)
        layout.addLayout(button_layout)

        self.username_input.setFocus()

    def get_user_data(self):
        return (
            self.username_input.text().strip(),
            self.password_input.text(),
            self.role_combo.currentText(),
            self.email_input.text().strip(),
        )

    def accept(self):
        username, password, _, _ = self.get_user_data()
        if not username:
            QtWidgets.QMessageBox.warning(self, "Fehler", "Bitte geben Sie einen Benutzernamen ein.")
            return
        if not password:
            QtWidgets.QMessageBox.warning(self, "Fehler", "Bitte geben Sie ein Passwort ein.")
            return
        if len(password) < 8:
            QtWidgets.QMessageBox.warning(self, "Fehler", "Das Passwort muss mindestens 8 Zeichen lang sein.")
            return
        if password != self.confirm_password_input.text():
            QtWidgets.QMessageBox.warning(self, "Fehler", "Die Passwörter stimmen nicht überein.")
            return
        email = self.email_input.text().strip()
        if email and not _EMAIL_RE.match(email):
            QtWidgets.QMessageBox.warning(self, "Fehler", "Bitte eine gültige E-Mail-Adresse eingeben.")
            return
        super().accept()


class EditUserDialog(QtWidgets.QDialog):
    def __init__(self, username, role, email, is_active, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Benutzer bearbeiten: {username}")
        self.setModal(True)
        self.setMinimumSize(480, 380)
        self._setup_ui(username, role, email, is_active)

    def _setup_ui(self, username, role, email, is_active):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        c = AppleTheme.current_colors()
        title = QtWidgets.QLabel(f"Bearbeiten: {username}")
        title.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {c['label']};")
        layout.addWidget(title)

        form = QtWidgets.QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self.username_input = QtWidgets.QLineEdit()
        self.username_input.setText(username)
        self.username_input.setMinimumHeight(36)
        form.addRow("Benutzername:", self.username_input)

        self.role_combo = QtWidgets.QComboBox()
        self.role_combo.addItems(["User", "Admin"])
        self.role_combo.setCurrentText(role)
        self.role_combo.setMinimumHeight(36)
        form.addRow("Rolle:", self.role_combo)

        self.email_input = QtWidgets.QLineEdit()
        self.email_input.setText(email)
        self.email_input.setMinimumHeight(36)
        form.addRow("E-Mail:", self.email_input)

        self.active_checkbox = QtWidgets.QCheckBox("Benutzer ist aktiv")
        self.active_checkbox.setChecked(is_active)
        form.addRow("Status:", self.active_checkbox)

        layout.addLayout(form)
        layout.addStretch()

        button_layout = QtWidgets.QHBoxLayout()
        self.btn_cancel = QtWidgets.QPushButton("Abbrechen")
        self.btn_cancel.setMinimumHeight(40)
        self.btn_cancel.setObjectName("btn_secondary")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QtWidgets.QPushButton("Änderungen speichern")
        self.btn_save.setMinimumHeight(40)
        self.btn_save.setObjectName("btn_save")
        self.btn_save.clicked.connect(self.accept)

        button_layout.addWidget(self.btn_cancel)
        button_layout.addWidget(self.btn_save)
        layout.addLayout(button_layout)

    def get_user_data(self):
        return (
            self.username_input.text().strip(),
            self.role_combo.currentText(),
            self.email_input.text().strip(),
            self.active_checkbox.isChecked(),
        )

    def accept(self):
        username, _, _, _ = self.get_user_data()
        if not username:
            QtWidgets.QMessageBox.warning(self, "Fehler", "Benutzername darf nicht leer sein.")
            return
        email = self.email_input.text().strip()
        if email and not _EMAIL_RE.match(email):
            QtWidgets.QMessageBox.warning(self, "Fehler", "Bitte eine gültige E-Mail-Adresse eingeben.")
            return
        super().accept()

