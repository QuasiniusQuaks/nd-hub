"""Bewegungen-Tab — Flow, Ranking, Top-Movers, Zeitreihen.

Issue #42 Phase 1+2 — mit interaktiven Bar-Charts und Cross-Filter.
"""

from __future__ import annotations

import logging

from PySide6 import QtWidgets

from apple_theme import AppleTheme
from ui.utils import configure_responsive_table

from .._charts.ranking_bar import RankingBarChart
from .._filters.cross_filter_state import CrossFilterState
from ._base_tab import BaseTab

logger = logging.getLogger(__name__)


class TabBewegungen(BaseTab):
    """Bewegungs-Analyse: Top-Movers (Charts), Rankings (Tabellen)."""

    def __init__(self, db, queries, parent=None) -> None:
        super().__init__(db, queries, parent)
        self._filter_state = CrossFilterState.instance()
        self._filter_state.add_listener(self._on_filter_changed)

    def _on_filter_changed(self, state) -> None:
        """Cross-Filter geändert → Tab neu laden."""
        self.refresh()

    def refresh(self) -> None:
        self._clear_content()

        days = self._filter_state.state.date_range_days

        # 1. Top-Movers Eingang (Bar-Chart)
        card_in = self._make_card("Top-Movers: Zugänge (interaktiv)")
        chart_in = self._build_movers_chart(direction="in", days=days)
        card_in.layout().addWidget(chart_in)

        # 2. Top-Movers Abgang (Bar-Chart)
        card_out = self._make_card("Top-Movers: Abgänge (interaktiv)")
        chart_out = self._build_movers_chart(direction="out", days=days)
        card_out.layout().addWidget(chart_out)

        # 3. Depot-Ranking (Tabelle)
        card_rank = self._make_card("Depot-Ranking nach Abgaben")
        table_rank = self._build_ranking_table()
        card_rank.layout().addWidget(table_rank)

        # 4. Präparat-Ranking (Tabelle)
        card_praep = self._make_card("Präparat-Ranking nach Abgaben")
        table_praep = self._build_praeparat_ranking_table()
        card_praep.layout().addWidget(table_praep)

        # 5. Anomalie-Detection (Phase 3)
        card_anomaly = self._make_card("🔮 Statistische Anomalien (Z-Score ≥ 2.0)")
        table_anomaly = self._build_anomaly_table()
        card_anomaly.layout().addWidget(table_anomaly)

        self.content_layout.addStretch()

    def _build_movers_chart(self, direction: str, days: int = 30) -> RankingBarChart:
        """Bar-Chart für Top-Movers mit Click-to-Filter."""
        rows = self.queries.get_top_movers(direction=direction, limit=10, days=days)

        # Cross-Filter anwenden
        if self._filter_state.state.praeparat_ids:
            rows = [r for r in rows if r["praeparat_id"] in self._filter_state.state.praeparat_ids]

        chart = RankingBarChart(width=5, height=3)
        if not rows:
            chart.plot([], [], title=f"Top-{direction.upper()} (keine Daten)")
            return chart

        labels = [str(r["praeparat_name"]) for r in rows]
        values = [int(r["gesamt"]) for r in rows]
        ids = [r["praeparat_id"] for r in rows]
        color = "green" if direction == "in" else "red"
        title = "Zugänge" if direction == "in" else "Abgänge"
        chart.plot(labels, values, title=title, color_key=color,
                   ids=ids, id_type="praeparat")
        return chart

    def _build_ranking_table(self) -> QtWidgets.QTableWidget:
        rows = self.queries.get_depot_ranking(limit=10)

        if self._filter_state.state.depot_ids:
            rows = [r for r in rows if str(r["depot_name"]) in
                    {str(d) for d in self._filter_state.state.depot_ids}]

        headers = ["Depot", "Präparat", "Abgaben gesamt"]
        table = self._create_table(headers, len(rows))

        for i, row in enumerate(rows):
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(row["depot_name"])))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(row["praeparat_name"])))
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(row["abgaben_gesamt"])))

        if not rows:
            self._add_empty_hint(table, "Keine Abgaben im gewählten Zeitraum.")

        return table

    def _build_praeparat_ranking_table(self) -> QtWidgets.QTableWidget:
        rows = self.queries.get_praeparat_ranking(limit=10)

        if self._filter_state.state.praeparat_ids:
            rows = [r for r in rows if str(r["praeparat_name"]) in
                    {str(p) for p in self._filter_state.state.praeparat_ids}]

        headers = ["Präparat", "Depot", "Abgaben gesamt"]
        table = self._create_table(headers, len(rows))

        for i, row in enumerate(rows):
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(row["praeparat_name"])))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(row["depot_name"])))
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(row["abgaben_gesamt"])))

        if not rows:
            self._add_empty_hint(table, "Keine Abgaben im gewählten Zeitraum.")

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

    def _build_anomaly_table(self) -> QtWidgets.QTableWidget:
        """Anomalie-Tabelle aus get_anomalies() (Phase 3)."""
        rows = self.queries.get_anomalies(threshold_std=2.0)
        headers = ["Präparat", "Typ", "Datum", "Menge", "Ø Normal", "Z-Score", "Bewertung"]
        table = self._create_table(headers, len(rows))

        c = AppleTheme.current_colors()
        for i, row in enumerate(rows):
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(row["praeparat_name"])))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(row["typ"])))
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(row["tag"])))
            table.setItem(i, 3, QtWidgets.QTableWidgetItem(str(row["total"])))
            table.setItem(i, 4, QtWidgets.QTableWidgetItem(f"{row['mean']:.1f}"))

            z_score = row["z_score"] or 0
            z_item = QtWidgets.QTableWidgetItem(f"{z_score:.2f}")
            from PySide6 import QtGui
            if abs(z_score) >= 3.0:
                z_item.setForeground(QtGui.QColor(c["red"]))
            elif abs(z_score) >= 2.5:
                z_item.setForeground(QtGui.QColor(c["orange"]))
            else:
                z_item.setForeground(QtGui.QColor(c["blue"]))
            table.setItem(i, 5, z_item)

            bewertung = "🔴 Kritisch" if abs(z_score) >= 3.0 else ("🟡 Auffällig" if abs(z_score) >= 2.5 else "🟢 Leicht")
            table.setItem(i, 6, QtWidgets.QTableWidgetItem(bewertung))

        if not rows:
            self._add_empty_hint(table, "Keine statistischen Anomalien erkannt ✅")

        return table
