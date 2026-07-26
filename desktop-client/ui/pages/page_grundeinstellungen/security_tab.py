"""Optionaler Sicherheits-Tab (Passwort) — aus Monolith extrahiert."""
from apple_theme import AppleTheme
from db_manager import DB
from PySide6 import QtWidgets
from security_manager import SecurityManager

from ui.utils import create_card_widget


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
