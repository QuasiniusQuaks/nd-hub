"""Globale Dialoge fuer Passwoerter, Depots und Kontakte."""
from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from apple_theme import AppleTheme

from core.auth_worker import AuthVerifyRunner


class PasswordDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Passwortschutz")
        self.setMinimumWidth(350)
        self.setModal(True)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(16)
        
        info_label = QtWidgets.QLabel(
            "\ud83d\udd12 Geschuetzter Bereich\n\n"
            "Die Grundeinstellungen sind passwortgeschuetzt.\n"
            "Bitte geben Sie das Passwort ein:"
        )
        c = AppleTheme.current_colors()
        info_label.setStyleSheet(f"color: {c['label']}; padding: 12px; background-color: {c['bg_tertiary']}; border-radius: 6px;")
        layout.addWidget(info_label)
        
        form = QtWidgets.QFormLayout()
        form.setSpacing(12)
        
        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password_input.setPlaceholderText("Passwort eingeben...")
        form.addRow("Passwort:", self.password_input)
        
        layout.addLayout(form)
        
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.ok_button = buttons.button(QtWidgets.QDialogButtonBox.Ok)
        buttons.accepted.connect(self.check_password)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.password_input.returnPressed.connect(self.check_password)
        self.password_input.setFocus()
        
        self._auth_runner: AuthVerifyRunner | None = None
    
    def check_password(self):
        """Startet die Passwort-Pruefung asynchron im Worker-Thread."""
        entered = self.password_input.text()
        parent_page = self.parent()
        if not parent_page or not hasattr(parent_page, 'load_password_hash'):
            self._show_error("Interner Fehler: Passwort-Hash kann nicht geladen werden.")
            return
        
        stored_hash = parent_page.load_password_hash()
        if not stored_hash:
            # Kein Passwort gesetzt -> direkt akzeptieren
            self.accept()
            return
        
        self.ok_button.setEnabled(False)
        self.ok_button.setText("Pruefe...")
        self.password_input.setEnabled(False)
        
        self._auth_runner = AuthVerifyRunner()
        self._auth_runner.signals.finished.connect(self._on_auth_finished)
        self._auth_runner.signals.failed.connect(self._on_auth_failed)
        self._auth_runner.start(entered, stored_hash)
    
    def _on_auth_finished(self, is_valid: bool):
        """Wird vom Worker-Signal aufgerufen, wenn die Verifikation fertig ist."""
        self._reset_ui()
        if is_valid:
            self.accept()
        else:
            self._show_error("Das eingegebene Passwort ist nicht korrekt.\n\nBitte versuchen Sie es erneut.")
    
    def _on_auth_failed(self, error_message: str):
        """Wird vom Worker-Signal aufgerufen, wenn die Verifikation fehlschlaegt."""
        self._reset_ui()
        self._show_error(f"Passwort-Pruefung fehlgeschlagen:\n{error_message}")
    
    def _reset_ui(self):
        self.ok_button.setEnabled(True)
        self.ok_button.setText("OK")
        self.password_input.setEnabled(True)
        self.password_input.setFocus()
    
    def _show_error(self, message: str):
        QtWidgets.QMessageBox.warning(self, "Falsches Passwort", message)
        self.password_input.clear()
        self.password_input.setFocus()


class DepotDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, name="", adresse="", telefon="", email=""):
        super().__init__(parent)
        self.setWindowTitle("Depot bearbeiten")
        self.setMinimumWidth(450)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(16)
        
        form = QtWidgets.QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)
        
        self.e_name = QtWidgets.QLineEdit(name)
        self.e_addr = QtWidgets.QLineEdit(adresse)
        self.e_tel = QtWidgets.QLineEdit(telefon)
        self.e_email = QtWidgets.QLineEdit(email)
        
        form.addRow("Name:", self.e_name)
        form.addRow("Adresse:", self.e_addr)
        form.addRow("Telefon:", self.e_tel)
        form.addRow("E-Mail:", self.e_email)
        layout.addLayout(form)
        
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        return (self.e_name.text().strip(), self.e_addr.text().strip(),
                self.e_tel.text().strip(), self.e_email.text().strip())


class KontaktDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, name="", rolle="", telefon="", email=""):
        super().__init__(parent)
        self.setWindowTitle("Ansprechpartner")
        self.setMinimumWidth(450)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(16)
        
        form = QtWidgets.QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)
        
        self.e_name = QtWidgets.QLineEdit(name)
        self.e_rolle = QtWidgets.QLineEdit(rolle)
        self.e_tel = QtWidgets.QLineEdit(telefon)
        self.e_email = QtWidgets.QLineEdit(email)
        
        form.addRow("Name:", self.e_name)
        form.addRow("Rolle:", self.e_rolle)
        form.addRow("Telefon:", self.e_tel)
        form.addRow("E-Mail:", self.e_email)
        layout.addLayout(form)
        
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        return (self.e_name.text().strip(), self.e_rolle.text().strip(), 
                self.e_tel.text().strip(), self.e_email.text().strip())
