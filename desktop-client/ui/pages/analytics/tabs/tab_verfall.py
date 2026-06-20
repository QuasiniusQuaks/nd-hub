"""Verfall-Tab — Prognose, Risiko-Score, Charge-Trace.

Issue #42 Phase 1.
"""

from __future__ import annotations

import logging

from PySide6 import QtWidgets

from apple_theme import AppleTheme
from ui.utils import configure_responsive_table

from ._base_tab import BaseTab

logger = logging.getLogger(__name__)


class TabVerfall(BaseTab):
    """Verfall-Analyse: Warnings, Forecast, Charge-Liste."""

    def refresh(self) -> None:
        self._clear_content()

        # 1. Verfall-Warnings (nächste 30 Tage)
        card_warn = self._make_card("🚨 Verfälle in den nächsten 30 Tagen")
        table_warn = self._build_warnings_table()
        card_warn.layout().addWidget(table_warn)

        # 2. Verfall-Forecast (12 Monate)
        card_forecast = self._make_card("Verfall-Forecast (nächste 12 Monate)")
        table_forecast = self._build_forecast_table()
        card_forecast.layout().addWidget(table_forecast)

        self.content_layout.addStretch()

    def _build_warnings_table(self) -> QtWidgets.QTableWidget:
        rows = self.queries.get_verfall_warnings(days=30)
        headers = ["Präparat", "Depot", "Charge", "Verfall", "Menge"]
        table = self._create_table(headers, len(rows))

        c = AppleTheme.current_colors()
        for i, row in enumerate(rows):
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(row["praeparat_name"])))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(row["depot_name"])))
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(row["charge"] or "—")))
            verfall_item = QtWidgets.QTableWidgetItem(str(row["verfall"] or "—"))
            from PySide6 import QtGui
            verfall_item.setForeground(QtGui.QColor(c["red"]))
            table.setItem(i, 3, verfall_item)
            table.setItem(i, 4, QtWidgets.QTableWidgetItem(f"{row['anzahl']} EH"))

        if not rows:
            self._add_empty_hint(table, "Keine Verfälle in den nächsten 30 Tagen ✅")

        return table

    def _build_forecast_table(self) -> QtWidgets.QTableWidget:
        rows = self.queries.get_verfall_forecast(months=12)
        headers = ["Monat", "Verfallende Einheiten", "Anzahl Chargen"]
        table = self._create_table(headers, len(rows))

        for i, row in enumerate(rows):
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(row["monat"])))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(row["verfallende_einheiten"])))
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(row["anzahl_chargen"])))

        if not rows:
            self._add_empty_hint(table, "Keine Verfallsdaten für Forecast verfügbar.")

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
        table.setRowCount(1)
        table.setItem(0, 0, QtWidgets.QTableWidgetItem(text))
