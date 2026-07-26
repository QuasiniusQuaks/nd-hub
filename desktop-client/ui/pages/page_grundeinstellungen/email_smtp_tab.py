"""SMTP-Direktversand-Tab für Grundeinstellungen."""
from apple_theme import AppleTheme
from icon_manager import IconManager
from PySide6 import QtWidgets

from ui.utils import create_card_widget


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

