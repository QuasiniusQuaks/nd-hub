"""Heatmap-Chart mit Hover-Tooltips und Click-to-Drill.

2D-Heatmap für Soll/Ist-Matrix (Depot × Präparat).
Jede Zelle ist klickbar → Cross-Filter.

Issue #42 Phase 2.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from apple_theme import AppleTheme

from ._charts.base_chart import BaseChartCanvas, ChartElement

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class HeatmapChart(FigureCanvasQTAgg, BaseChartCanvas):
    """2D-Heatmap (Depot × Präparat) mit Hover-Tooltips und Click-to-Filter."""

    def __init__(self, parent=None, width: float = 6, height: float = 4, dpi: int = 100) -> None:
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        self._setup_interactivity()
        AppleTheme.setup_matplotlib(None)
        self._cell_rects: list = []  # Für Hit-Test

    def _find_element_at(self, x: float | None, y: float | None) -> ChartElement | None:
        """Überschrieben: Hit-Test über 2D-Zell-Grid statt Artist.contains()."""
        if x is None or y is None:
            return None
        for element in self._elements:
            meta = element.metadata
            if "x0" in meta and "x1" in meta and "y0" in meta and "y1" in meta:
                if meta["x0"] <= x <= meta["x1"] and meta["y0"] <= y <= meta["y1"]:
                    return element
        return None

    def plot(
        self,
        depot_names: list[str],
        praeparat_names: list[str],
        values: np.ndarray,
        title: str = "Soll/Ist-Heatmap",
        depot_ids: list[int] | None = None,
        praeparat_ids: list[int] | None = None,
    ) -> None:
        """Zeichnet die Heatmap.

        Args:
            depot_names: Y-Achsen-Labels (Depots).
            praeparat_names: X-Achsen-Labels (Präparate).
            values: 2D-Array (len(depot_names) × len(praeparat_names)).
            title: Chart-Titel.
            depot_ids: IDs für Cross-Filter (Y-Achse).
            praeparat_ids: IDs für Cross-Filter (X-Achse).
        """
        self.clear_elements()
        self._cell_rects = []
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(left=0.2, right=0.95, top=0.9, bottom=0.2)

        c = AppleTheme.current_colors()

        if values.size == 0 or len(depot_names) == 0 or len(praeparat_names) == 0:
            ax.text(0.5, 0.5, "Keine Daten", ha="center", va="center",
                    transform=ax.transAxes, color=c["tertiary_label"], fontsize=12)
            ax.set_xticks([])
            ax.set_yticks([])
            self.draw_idle()
            return

        # Color-Norm: negativ=rot, 0=neutral, positiv=grün
        vmax = max(abs(values.min()), abs(values.max()), 1)
        im = ax.imshow(values, cmap="RdYlGn", vmin=-vmax, vmax=vmax, aspect="auto")

        # Achsen
        ax.set_xticks(np.arange(len(praeparat_names)))
        ax.set_xticklabels(praeparat_names, fontsize=8, rotation=45, ha="right")
        ax.set_yticks(np.arange(len(depot_names)))
        ax.set_yticklabels(depot_names, fontsize=9)
        ax.set_title(title, fontsize=11, color=c["label"], pad=10)

        # Colorbar
        self.fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        # Zellen-Werte + ChartElements
        for i in range(len(depot_names)):
            for j in range(len(praeparat_names)):
                val = values[i, j]
                # Text in Zelle
                text_color = "white" if abs(val) > vmax * 0.6 else c["label"]
                ax.text(j, i, f"{val:+d}", ha="center", va="center",
                        fontsize=7, color=text_color)

                # ChartElement mit Zell-Koordinaten für Hit-Test
                d_id = depot_ids[i] if depot_ids else None
                p_id = praeparat_ids[j] if praeparat_ids else None
                tooltip = f"{depot_names[i]} × {praeparat_names[j]}: {val:+d}"
                self._elements.append(ChartElement(
                    artist=None,
                    label=tooltip,
                    value=int(val),
                    depot_id=d_id,
                    praeparat_id=p_id,
                    metadata={
                        "x0": j - 0.5, "x1": j + 0.5,
                        "y0": i - 0.5, "y1": i + 0.5,
                    },
                ))

        self.fig.tight_layout()
        self.draw_idle()
