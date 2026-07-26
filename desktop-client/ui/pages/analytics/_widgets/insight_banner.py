"""Insight-Banner — 4 Smart-Cards oben im Analytics Control Center.

Jede Karte zeigt eine automatische Insight-Berechnung:
  1. 🚨 Verfälle in nächsten 30 Tagen
  2. ✅ Depot mit größter Soll/Ist-Abweichung
  3. ⚠️ Inaktive Depots (>180 Tage keine Bewegung)
  4. 📈 Zugang-Trend vs. Vorperiode

Jede Karte ist klickbar und emit ein Signal mit dem Insight-Typ für
Drill-Down-Navigation.

Issue #42 Phase 1 — Hero-Layer.
"""
from __future__ import annotations

import logging

from db_manager import Database
from PySide6 import QtCore, QtWidgets

from .sparkline_kpi_card import SparklineKpiCard

logger = logging.getLogger(__name__)


class InsightBanner(QtWidgets.QWidget):
    """4 Smart-Cards als Hero-Layer über den Tabs."""

    insightClicked = QtCore.Signal(str)  # insight_type

    def __init__(self, db: Database, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )

        self._grid = QtWidgets.QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(12)

        self.card_verfall = self._create_clickable_card("🚨", "Verfälle <30 Tage", 0, "red")
        self.card_deviation = self._create_clickable_card("✅", "Top-Abweichung", 0, "green")
        self.card_inactive = self._create_clickable_card("⚠️", "Inaktive Depots", 0, "orange")
        self.card_trend = self._create_clickable_card("📈", "Zugang-Trend", 0, "blue")
        self._cards = [
            self.card_verfall,
            self.card_deviation,
            self.card_inactive,
            self.card_trend,
        ]
        self._relayout(self.width() or 1200)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout(event.size().width())

    def _relayout(self, width: int) -> None:
        """1–4 Spalten je nach verfügbarer Breite."""
        if width < 520:
            cols = 1
        elif width < 820:
            cols = 2
        else:
            cols = 4
        # clear grid positions
        while self._grid.count():
            item = self._grid.takeAt(0)
            # widgets remain owned
            _ = item.widget()
        for i, card in enumerate(self._cards):
            r, c = divmod(i, cols)
            self._grid.addWidget(card, r, c)
            self._grid.setColumnStretch(c, 1)

    def _create_clickable_card(
        self,
        icon: str,
        title: str,
        value: int | float,
        accent: str,
    ) -> SparklineKpiCard:
        card = SparklineKpiCard(
            title=title,
            value=value,
            icon=icon,
            accent_color=accent,
        )
        card.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        card.mousePressEvent = lambda _event, t=title.lower(): self._on_card_clicked(t)
        return card

    def _on_card_clicked(self, title: str) -> None:
        if "verfäl" in title or "verfall" in title:
            self.insightClicked.emit("verfall")
        elif "abweich" in title:
            self.insightClicked.emit("deviation")
        elif "inakt" in title:
            self.insightClicked.emit("inactive")
        elif "trend" in title:
            self.insightClicked.emit("trend")

    def refresh(self) -> None:
        try:
            verfall_rows = self.db.get_verfall_warnings(days=30)
            self.card_verfall.counter.set_target(len(verfall_rows))
        except Exception:
            logger.exception("Verfall-Insight fehlgeschlagen")
            self.card_verfall.counter.set_target(0)

        try:
            deviation_rows = self.db.get_depot_deviation()
            top_dev = deviation_rows[0] if deviation_rows else None
            value = abs(top_dev["differenz"]) if top_dev else 0
            self.card_deviation.counter.set_target(value)
        except Exception:
            logger.exception("Deviation-Insight fehlgeschlagen")
            self.card_deviation.counter.set_target(0)

        try:
            inactive_rows = self.db.get_inactive_depots(days=180)
            self.card_inactive.counter.set_target(len(inactive_rows))
        except Exception:
            logger.exception("Inactive-Insight fehlgeschlagen")
            self.card_inactive.counter.set_target(0)

        try:
            trend = self.db.get_period_trend(days=7)
            pct = trend["veraenderung_pct"]
            self.card_trend.counter.set_target(pct)
        except Exception:
            logger.exception("Trend-Insight fehlgeschlagen")
            self.card_trend.counter.set_target(0)
