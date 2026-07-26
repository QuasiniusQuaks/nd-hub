"""Ranking-Bar-Chart mit Hover-Tooltips und Click-to-Drill.

Horizontaler Bar-Chart für Rankings (Top-Depots, Top-Präparate).
Jede Bar ist klickbar → Cross-Filter + Drill-Down.

Issue #42 Phase 2.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from apple_theme import AppleTheme
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from .base_chart import BaseChartCanvas, ChartElement

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class RankingBarChart(FigureCanvasQTAgg, BaseChartCanvas):
    """Horizontaler Bar-Chart mit Hover-Tooltips und Click-to-Filter."""

    def __init__(self, parent=None, width: float = 5, height: float = 3, dpi: int = 100) -> None:
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        self._setup_interactivity()
        AppleTheme.setup_matplotlib(None)
        self.enable_responsive_size(min_height_px=300)


    def sizeHint(self):  # noqa: N802
        from PySide6 import QtCore
        h = int(getattr(self, "_responsive_min_height", 320))
        return QtCore.QSize(400, h)

    def minimumSizeHint(self):  # noqa: N802
        from PySide6 import QtCore
        h = int(getattr(self, "_responsive_min_height", 240))
        return QtCore.QSize(120, max(160, h // 2))

    def resizeEvent(self, event) -> None:  # noqa: N802
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
        FigureCanvasQTAgg.resizeEvent(self, event)
        self._fit_figure_to_widget()

    def plot(
        self,
        labels: list[str],
        values: list[int | float],
        title: str = "",
        color_key: str = "blue",
        ids: list[int | None] | None = None,
        id_type: str = "depot",
    ) -> None:
        """Zeichnet den Bar-Chart.

        Args:
            labels: Beschriftungen der Bars (z.B. Depot-Namen).
            values: Werte der Bars.
            title: Chart-Titel.
            color_key: AppleTheme-Farbkey ('blue', 'green', 'red', 'orange').
            ids: Optionale IDs für Cross-Filter (depot_id oder praeparat_id).
            id_type: 'depot' oder 'praeparat' — bestimmt welche Filter-Klasse.
        """
        self.clear_elements()
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(left=0.25, right=0.95, top=0.9, bottom=0.1)

        c = AppleTheme.current_colors()
        bar_color = c.get(color_key, c["blue"])

        if not labels or not values:
            ax.text(0.5, 0.5, "Keine Daten", ha="center", va="center",
                    transform=ax.transAxes, color=c["tertiary_label"], fontsize=12)
            ax.set_xticks([])
            ax.set_yticks([])
            self.draw_idle()
            return

        y_pos = np.arange(len(labels))
        bars = ax.barh(y_pos, values, color=bar_color, height=0.6, edgecolor="none")

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_title(title, fontsize=11, color=c["label"], pad=10)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color(c.get("separator", "#cccccc"))
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="x", colors=c["secondary_label"], labelsize=8)
        ax.tick_params(axis="y", colors=c["label"], labelsize=9)
        ax.invert_yaxis()  # Top-Wert oben

        # ChartElement pro Bar
        for i, (bar, label, value) in enumerate(zip(bars, labels, values, strict=False)):
            depot_id = ids[i] if ids and id_type == "depot" else None
            praeparat_id = ids[i] if ids and id_type == "praeparat" else None
            tooltip = f"{label}: {value}"
            self._elements.append(ChartElement(
                artist=bar,
                label=tooltip,
                value=value,
                depot_id=depot_id,
                praeparat_id=praeparat_id,
            ))

        self.fig.tight_layout()
        self.draw_idle()
