"""Verfall-Tab — Prognose, Risiko-Score, Charge-Trace.

Issue #42 Phase 1+2 — mit interaktivem Forecast-Chart und Cross-Filter.
"""

from __future__ import annotations

import logging

from PySide6 import QtWidgets

from apple_theme import AppleTheme
from ui.utils import configure_responsive_table

from .._charts.forecast_band import ForecastBandChart
from .._filters.cross_filter_state import CrossFilterState
from ._base_tab import BaseTab

logger = logging.getLogger(__name__)


class TabVerfall(BaseTab):
    """Verfall-Analyse: Warnings, Forecast-Chart, Charge-Liste."""

    def __init__(self, db, queries, parent=None) -> None:
        super().__init__(db, queries, parent)
        self._filter_state = CrossFilterState.instance()
        self._filter_state.add_listener(self._on_filter_changed)

    def _on_filter_changed(self, state) -> None:
        """Cross-Filter geändert → Tab neu laden."""
        self.refresh()

    def refresh(self) -> None:
        self._clear_content()

        # 1. Interaktiver Forecast-Chart
        card_forecast = self._make_card("📈 Verfall-Forecast (nächste 12 Monate)")
        chart_forecast = self._build_forecast_chart()
        card_forecast.layout().addWidget(chart_forecast)

        # 2. Verfall-Warnings (nächste 30 Tage)
        card_warn = self._make_card("🚨 Verfälle in den nächsten 30 Tagen")
        table_warn = self._build_warnings_table()
        card_warn.layout().addWidget(table_warn)

        self.content_layout.addStretch()

    def _build_forecast_chart(self) -> ForecastBandChart:
        """Interaktiver Forecast-Chart aus get_verfall_forecast()."""
        rows = self.queries.get_verfall_forecast(months=12)
        chart = ForecastBandChart(width=6, height=3)

        if not rows:
            chart.plot([], [], title="Verfall-Forecast")
            return chart

        months = [str(r["monat"]) for r in rows]
        values = [int(r["verfallende_einheiten"]) for r in rows]

        # Einfaches Konfidenz-Band: ±20% um den Wert
        confidence_band = [(v * 0.8, v * 1.2) for v in values]

        chart.plot(months, values, title="Verfallende Einheiten pro Monat",
                   confidence_band=confidence_band)
        return chart

    def _build_warnings_table(self) -> QtWidgets.QTableWidget:
        rows = self.queries.get_verfall_warnings(days=30)

        # Cross-Filter anwenden
        if self._filter_state.state.depot_ids:
            rows = [r for r in rows if r["depot_id"] in self._filter_state.state.depot_ids]
        if self._filter_state.state.praeparat_ids:
            rows = [r for r in rows if r["praeparat_id"] in self._filter_state.state.praeparat_ids]

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
