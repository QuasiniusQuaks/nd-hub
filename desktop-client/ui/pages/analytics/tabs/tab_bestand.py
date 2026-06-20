"""Bestand-Tab — Heatmap, Soll/Ist-Vergleich, Top-Abweichungen.

Issue #42 Phase 1.
"""

from __future__ import annotations

import logging

from PySide6 import QtWidgets

from apple_theme import AppleTheme
from ui.utils import configure_responsive_table

from ._base_tab import BaseTab

logger = logging.getLogger(__name__)


class TabBestand(BaseTab):
    """Bestand-Analyse: Soll/Ist, Matrix, Umschlag, Dead Stock."""

    def refresh(self) -> None:
        self._clear_content()

        # 1. Soll/Ist-Vergleich
        card_deviation = self._make_card("Soll/Ist-Abweichung pro Depot")
        table_deviation = self._build_deviation_table()
        card_deviation.layout().addWidget(table_deviation)

        # 2. Lagerumschlag
        card_turnover = self._make_card("Lagerumschlag pro Präparat")
        table_turnover = self._build_turnover_table()
        card_turnover.layout().addWidget(table_turnover)

        # 3. Dead Stock
        card_dead = self._make_card("Toter Bestand (>180 Tage ohne Bewegung)")
        table_dead = self._build_dead_stock_table()
        card_dead.layout().addWidget(table_dead)

        self.content_layout.addStretch()

    def _build_deviation_table(self) -> QtWidgets.QTableWidget:
        """Soll/Ist-Tabelle aus get_depot_deviation()."""
        rows = self.queries.get_depot_deviation()
        headers = ["Depot", "Soll", "Ist", "Differenz", "Status"]
        table = self._create_table(headers, len(rows))

        c = AppleTheme.current_colors()
        for i, row in enumerate(rows):
            diff = row["differenz"] or 0
            status = "🟢 OK" if abs(diff) <= 5 else ("🟡 Leicht" if abs(diff) <= 20 else "🔴 Kritisch")
            color = c["green"] if abs(diff) <= 5 else (c["orange"] if abs(diff) <= 20 else c["red"])

            table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(row["depot_name"])))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(row["soll_gesamt"])))
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(row["ist_gesamt"])))
            diff_item = QtWidgets.QTableWidgetItem(f"{diff:+d}")
            diff_item.setForeground(self._qcolor(color))
            table.setItem(i, 3, diff_item)
            table.setItem(i, 4, QtWidgets.QTableWidgetItem(status))

        return table

    def _build_turnover_table(self) -> QtWidgets.QTableWidget:
        """Umschlag-Tabelle aus get_inventory_turnover()."""
        rows = self.queries.get_inventory_turnover()
        headers = ["Präparat", "Zugang", "Abgang", "Umschlagsrate"]
        table = self._create_table(headers, len(rows))

        for i, row in enumerate(rows):
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(row["praeparat_name"])))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(row["zugang"])))
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(row["abgang"])))
            rate = row["umschlagsrate"] or 0
            rate_item = QtWidgets.QTableWidgetItem(f"{rate:.2f}")
            table.setItem(i, 3, rate_item)

        return table

    def _build_dead_stock_table(self) -> QtWidgets.QTableWidget:
        """Dead-Stock-Tabelle aus get_dead_stock()."""
        rows = self.queries.get_dead_stock(days=180)
        headers = ["Präparat", "Depot", "Bestand", "Letzte Bewegung"]
        table = self._create_table(headers, len(rows))

        for i, row in enumerate(rows):
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(row["praeparat_name"])))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(row["depot_name"])))
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(row["ist_bestand"])))
            last = row["letzte_bewegung"] or "—"
            table.setItem(i, 3, QtWidgets.QTableWidgetItem(str(last)))

        if not rows:
            self._add_empty_hint(table, "Kein toter Bestand — alle Präparate in Bewegung ✅")

        return table

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

    def _add_empty_hint(self, table: QtWidgets.QTableWidget, text: str) -> None:
        """Zeigt einen Hinweistext in einer leeren Tabelle."""
        table.setRowCount(1)
        table.setItem(0, 0, QtWidgets.QTableWidgetItem(text))

    @staticmethod
    def _qcolor(hex_color: str):
        from PySide6 import QtGui
        return QtGui.QColor(hex_color)
