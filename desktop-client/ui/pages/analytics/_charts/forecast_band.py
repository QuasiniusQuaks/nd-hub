"""Forecast-Band-Chart mit Hover-Tooltips.

Line-Chart mit Konfidenzintervall-Band für Verfall-Prognose.
Jeder Punkt ist hover-bar mit Tooltip (Monat + Einheiten).

Issue #42 Phase 2.
"""

from __future__ import annotations

import logging

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from apple_theme import AppleTheme

from ._charts.base_chart import BaseChartCanvas, ChartElement

logger = logging.getLogger(__name__)


class ForecastBandChart(FigureCanvasQTAgg, BaseChartCanvas):
    """Line-Chart mit Konfidenz-Band für Verfall-Forecast."""

    def __init__(self, parent=None, width: float = 6, height: float = 3, dpi: int = 100) -> None:
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        self._setup_interactivity()
        AppleTheme.setup_matplotlib(None)

    def _find_element_at(self, x: float | None, y: float | None) -> ChartElement | None:
        """Hit-Test: findet den nächsten Datenpunkt zum Cursor."""
        if x is None or y is None or not self._elements:
            return None

        # Nächsten Punkt anhand der X-Koordinate finden
        best = None
        best_dist = float("inf")
        for element in self._elements:
            ex = element.metadata.get("x")
            if ex is None:
                continue
            dist = abs(ex - x)
            if dist < best_dist:
                best_dist = dist
                best = element

        # Nur zurückgeben wenn innerhalb 0.5 Einheiten (halbe Zellbreite)
        if best is not None and best_dist < 0.6:
            return best
        return None

    def plot(
        self,
        months: list[str],
        values: list[int],
        title: str = "Verfall-Forecast",
        confidence_band: list[tuple[float, float]] | None = None,
    ) -> None:
        """Zeichnet den Forecast-Chart.

        Args:
            months: X-Achsen-Labels (Monate als 'YYYY-MM').
            values: Y-Werte (verfallende Einheiten pro Monat).
            title: Chart-Titel.
            confidence_band: Optionale Liste von (lower, upper) pro Monat.
        """
        self.clear_elements()
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.2)

        c = AppleTheme.current_colors()

        if not months or not values:
            ax.text(0.5, 0.5, "Keine Forecast-Daten", ha="center", va="center",
                    transform=ax.transAxes, color=c["tertiary_label"], fontsize=12)
            ax.set_xticks([])
            ax.set_yticks([])
            self.draw_idle()
            return

        x = np.arange(len(months))

        # Konfidenz-Band (optional)
        if confidence_band and len(confidence_band) == len(values):
            lower = [cb[0] for cb in confidence_band]
            upper = [cb[1] for cb in confidence_band]
            ax.fill_between(x, lower, upper, alpha=0.2, color=c.get("orange", "#ff9500"),
                            label="Konfidenzintervall")

        # Haupt-Linie
        line = ax.plot(x, values, color=c.get("orange", "#ff9500"), linewidth=2,
                       marker="o", markersize=5, solid_capstyle="round")[0]

        # Punkte hoverbar
        for i, (month, val) in enumerate(zip(months, values, strict=False)):
            tooltip = f"{month}: {val} EH"
            self._elements.append(ChartElement(
                artist=line,
                label=tooltip,
                value=val,
                metadata={"x": i, "month": month},
            ))

        ax.set_xticks(x)
        ax.set_xticklabels(months, fontsize=8, rotation=45, ha="right")
        ax.set_title(title, fontsize=11, color=c["label"], pad=10)
        ax.set_ylabel("Einheiten", fontsize=9, color=c["secondary_label"])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color(c.get("separator", "#cccccc"))
        ax.spines["left"].set_color(c.get("separator", "#cccccc"))
        ax.tick_params(axis="x", colors=c["secondary_label"], labelsize=8)
        ax.tick_params(axis="y", colors=c["secondary_label"], labelsize=8)

        if confidence_band:
            ax.legend(fontsize=8, loc="upper right")

        self.fig.tight_layout()
        self.draw_idle()
