"""Bestand-Tab — Heatmap, Soll/Ist-Vergleich, Top-Abweichungen.

Issue #42 Phase 1+2 — mit interaktiver Heatmap und Cross-Filter.
"""

from __future__ import annotations

import logging

import numpy as np
from apple_theme import AppleTheme
from PySide6 import QtWidgets

from .._charts.heatmap import HeatmapChart
from .._charts.ranking_bar import RankingBarChart
from .._filters.cross_filter_state import CrossFilterState
from ._base_tab import BaseTab

logger = logging.getLogger(__name__)


class TabBestand(BaseTab):
    """Bestand-Analyse: Heatmap, Soll/Ist, Umschlag, Dead Stock."""

    def __init__(self, db, queries, parent=None) -> None:
        super().__init__(db, queries, parent)
        self._filter_state = CrossFilterState.instance()
        self._filter_state.add_listener(self._on_filter_changed)

    def _on_filter_changed(self, state) -> None:
        """Cross-Filter geändert → Tab neu laden."""
        self.refresh()

    def refresh(self) -> None:
        self._clear_content()

        # 1. Interaktive Heatmap (Soll/Ist-Matrix)
        card_heatmap = self._make_card("📊 Soll/Ist-Heatmap (Depot × Präparat)")
        heatmap = self._build_heatmap()
        card_heatmap.layout().addWidget(heatmap)

        # 2. Soll/Ist-Tabelle
        card_deviation = self._make_card("Soll/Ist-Abweichung pro Depot")
        table_deviation = self._build_deviation_table()
        card_deviation.layout().addWidget(table_deviation)

        # 3. Top-Abweichungen als Bar-Chart
        card_bars = self._make_card("Top-Abweichungen (Ranking)")
        bar_chart = self._build_deviation_bar_chart()
        card_bars.layout().addWidget(bar_chart)

        # 4. Lagerumschlag
        card_turnover = self._make_card("Lagerumschlag pro Präparat")
        table_turnover = self._build_turnover_table()
        card_turnover.layout().addWidget(table_turnover)

        # 5. Dead Stock
        card_dead = self._make_card("Toter Bestand (>180 Tage ohne Bewegung)")
        table_dead = self._build_dead_stock_table()
        card_dead.layout().addWidget(table_dead)

        self.content_layout.addStretch()

    def _build_heatmap(self) -> HeatmapChart:
        """Interaktive Heatmap aus get_matrix_data().

        Bei vielen Präparaten werden die Top-N nach |Ist−Soll|-Summe gezeigt,
        damit Labels und Zellen lesbar bleiben.
        """
        rows = self.queries.get_matrix_data()
        chart = HeatmapChart(width=8, height=5)

        if not rows:
            chart.plot([], [], np.array([]))
            return chart

        # Cross-Filter
        def _rg(row, key, default=None):
            try:
                return row[key]
            except (KeyError, IndexError, TypeError):
                return default

        if self._filter_state.state.depot_ids:
            rows = [r for r in rows if _rg(r, "depot_id") in self._filter_state.state.depot_ids]
        if self._filter_state.state.praeparat_ids:
            rows = [r for r in rows if _rg(r, "praeparat_id") in self._filter_state.state.praeparat_ids]

        if not rows:
            chart.plot([], [], np.array([]), subtitle="Keine Daten für aktuelle Filter")
            return chart

        depot_names = sorted({str(r["depot_name"]) for r in rows})
        all_praep = sorted({str(r["praeparat_name"]) for r in rows})

        full = np.zeros((len(depot_names), len(all_praep)), dtype=int)
        for r in rows:
            di = depot_names.index(str(r["depot_name"]))
            pi = all_praep.index(str(r["praeparat_name"]))
            ist = r["ist_bestand"] or 0
            soll = r["sollbestand"] or 0
            full[di, pi] = int(ist) - int(soll)

        max_cols = 18
        col_scores = np.abs(full).sum(axis=0)
        if len(all_praep) > max_cols:
            top_idx = list(np.argsort(-col_scores)[:max_cols])
            top_idx.sort(key=lambda i: all_praep[i])
            praeparat_names = [all_praep[i] for i in top_idx]
            matrix = full[:, top_idx]
            subtitle = (
                f"Top {max_cols} Präparate nach |Ist−Soll| · {len(all_praep)} gesamt · "
                "Hover für Details"
            )
        else:
            praeparat_names = all_praep
            matrix = full
            subtitle = (
                f"{len(depot_names)} Depots × {len(praeparat_names)} Präparate · "
                "grün = Überbestand, rot = Unterbestand"
            )

        depot_name_to_id: dict = {}
        praeparat_name_to_id: dict = {}
        try:
            for r in self.db.cur.execute("SELECT id, name FROM depots").fetchall():
                if isinstance(r, tuple):
                    depot_name_to_id[r[1]] = r[0]
                else:
                    depot_name_to_id[r["name"]] = r["id"]
        except Exception:
            logger.debug("Depot-ID-Mapping fehlgeschlagen", exc_info=True)
        try:
            for r in self.db.cur.execute("SELECT id, name FROM praeparate").fetchall():
                if isinstance(r, tuple):
                    praeparat_name_to_id[r[1]] = r[0]
                else:
                    praeparat_name_to_id[r["name"]] = r["id"]
        except Exception:
            logger.debug("Präparat-ID-Mapping fehlgeschlagen", exc_info=True)

        for r in rows:
            did = _rg(r, "depot_id")
            pid = _rg(r, "praeparat_id")
            if did is not None:
                depot_name_to_id[str(r["depot_name"])] = did
            if pid is not None:
                praeparat_name_to_id[str(r["praeparat_name"])] = pid

        depot_ids = [depot_name_to_id.get(dn) for dn in depot_names]
        praeparat_ids = [praeparat_name_to_id.get(pn) for pn in praeparat_names]

        chart.plot(
            depot_names,
            praeparat_names,
            matrix,
            depot_ids=depot_ids,
            praeparat_ids=praeparat_ids,
            subtitle=subtitle,
        )
        return chart


    def _build_deviation_bar_chart(self) -> RankingBarChart:
        """Bar-Chart der Top-Abweichungen."""
        rows = self.queries.get_depot_deviation()
        chart = RankingBarChart(width=5, height=3)

        if not rows:
            chart.plot([], [], title="Top-Abweichungen")
            return chart

        # Filter anwenden (Cross-Filter)
        if self._filter_state.state.depot_ids:
            rows = [r for r in rows if r["depot_id"] in self._filter_state.state.depot_ids]

        labels = [str(r["depot_name"]) for r in rows[:10]]
        values = [abs(r["differenz"] or 0) for r in rows[:10]]
        ids = [r["depot_id"] for r in rows[:10]]

        chart.plot(labels, values, title="Abweichung (absolut)", color_key="orange",
                   ids=ids, id_type="depot")
        return chart

    def _build_deviation_table(self) -> QtWidgets.QTableWidget:
        """Soll/Ist-Tabelle aus get_depot_deviation()."""
        rows = self.queries.get_depot_deviation()

        # Cross-Filter anwenden
        if self._filter_state.state.depot_ids:
            rows = [r for r in rows if r["depot_id"] in self._filter_state.state.depot_ids]

        headers = ["Depot", "Soll", "Ist", "Differenz", "Status"]
        table = self._create_responsive_table(headers, len(rows))

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

        # Cross-Filter anwenden
        if self._filter_state.state.praeparat_ids:
            rows = [r for r in rows if r["praeparat_id"] in self._filter_state.state.praeparat_ids]

        headers = ["Präparat", "Zugang", "Abgang", "Umschlagsrate"]
        table = self._create_responsive_table(headers, len(rows))

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

        # Cross-Filter anwenden
        if self._filter_state.state.depot_ids:
            rows = [r for r in rows if str(r["depot_name"]) in
                    {str(d) for d in self._filter_state.state.depot_ids}]

        headers = ["Präparat", "Depot", "Bestand", "Letzte Bewegung"]
        table = self._create_responsive_table(headers, len(rows))

        for i, row in enumerate(rows):
            table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(row["praeparat_name"])))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(row["depot_name"])))
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(str(row["ist_bestand"])))
            last = row["letzte_bewegung"] or "—"
            table.setItem(i, 3, QtWidgets.QTableWidgetItem(str(last)))

        if not rows:
            self._add_empty_hint(table, "Kein toter Bestand — alle Präparate in Bewegung ✅")

        return table


    def _add_empty_hint(self, table: QtWidgets.QTableWidget, text: str) -> None:
        table.setRowCount(1)
        table.setItem(0, 0, QtWidgets.QTableWidgetItem(text))

    @staticmethod
    def _qcolor(hex_color: str):
        from PySide6 import QtGui
        return QtGui.QColor(hex_color)
