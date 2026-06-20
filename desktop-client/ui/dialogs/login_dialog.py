
"""
Login und Passwort-Dialoge für ND-Hub - Die ND-Hub-Verwaltung
Version: 1.1 (Layout-Refactor)
"""
from PySide6 import QtWidgets
from PySide6.QtCore import Qt

from apple_theme import AppleTheme


class LoginDialog(QtWidgets.QDialog):
    """Moderner Login-Dialog mit Username und Passwort"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Anmeldung - ND-Hub")
        self.setModal(True)
        self.resize(450, 520)  # Dynamische Größe statt fix
        self.username = None
        self.password = None
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Logo/Icon
        icon_label = QtWidgets.QLabel("🔐")
        icon_label.setStyleSheet("font-size: 64px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # Titel
        c = AppleTheme.current_colors()
        title = QtWidgets.QLabel("Willkommen")
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 700;
            color: {c['label']};
        """)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Untertitel
        subtitle = QtWidgets.QLabel("Bitte melden Sie sich an")
        subtitle.setStyleSheet(f"font-size: 14px; color: {c['secondary_label']};")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        # Formular
        form_widget = QtWidgets.QWidget()
        form_layout = QtWidgets.QFormLayout(form_widget)
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignRight)

        self.username_input = QtWidgets.QLineEdit()
        self.username_input.setPlaceholderText("Benutzername eingeben...")
        self.username_input.setMinimumHeight(40)
        self.username_input.setText("admin")  # Vorausgefüllt
        form_layout.addRow("Benutzername:", self.username_input)

        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setPlaceholderText("Passwort eingeben...")
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password_input.setMinimumHeight(40)
        form_layout.addRow("Passwort:", self.password_input)

        self.show_password_check = QtWidgets.QCheckBox("Passwort anzeigen")
        self.show_password_check.stateChanged.connect(self.toggle_password_visibility)
        form_layout.addRow("", self.show_password_check)

        layout.addWidget(form_widget)

        # Info-Text
        info_label = QtWidgets.QLabel(
            "💡 Standard-Login: admin / admin\nBitte ändern Sie das Passwort nach der ersten Anmeldung!"
        )
        info_label.setStyleSheet(f"""
            background-color: {c['orange']}22;
            color: {c['label']};
            padding: 12px;
            border-radius: 6px;
            border: 1px solid {c['orange']};
            font-size: 12px;
        """)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        layout.addStretch()

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(10)
        self.btn_cancel = QtWidgets.QPushButton("Abbrechen")
        self.btn_cancel.setMinimumHeight(44)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_login = QtWidgets.QPushButton("Anmelden")
        self.btn_login.setMinimumHeight(44)
        self.btn_login.clicked.connect(self.accept)
        self.btn_login.setDefault(True)

        button_layout.addWidget(self.btn_cancel)
        button_layout.addWidget(self.btn_login)
        layout.addLayout(button_layout)

        # Enter-Taste für Login
        self.password_input.returnPressed.connect(self.accept)
        self.username_input.returnPressed.connect(self.password_input.setFocus)

    def toggle_password_visibility(self, state):
        """Schaltet Passwort-Sichtbarkeit um"""
        mode = QtWidgets.QLineEdit.Normal if state == Qt.Checked else QtWidgets.QLineEdit.Password
        self.password_input.setEchoMode(mode)

    def get_credentials(self):
        """Gibt die eingegebenen Anmeldedaten zurück"""
        return self.username_input.text().strip(), self.password_input.text()

    def accept(self):
        """Validiert und akzeptiert die Eingabe"""
        username, password = self.get_credentials()
        if not username:
            QtWidgets.QMessageBox.warning(self, "Eingabe erforderlich", "Bitte geben Sie einen Benutzernamen ein.")
            self.username_input.setFocus()
            return
        if not password:
            QtWidgets.QMessageBox.warning(self, "Eingabe erforderlich", "Bitte geben Sie ein Passwort ein.")
            self.password_input.setFocus()
            return
        self.username = username
        self.password = password
        super().accept()


