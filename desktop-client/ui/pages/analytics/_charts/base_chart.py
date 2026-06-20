"""Base-Chart-Canvas mit Hover-Tooltip, Click-to-Drill und Cross-Filter.

Abstrakte Basisklasse für alle Charts im Analytics Control Center.
Stellt bereit:
  - Hover-Tooltips (Mouse-Motion → Annotation unter Cursor)
  - Click-to-Drill (Click auf Bar/Punkt → Signal mit Element-Context)
  - Cross-Filter-Integration (Click → CrossFilterState aktualisieren)
  - Theme-awarees Coloring (AppleTheme)

Issue #42 Phase 2 — Interaktivität.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from PySide6 import QtCore

from apple_theme import AppleTheme

logger = logging.getLogger(__name__)


@dataclass
class ChartElement:
    """Metadaten für ein klickbares/beschreibbares Chart-Element.

    Wird von Subklassen beim Plotten gefüllt. Jedes Element hat
    artist (matplotlib Artist), label, und optionale filter-Daten
    (depot_id, praeparat_id) für Cross-Filtering.
    """

    artist: Any = None  # matplotlib Artist (BarContainer, Line2D, etc.)
    label: str = ""
    value: float | int = 0
    depot_id: int | None = None
    praeparat_id: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseChartCanvas:
    """Mix-in für matplotlib FigureCanvasQTAgg mit Tooltip + Click-Handler.

    Subklassen müssen:
      1. In `plot()` die `_elements`-Liste füllen (ChartElement pro Bar/Punkt)
      2. `super().plot()` aufrufen (verbindet Event-Handler)

    Subklassen erben von FigureCanvasQTAgg UND BaseChartCanvas:
        class MyChart(FigureCanvasQTAgg, BaseChartCanvas): ...
    """

    # Signale — werden in __init_subclass__ oder __init__ als QtCore.Signal erstellt
    # Da FigureCanvasQTAgg schon QObject ist, können wir Signale direkt definieren
    elementClicked = QtCore.Signal(object)  # ChartElement
    drillRequested = QtCore.Signal(str, dict)  # (drill_type, context_dict)

    def _setup_interactivity(self) -> None:
        """Verbindet matplotlib-Event-Handler. In __init__ nach super().__init__() aufrufen."""
        self._elements: list[ChartElement] = []
        self._tooltip_annotation = None
        self._hover_element: ChartElement | None = None

        # Mouse-Motion → Hover-Tooltip
        self.mpl_connect("motion_notify_event", self._on_motion)
        # Button-Press → Click-to-Drill + Cross-Filter
        self.mpl_connect("button_press_event", self._on_click)

    def _on_motion(self, event) -> None:
        """Hover-Tooltip: zeigt Annotation wenn Maus über Chart-Element."""
        if event.inaxes != self.figure.axes[0] if self.figure.axes else None:
            return

        element = self._find_element_at(event.xdata, event.ydata)
        if element is self._hover_element:
            return  # Kein Wechsel → nichts tun

        self._hover_element = element
        ax = self.figure.axes[0] if self.figure.axes else None
        if ax is None:
            return

        # Alte Annotation entfernen
        if self._tooltip_annotation is not None:
            self._tooltip_annotation.remove()
            self._tooltip_annotation = None

        if element is not None and element.label:
            # Neue Annotation erstellen
            c = AppleTheme.current_colors()
            self._tooltip_annotation = ax.annotate(
                element.label,
                xy=(event.xdata, event.ydata),
                xytext=(10, 10),
                textcoords="offset points",
                bbox={
                    "boxstyle": "round,pad=0.3",
                    "facecolor": c.get("card_bg", c.get("background", "#ffffff")),
                    "edgecolor": c.get("separator", "#cccccc"),
                    "alpha": 0.95,
                },
                fontsize=9,
                color=c.get("label", "#2c3e50"),
            )
            self.draw_idle()

    def _on_click(self, event) -> None:
        """Click-to-Drill + Cross-Filter: Element unter Cursor finden + Signal."""
        if event.inaxes != self.figure.axes[0] if self.figure.axes else None:
            return
        if event.button != 1:  # Nur Linksklick
            return

        element = self._find_element_at(event.xdata, event.ydata)
        if element is None:
            return

        logger.debug("Chart-Element geklickt: %s (depot=%s, praep=%s)",
                      element.label, element.depot_id, element.praeparat_id)

        # Signal emit
        self.elementClicked.emit(element)

        # Cross-Filter anwenden
        self._apply_cross_filter(element)

        # Drill-Context bauen
        drill_context = {
            "label": element.label,
            "value": element.value,
            "depot_id": element.depot_id,
            "praeparat_id": element.praeparat_id,
            "metadata": element.metadata,
        }
        self.drillRequested.emit("element", drill_context)

    def _find_element_at(self, x: float | None, y: float | None) -> ChartElement | None:
        """Findet das ChartElement unter den gegebenen Koordinaten.

        Default-Implementation: iteriert über _elements und prüft
        contains(). Subklassen können dies für komplexere Hit-Tests
        überschreiben (z.B. Heatmap mit 2D-Grid).
        """
        if x is None or y is None:
            return None

        for element in self._elements:
            if element.artist is None:
                continue
            try:
                contains, _ = element.artist.contains({"x": x, "y": y})
                if contains:
                    return element
            except (TypeError, AttributeError, ValueError):
                continue
        return None

    def _apply_cross_filter(self, element: ChartElement) -> None:
        """Wendet Cross-Filter an wenn Element depot_id oder praeparat_id hat."""
        try:
            from ._filters.cross_filter_state import CrossFilterState

            filter_state = CrossFilterState.instance()
            if element.depot_id is not None:
                # Toggle: wenn schon gefiltert → entfernen, sonst setzen
                current = filter_state.state.depot_ids
                if element.depot_id in current:
                    current = current - {element.depot_id}
                else:
                    current = {element.depot_id}
                filter_state.set_depot_filter(current)
            elif element.praeparat_id is not None:
                current = filter_state.state.praeparat_ids
                if element.praeparat_id in current:
                    current = current - {element.praeparat_id}
                else:
                    current = {element.praeparat_id}
                filter_state.set_praeparat_filter(current)
        except Exception:
            logger.debug("Cross-Filter nicht angewendet (FilterState nicht verfügbar)")

    def clear_elements(self) -> None:
        """Leert die Element-Liste (vor neuem plot())."""
        self._elements = []
        self._hover_element = None
        if self._tooltip_annotation is not None:
            try:
                self._tooltip_annotation.remove()
            except ValueError:
                pass  # schon entfernt
            self._tooltip_annotation = None

    def apply_theme(self) -> None:
        """Wendet AppleTheme auf die Figure an. Override in Subclass für Details."""
        AppleTheme.setup_matplotlib(None)  # Setup global rcParams
        self.draw_idle()
