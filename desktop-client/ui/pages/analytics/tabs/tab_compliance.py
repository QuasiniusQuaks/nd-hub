"""Compliance-Tab — Audit-Trail, User-Aktivität, Email-Verlauf.

Issue #42 Phase 1.
"""

from __future__ import annotations

import logging

from PySide6 import QtWidgets

from apple_theme import AppleTheme

from ._base_tab import BaseTab

logger = logging.getLogger(__name__)


class TabCompliance(BaseTab):
    """Compliance-Analyse: Email-Verlauf, User-Berechtigungen."""

    def refresh(self) -> None:
        self._clear_content()

        data = self.queries.get_compliance_overview()

        # 1. Email-Verlauf
        card_emails = self._make_card("Email-Versand-Verlauf (letzte 50)")
        table_emails = self._build_email_table(data.get("email_verlauf", []))
        card_emails.layout().addWidget(table_emails)

        # 2. User-Berechtigungen
        card_perms = self._make_card("User-Depot-Berechtigungen")
        table_perms = self._build_permissions_table(data.get("permissions", []))
        card_perms.layout().addWidget(table_perms)

        self.content_layout.addStretch()

    def _build_email_table(self, rows: list) -> QtWidgets.QTableWidget:
        headers = ["Datum", "Betreff", "Empfänger-Depots", "Status", "Kanal"]
        table = self._create_responsive_table(headers, len(rows))

        c = AppleTheme.current_colors()
        for i, row in enumerate(rows):
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(row["datum"] or "—")))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(row["betreff"] or "—")))
            depots = str(row["empfaenger_depots"] or "—")
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(depots))

            status = str(row["delivery_status"] or "draft")
            status_item = QtWidgets.QTableWidgetItem(status)
            from PySide6 import QtGui
            if status == "sent":
                status_item.setForeground(QtGui.QColor(c["green"]))
            elif status == "failed":
                status_item.setForeground(QtGui.QColor(c["red"]))
            elif status == "draft":
                status_item.setForeground(QtGui.QColor(c["tertiary_label"]))
            table.setItem(i, 3, status_item)

            table.setItem(i, 4, QtWidgets.QTableWidgetItem(str(row["delivery_channel"] or "—")))

        if not rows:
            self._add_empty_hint(table, "Keine Emails versendet.")

        return table

    def _build_permissions_table(self, rows: list) -> QtWidgets.QTableWidget:
        headers = ["User", "Depot", "Lesen", "Schreiben"]
        table = self._create_responsive_table(headers, len(rows))

        for i, row in enumerate(rows):
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(row["username"])))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(row["depot_name"])))
            read = "✅" if row["can_read"] else "❌"
            write = "✅" if row["can_write"] else "❌"
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(read))
            table.setItem(i, 3, QtWidgets.QTableWidgetItem(write))

        if not rows:
            self._add_empty_hint(table, "Keine User-Berechtigungen vergeben.")

        return table


    def _add_empty_hint(self, table: QtWidgets.QTableWidget, text: str) -> None:
        table.setRowCount(1)
        table.setItem(0, 0, QtWidgets.QTableWidgetItem(text))
