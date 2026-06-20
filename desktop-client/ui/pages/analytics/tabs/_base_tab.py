"""Basis-Tab-Widget für alle Analytics-Tabs.

Stellt gemeinsame Infrastruktur bereit: refresh(), ein Scroll-Area,
und ein Card-Layout für einheitliches Design.
"""

from __future__ import annotations

import logging

from PySide6 import QtWidgets

from apple_theme import AppleTheme
from db_manager import Database

if False:  # TYPE_CHECKING
    from .._db.analytics_queries import AnalyticsQueries

logger = logging.getLogger(__name__)


class BaseTab(QtWidgets.QWidget):
    """Basis-Klasse für alle Analytics-Tabs."""

    def __init__(self, db: Database, queries: AnalyticsQueries, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self.queries = queries

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        layout.addWidget(self.scroll)

        self.content = QtWidgets.QWidget()
        self.scroll.setWidget(self.content)

        self.content_layout = QtWidgets.QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(16)

    def refresh(self) -> None:
        """Override in Subclass — lädt Tab-spezifische Daten."""
        pass

    def _make_card(self, title: str = "") -> QtWidgets.QFrame:
        """Erstellt eine Card mit optionalem Titel."""
        c = AppleTheme.current_colors()
        card = QtWidgets.QFrame()
        card.setObjectName("analytics_card")
        card.setStyleSheet(
            f"""
            #analytics_card {{
                background-color: {c.get('card_bg', c.get('background', '#ffffff'))};
                border-radius: 12px;
                border: 1px solid {c.get('separator', '#e0e0e0')};
            }}
            """
        )

        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        if title:
            lbl = QtWidgets.QLabel(title)
            lbl.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {c['label']};")
            card_layout.addWidget(lbl)

        self.content_layout.addWidget(card)
        return card

    def _clear_content(self) -> None:
        """Entfernt alle Widgets aus dem Content-Layout."""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
