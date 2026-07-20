"""Heatmap-Chart mit Hover-Tooltips und Click-to-Drill.

2D-Heatmap für Soll/Ist-Matrix (Depot × Präparat).
Jede Zelle ist klickbar → Cross-Filter.

Issue #42 Phase 2 — Lesbarkeit für große Matrizen optimiert.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from matplotlib import colors as mcolors
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from apple_theme import AppleTheme

from .base_chart import BaseChartCanvas, ChartElement

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _shorten(text: str, max_len: int = 22) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


class HeatmapChart(FigureCanvasQTAgg, BaseChartCanvas):
    """2D-Heatmap (Depot × Präparat) mit Hover-Tooltips und Click-to-Filter."""

    def __init__(self, parent=None, width: float = 6, height: float = 4, dpi: int = 100) -> None:
        self.fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=False)
        super().__init__(self.fig)
        self.setParent(parent)
        self._setup_interactivity()
        AppleTheme.setup_matplotlib(None)
        # Heatmaps brauchen mehr vertikale Luft für lesbare Zeilenlabels
        self.enable_responsive_size(min_height_px=480)
        self._cell_rects: list = []

    def sizeHint(self):  # noqa: N802
        from PySide6 import QtCore

        h = int(getattr(self, "_responsive_min_height", 480))
        return QtCore.QSize(480, h)

    def minimumSizeHint(self):  # noqa: N802
        from PySide6 import QtCore

        h = int(getattr(self, "_responsive_min_height", 320))
        return QtCore.QSize(200, max(240, h // 2))

    def resizeEvent(self, event) -> None:  # noqa: N802
        FigureCanvasQTAgg.resizeEvent(self, event)
        self._fit_figure_to_widget()

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
        title: str = "Soll/Ist-Differenz (Ist − Soll)",
        depot_ids: list[int] | None = None,
        praeparat_ids: list[int] | None = None,
        subtitle: str = "",
    ) -> None:
        """Zeichnet die Heatmap mit besserer Lesbarkeit."""
        self.clear_elements()
        self._cell_rects = []
        self.fig.clear()
        ax = self.fig.add_subplot(111)

        c = AppleTheme.current_colors()
        label_color = c.get("label", "#2c3e50")
        secondary = c.get("secondary_label", "#7f8c8d")
        face = c.get("bg_secondary", c.get("bg_primary", "#ffffff"))
        self.fig.patch.set_facecolor(face)
        ax.set_facecolor(face)

        if values.size == 0 or len(depot_names) == 0 or len(praeparat_names) == 0:
            ax.text(
                0.5,
                0.5,
                "Keine Daten für Heatmap",
                ha="center",
                va="center",
                transform=ax.transAxes,
                color=secondary,
                fontsize=13,
            )
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
            self.draw_idle()
            return

        n_rows, n_cols = len(depot_names), len(praeparat_names)
        values = np.asarray(values, dtype=float)

        # Diverging colormap, 0 = neutral
        vmax = float(max(abs(np.nanmin(values)), abs(np.nanmax(values)), 1.0))
        norm = mcolors.TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
        cmap = "RdYlGn"

        im = ax.imshow(
            values,
            cmap=cmap,
            norm=norm,
            aspect="auto",
            interpolation="nearest",
            origin="upper",
        )

        # Subtile Zellgitter für Orientierung
        ax.set_xticks(np.arange(-0.5, n_cols, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, n_rows, 1), minor=True)
        ax.grid(which="minor", color=c.get("separator", "#e1e8ed"), linestyle="-", linewidth=0.6, alpha=0.9)
        ax.tick_params(which="minor", bottom=False, left=False)

        # Adaptive Schriftgrößen
        y_fs = 11 if n_rows <= 8 else (10 if n_rows <= 14 else 8)
        x_fs = 10 if n_cols <= 12 else (9 if n_cols <= 18 else (8 if n_cols <= 28 else 7))
        cell_fs = 10 if n_cols * n_rows <= 80 else (8 if n_cols * n_rows <= 160 else 0)

        y_labels = [_shorten(n, 28) for n in depot_names]
        x_labels = [_shorten(n, 20 if n_cols <= 16 else 14) for n in praeparat_names]

        ax.set_xticks(np.arange(n_cols))
        ax.set_xticklabels(x_labels, fontsize=x_fs, rotation=40, ha="right", rotation_mode="anchor", color=label_color)
        ax.set_yticks(np.arange(n_rows))
        ax.set_yticklabels(y_labels, fontsize=y_fs, color=label_color)
        ax.tick_params(axis="both", colors=label_color, length=0)

        ax.set_title(title, fontsize=13, fontweight="600", color=label_color, pad=12)
        if subtitle:
            ax.text(
                0.0,
                1.02,
                subtitle,
                transform=ax.transAxes,
                fontsize=9,
                color=secondary,
                ha="left",
                va="bottom",
            )

        # Colorbar mit Beschriftung
        cbar = self.fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
        cbar.set_label("Ist − Soll", fontsize=9, color=secondary)
        cbar.ax.tick_params(labelsize=8, colors=secondary)

        # Zellwerte nur wenn genügend Platz
        for i in range(n_rows):
            for j in range(n_cols):
                val = int(values[i, j])
                if cell_fs:
                    # Kontrast je nach Zellenfarbe
                    intensity = abs(val) / vmax if vmax else 0
                    text_color = "#ffffff" if intensity > 0.55 else label_color
                    weight = "bold" if val != 0 else "normal"
                    display = f"{val:+d}" if val != 0 else "0"
                    ax.text(
                        j,
                        i,
                        display,
                        ha="center",
                        va="center",
                        fontsize=cell_fs,
                        color=text_color,
                        fontweight=weight,
                    )

                d_id = depot_ids[i] if depot_ids else None
                p_id = praeparat_ids[j] if praeparat_ids else None
                tooltip = f"{depot_names[i]} × {praeparat_names[j]}: {val:+d}"
                self._elements.append(
                    ChartElement(
                        artist=None,
                        label=tooltip,
                        value=val,
                        depot_id=d_id,
                        praeparat_id=p_id,
                        metadata={
                            "x0": j - 0.5,
                            "x1": j + 0.5,
                            "y0": i - 0.5,
                            "y1": i + 0.5,
                        },
                    )
                )

        # Mehr Platz für lange Labels
        left = 0.18 if n_rows <= 10 else 0.22
        bottom = 0.22 if n_cols <= 14 else (0.28 if n_cols <= 24 else 0.34)
        self.fig.subplots_adjust(left=left, right=0.90, top=0.88, bottom=bottom)
        self.draw_idle()
