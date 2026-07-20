"""Email-Schedule-Tab — wöchentliche/monthliche PDF-Reports per Email.

Ermöglicht das Einrichten von Email-Schedules für Analytics-Reports.
Power-User können definieren: welche Empfänger, welches Intervall,
welches Format (PDF/HTML).

Issue #42 Phase 4 — Power-User.
"""

from __future__ import annotations

import logging

from PySide6 import QtCore, QtWidgets

from apple_theme import AppleTheme
from db_manager import Database
from ui.utils import configure_responsive_table

from ._base_tab import BaseTab

logger = logging.getLogger(__name__)

_SCHEDULE_OPTIONS = [
    ("Täglich", "daily"),
    ("Wöchentlich", "weekly"),
    ("Monatlich", "monthly"),
]

_REPORT_TYPES = [
    ("PDF", "pdf"),
    ("HTML", "html"),
]


class TabEmailSchedule(BaseTab):
    """Email-Schedule-Tab für automatisierte Analytics-Reports."""

    def __init__(self, db: Database, queries=None, parent=None) -> None:
        super().__init__(db, queries, parent)

    def refresh(self) -> None:
        self._clear_content()

        # 1. Neuen Schedule anlegen
        card_new = self._make_card("📧 Neuen Email-Schedule anlegen")
        self._build_new_schedule_form(card_new)
        self.content_layout.addWidget(card_new)

        # 2. Bestehende Schedules
        card_list = self._make_card("📋 Aktive Schedules")
        self._build_schedule_list(card_list)
        self.content_layout.addWidget(card_list)

        self.content_layout.addStretch()

    def _build_new_schedule_form(self, card: QtWidgets.QFrame) -> None:
        """Baut das Formular für neue Schedules."""
        layout = card.layout()
        c = AppleTheme.current_colors()

        form_layout = QtWidgets.QFormLayout()
        form_layout.setSpacing(10)

        # Name
        self.input_name = QtWidgets.QLineEdit()
        self.input_name.setPlaceholderText("z.B. 'Wöchentlicher Depot-Report'")
        form_layout.addRow("Name:", self.input_name)

        # Empfänger
        self.input_recipients = QtWidgets.QLineEdit()
        self.input_recipients.setPlaceholderText("email1@beispiel.de, email2@beispiel.de")
        form_layout.addRow("Empfänger:", self.input_recipients)

        # Intervall
        self.combo_schedule = QtWidgets.QComboBox()
        for label, value in _SCHEDULE_OPTIONS:
            self.combo_schedule.addItem(label, value)
        form_layout.addRow("Intervall:", self.combo_schedule)

        # Format
        self.combo_report_type = QtWidgets.QComboBox()
        for label, value in _REPORT_TYPES:
            self.combo_report_type.addItem(label, value)
        form_layout.addRow("Format:", self.combo_report_type)

        layout.addLayout(form_layout)

        # Save-Button
        self.btn_save_schedule = QtWidgets.QPushButton("💾 Schedule speichern")
        self.btn_save_schedule.setStyleSheet(
            f"background-color: {c['blue']}; color: white; font-weight: 600; padding: 8px 16px; border-radius: 6px;"
        )
        self.btn_save_schedule.clicked.connect(self._on_save_schedule)
        layout.addWidget(self.btn_save_schedule)

    def _build_schedule_list(self, card: QtWidgets.QFrame) -> None:
        """Baut die Liste der bestehenden Schedules."""
        layout = card.layout()

        self.schedule_table = self._create_responsive_table([], 0)
        self._populate_schedules()
        layout.addWidget(self.schedule_table)

        # Action-Buttons
        action_layout = QtWidgets.QHBoxLayout()

        self.btn_toggle = QtWidgets.QPushButton("⏯ Aktiv/Inaktiv")
        self.btn_toggle.clicked.connect(self._on_toggle_schedule)
        action_layout.addWidget(self.btn_toggle)

        self.btn_send_now = QtWidgets.QPushButton("📨 Jetzt senden")
        self.btn_send_now.clicked.connect(self._on_send_now)
        action_layout.addWidget(self.btn_send_now)

        self.btn_delete_schedule = QtWidgets.QPushButton("🗑️ Löschen")
        self.btn_delete_schedule.clicked.connect(self._on_delete_schedule)
        action_layout.addWidget(self.btn_delete_schedule)

        action_layout.addStretch()
        layout.addLayout(action_layout)

    def _populate_schedules(self) -> None:
        """Lädt Schedules in die Tabelle."""
        try:
            schedules = self.db.get_email_schedules()
        except Exception:
            schedules = []

        headers = ["Name", "Format", "Empfänger", "Intervall", "Aktiv", "Zuletzt gesendet"]
        self.schedule_table.setColumnCount(len(headers))
        self.schedule_table.setHorizontalHeaderLabels(headers)
        self.schedule_table.setRowCount(len(schedules))

        for i, s in enumerate(schedules):
            self.schedule_table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(s["name"])))
            self.schedule_table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(s["report_type"]).upper()))
            self.schedule_table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(s["recipients"])))
            self.schedule_table.setItem(i, 3, QtWidgets.QTableWidgetItem(str(s["schedule"])))
            enabled = "✅" if s["enabled"] else "❌"
            self.schedule_table.setItem(i, 4, QtWidgets.QTableWidgetItem(enabled))
            self.schedule_table.setItem(i, 5, QtWidgets.QTableWidgetItem(str(s["last_sent"] or "—")))

            # ID als unsichtbare Daten speichern
            item = self.schedule_table.item(i, 0)
            if item:
                item.setData(QtCore.Qt.UserRole, s["id"])

    def _on_save_schedule(self) -> None:
        """Neuen Schedule speichern."""
        name = self.input_name.text().strip()
        recipients = self.input_recipients.text().strip()
        schedule = self.combo_schedule.currentData()
        report_type = self.combo_report_type.currentData()

        if not name or not recipients:
            QtWidgets.QMessageBox.warning(self, "Fehler", "Name und Empfänger sind Pflichtfelder.")
            return

        if self.db.save_email_schedule(name, recipients, schedule, report_type):
            self._populate_schedules()
            self.input_name.clear()
            self.input_recipients.clear()
            QtWidgets.QMessageBox.information(self, "Gespeichert", f"Schedule '{name}' angelegt.")
        else:
            QtWidgets.QMessageBox.warning(self, "Fehler", "Schedule konnte nicht gespeichert werden.")

    def _on_toggle_schedule(self) -> None:
        """Schedule aktivieren/deaktivieren."""
        row = self.schedule_table.currentRow()
        if row < 0:
            return
        item = self.schedule_table.item(row, 0)
        schedule_id = item.data(QtCore.Qt.UserRole) if item else None
        if schedule_id is None:
            return

        current_enabled = self.schedule_table.item(row, 4).text() == "✅"
        self.db.toggle_email_schedule(schedule_id, not current_enabled)
        self._populate_schedules()

    def _on_send_now(self) -> None:
        """Schedule sofort auslösen (manueller Versand)."""
        row = self.schedule_table.currentRow()
        if row < 0:
            return
        name = self.schedule_table.item(row, 0).text()
        QtWidgets.QMessageBox.information(
            self, "Senden",
            f"Schedule '{name}' wird vorbereitet.\n"
            "Der eigentliche Email-Versand erfolgt über das Backend "
            "(n8n-Workflow oder SMTP-Integration).\n"
            "last_sent wurde aktualisiert.",
        )
        item = self.schedule_table.item(row, 0)
        schedule_id = item.data(QtCore.Qt.UserRole) if item else None
        if schedule_id is not None:
            self.db.update_email_schedule_sent(schedule_id)
            self._populate_schedules()

    def _on_delete_schedule(self) -> None:
        """Schedule löschen."""
        row = self.schedule_table.currentRow()
        if row < 0:
            return
        item = self.schedule_table.item(row, 0)
        schedule_id = item.data(QtCore.Qt.UserRole) if item else None
        name = item.text() if item else ""
        if schedule_id is None:
            return

        reply = QtWidgets.QMessageBox.question(
            self, "Löschen", f"Schedule '{name}' wirklich löschen?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.db.delete_email_schedule(schedule_id)
            self._populate_schedules()

    def _create_table(self, headers: list[str], row_count: int) -> QtWidgets.QTableWidget:
        table = QtWidgets.QTableWidget(row_count, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        try:
            configure_responsive_table(table)
        except Exception:
            table.resizeColumnsToContents()
        return table