class ChangePasswordDialog(QtWidgets.QDialog):
    """Dialog zum Ändern des Passworts"""

    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self.username = username
        self.setWindowTitle("Passwort ändern")
        self.setModal(True)
        self.resize(450, 500)  # Dynamische Größe
        self.old_password = None
        self.new_password = None
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        header_layout = QtWidgets.QHBoxLayout()
        icon_label = QtWidgets.QLabel("🔑")
        icon_label.setStyleSheet("font-size: 48px;")
        header_layout.addWidget(icon_label)

        title_layout = QtWidgets.QVBoxLayout()
        c = AppleTheme.current_colors()
        title = QtWidgets.QLabel("Passwort ändern")
        title.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {c['label']};")
        subtitle = QtWidgets.QLabel(f"Benutzer: {self.username}")
        subtitle.setStyleSheet(f"font-size: 13px; color: {c['secondary_label']};")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Formular
        form_widget = QtWidgets.QWidget()
        form_layout = QtWidgets.QFormLayout(form_widget)
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignRight)

        self.old_password_input = QtWidgets.QLineEdit()
        self.old_password_input.setPlaceholderText("Aktuelles Passwort eingeben...")
        self.old_password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.old_password_input.setMinimumHeight(40)
        form_layout.addRow("Aktuelles Passwort:", self.old_password_input)

        self.new_password_input = QtWidgets.QLineEdit()
        self.new_password_input.setPlaceholderText("Neues Passwort eingeben...")
        self.new_password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.new_password_input.setMinimumHeight(40)
        self.new_password_input.textChanged.connect(self.update_password_strength)
        form_layout.addRow("Neues Passwort:", self.new_password_input)

        self.strength_label = QtWidgets.QLabel("Passwortstärke: -")
        self.strength_label.setStyleSheet("font-size: 12px; color: #95a5a6; margin-left: 4px;")
        layout.addWidget(form_widget)
        layout.addWidget(self.strength_label)

        self.confirm_password_input = QtWidgets.QLineEdit()
        self.confirm_password_input.setPlaceholderText("Neues Passwort wiederholen...")
        self.confirm_password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.confirm_password_input.setMinimumHeight(40)
        form_layout.addRow("Passwort wiederholen:", self.confirm_password_input)

        self.show_password_check = QtWidgets.QCheckBox("Passwörter anzeigen")
        self.show_password_check.stateChanged.connect(self.toggle_password_visibility)
        form_layout.addRow("", self.show_password_check)

        # Hinweise
        hints_widget = QtWidgets.QWidget()
        hints_widget.setStyleSheet(f"""
            background-color: {c['blue']}15;
            border: 1px solid {c['blue']};
            border-radius: 6px;
            padding: 12px;
        """)
        hints_layout = QtWidgets.QVBoxLayout(hints_widget)
        hints_layout.setSpacing(4)
        hints_title = QtWidgets.QLabel("💡 Tipps für ein sicheres Passwort:")
        hints_title.setStyleSheet(f"font-weight: 600; color: {c['label']}; font-size: 12px;")
        hints_layout.addWidget(hints_title)
        for hint in [
            "• Mindestens 8 Zeichen verwenden",
            "• Groß- und Kleinbuchstaben kombinieren",
            "• Zahlen und Sonderzeichen einbauen",
            "• Keine persönlichen Informationen verwenden"
        ]:
            hint_label = QtWidgets.QLabel(hint)
            hint_label.setStyleSheet(f"color: {c['secondary_label']}; font-size: 11px;")
            hints_layout.addWidget(hint_label)
        layout.addWidget(hints_widget)
        layout.addStretch()

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(10)
        self.btn_cancel = QtWidgets.QPushButton("Abbrechen")
        self.btn_cancel.setMinimumHeight(44)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QtWidgets.QPushButton("Passwort ändern")
        self.btn_save.setMinimumHeight(44)
        self.btn_save.clicked.connect(self.validate_and_accept)

        button_layout.addWidget(self.btn_cancel)
        button_layout.addWidget(self.btn_save)
        layout.addLayout(button_layout)

        self.old_password_input.setFocus()

    def toggle_password_visibility(self, state):
        mode = QtWidgets.QLineEdit.Normal if state == Qt.Checked else QtWidgets.QLineEdit.Password
        self.old_password_input.setEchoMode(mode)
        self.new_password_input.setEchoMode(mode)
        self.confirm_password_input.setEchoMode(mode)

    def update_password_strength(self):
        password = self.new_password_input.text()
        if not password:
            self.strength_label.setText("Passwortstärke: -")
            self.strength_label.setStyleSheet("font-size: 12px; color: #95a5a6;")
            return
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
        if any(c in "!@#$%^&*()_+-=[]{};:,.<>?" for c in password):
            strength += 1
        else:
            feedback.append("Sonderzeichen")

        if strength <= 1:
            color, text = "#e74c3c", "Sehr schwach"
        elif strength == 2:
            color, text = "#e67e22", "Schwach"
        elif strength == 3:
            color, text = "#f39c12", "Mittel"
        elif strength == 4:
            color, text = "#27ae60", "Gut"
        else:
            color, text = "#27ae60", "Sehr gut"

        feedback_text = f" (Fehlt: {', '.join(feedback)})" if feedback and strength < 4 else ""
        self.strength_label.setText(f"Passwortstärke: {text}{feedback_text}")
        self.strength_label.setStyleSheet(f"font-size: 12px; color: {color}; font-weight: 600;")

    def validate_and_accept(self):
        old_pw = self.old_password_input.text()
        new_pw = self.new_password_input.text()
        confirm_pw = self.confirm_password_input.text()
        if not old_pw:
            QtWidgets.QMessageBox.warning(self, "Eingabe erforderlich", "Bitte geben Sie Ihr aktuelles Passwort ein.")
            self.old_password_input.setFocus()
            return
        if not new_pw:
            QtWidgets.QMessageBox.warning(self, "Eingabe erforderlich", "Bitte geben Sie ein neues Passwort ein.")
            self.new_password_input.setFocus()
            return
        if len(new_pw) < 8:
            QtWidgets.QMessageBox.warning(self, "Passwort zu kurz",
                                          "Das neue Passwort muss mindestens 8 Zeichen lang sein.\n"
                                          "Empfohlen: Groß-/Kleinbuchstaben, Zahlen und Sonderzeichen.")
            self.new_password_input.setFocus()
            return
        if new_pw != confirm_pw:
            QtWidgets.QMessageBox.warning(self, "Passwörter stimmen nicht überein",
                                          "Die eingegebenen Passwörter stimmen nicht überein.\nBitte überprüfen Sie Ihre Eingabe.")
            self.confirm_password_input.clear()
            self.confirm_password_input.setFocus()
            return
        if old_pw == new_pw:
            QtWidgets.QMessageBox.warning(self, "Gleiches Passwort", "Das neue Passwort darf nicht mit dem alten identisch sein.")
            self.new_password_input.clear()
            self.confirm_password_input.clear()
            self.new_password_input.setFocus()
            return
        self.old_password = old_pw
        self.new_password = new_pw
        super().accept()

    def get_passwords(self):
        return self.old_password, self.new_password
