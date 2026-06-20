"""Bewegungen-Tab — Flow, Ranking, Top-Movers, Zeitreihen.

Issue #42 Phase 1.
"""

from __future__ import annotations

import logging

from PySide6 import QtWidgets

from ui.utils import configure_responsive_table

from ._base_tab import BaseTab

logger = logging.getLogger(__name__)


class TabBewegungen(BaseTab):
    """Bewegungs-Analyse: Top-Movers, Depot-Ranking, Präparat-Ranking."""

    def refresh(self) -> None:
        self._clear_content()

        # 1. Top-Movers (Zugang)
        card_in = self._make_card("Top-Movers: Zugänge (letzte 30 Tage)")
        table_in = self._build_movers_table(direction="in")
        card_in.layout().addWidget(table_in)

        # 2. Top-Movers (Abgang)
        card_out = self._make_card("Top-Movers: Abgänge (letzte 30 Tage)")
        table_out = self._build_movers_table(direction="out")
        card_out.layout().addWidget(table_out)

        # 3. Depot-Ranking
        card_rank = self._make_card("Depot-Ranking nach Abgaben")
        table_rank = self._build_ranking_table()
        card_rank.layout().addWidget(table_rank)

        self.content_layout.addStretch()

    def _build_movers_table(self, direction: str) -> QtWidgets.QTableWidget:
        rows = self.queries.get_top_movers(direction=direction, limit=10, days=30)
        headers = ["Präparat", "Gesamt", "Anzahl Bewegungen", "Letzte Bewegung"]
        table = self._create_table(headers, len(rows))

        for i, row in enumerate(rows):
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(row["praeparat_name"])))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(row["gesamt"])))
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(row["anzahl_bewegungen"])))
            last = row["letzte_bewegung"] or "—"
            table.setItem(i, 3, QtWidgets.QTableWidgetItem(str(last)))

        if not rows:
            self._add_empty_hint(table, "Keine Bewegungen im gewählten Zeitraum.")

        return table

    def _build_ranking_table(self) -> QtWidgets.QTableWidget:
        rows = self.queries.get_depot_ranking(limit=10)
        headers = ["Depot", "Präparat", "Abgaben gesamt"]
        table = self._create_table(headers, len(rows))

        for i, row in enumerate(rows):
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(row["depot_name"])))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(row["praeparat_name"])))
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
