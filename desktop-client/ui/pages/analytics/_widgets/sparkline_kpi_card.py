"""Sparkline-KPI-Card — KPI mit Mini-Chart (7-Tage-Verlauf).

Kombiniert AnimatedCounter mit einer Sparkline (Mini-Line-Chart via
matplotlib). Apple-Health-Style.

Issue #42 Phase 1 — Wow-Details.
"""

from __future__ import annotations

import logging

from PySide6 import QtWidgets

from apple_theme import AppleTheme

from .animated_counter import AnimatedCounter
from .glass_card import GlassCard

logger = logging.getLogger(__name__)


class SparklineKpiCard(GlassCard):
    """KPI-Card mit Titel, animiertem Zähler und Sparkline.

    Args:
        title: KPI-Bezeichnung (z.B. "Verfälle <30 Tage").
        value: Aktueller Wert.
        icon: Emoji-Icon (z.B. "🚨").
        accent_color: Farbe für Wert und Sparkline (hex oder AppleTheme-key).
        sparkline_data: Liste von int/float für Mini-Chart.
    """

    def __init__(
        self,
        title: str = "",
        value: int | float = 0,
        icon: str = "",
        accent_color: str | None = None,
        sparkline_data: list[int | float] | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._accent_color = accent_color
        self._sparkline_data = sparkline_data or []

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        # Icon + Titel (horizontal)
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setSpacing(6)
        if icon:
            lbl_icon = QtWidgets.QLabel(icon)
            lbl_icon.setStyleSheet("font-size: 18px;")
            header_layout.addWidget(lbl_icon)

        self.lbl_title = QtWidgets.QLabel(title)
        c = AppleTheme.current_colors()
        self.lbl_title.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {c['tertiary_label']};"
        )
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Animated Counter
        color = self._resolve_color(accent_color)
        self.counter = AnimatedCounter(value)
        self.counter.setStyleSheet(f"font-size: 28px; font-weight: 700; color: {color};")
        layout.addWidget(self.counter)

        # Sparkline (matplotlib)
        self._spark_canvas: QtWidgets.QWidget | None = None
        if sparkline_data:
            self._build_sparkline(color)
        else:
            layout.addStretch()

    def _resolve_color(self, color: str | None) -> str:
        """Löst einen AppleTheme-Key oder Hex-Wert auf."""
        if not color:
            return AppleTheme.current_colors()["blue"]
        c = AppleTheme.current_colors()
        return c.get(color, color)

    def _build_sparkline(self, color: str) -> None:
        """Erstellt eine Mini-Sparkline via matplotlib."""
        try:
            import numpy as np
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
        except ImportError:
            logger.warning("matplotlib/numpy nicht verfügbar — Sparkline deaktiviert")
            return

        fig = Figure(figsize=(2.0, 0.5), dpi=60)
        fig.patch.set_alpha(0)
        ax = fig.add_subplot(111)
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

        data = self._sparkline_data
        if len(data) < 2:
            return

        x = np.arange(len(data))
        ax.plot(x, data, color=color, linewidth=1.5, solid_capstyle="round")
        ax.fill_between(x, data, min(data) - 1, color=color, alpha=0.15)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)

        canvas = FigureCanvasQTAgg(fig)
        canvas.setFixedSize(160, 40)
        self._spark_canvas = canvas

        layout = self.layout()
        if isinstance(layout, QtWidgets.QVBoxLayout):
            layout.addWidget(canvas)

    def update_value(self, value: int | float, sparkline_data: list[int | float] | None = None) -> None:
        """Aktualisiert Wert (mit Animation) und optional die Sparkline."""
        self.counter.animate_to(value)
        if sparkline_data is not None and sparkline_data != self._sparkline_data:
            self._sparkline_data = sparkline_data
            # Sparkline neu zeichnen — für Phase 1 vereinfacht: nur bei Neubau
            logger.debug("Sparkline update deferred to next full refresh")
