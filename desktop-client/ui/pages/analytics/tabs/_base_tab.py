"""Basis-Tab-Widget für alle Analytics-Tabs.

Stellt gemeinsame Infrastruktur bereit: refresh(), ein Scroll-Area,
und ein Card-Layout für einheitliches Design.
"""
from __future__ import annotations

import logging

from apple_theme import AppleTheme
from db_manager import Database
from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView

if False:  # TYPE_CHECKING
    from .._db.analytics_queries import AnalyticsQueries

logger = logging.getLogger(__name__)


class BaseTab(QtWidgets.QWidget):
    """Basis-Klasse für alle Analytics-Tabs."""

    def __init__(self, db: Database, queries: AnalyticsQueries, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self.queries = queries
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        layout.addWidget(self.scroll)

        self.content = QtWidgets.QWidget()
        self.content.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Minimum,
        )
        self.scroll.setWidget(self.content)

        self.content_layout = QtWidgets.QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(12, 12, 12, 12)
        self.content_layout.setSpacing(16)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        # Content an Viewport-Breite klemmen
        vp_w = self.scroll.viewport().width()
        if vp_w > 0:
            self.content.setMaximumWidth(vp_w)
            self.content.setMinimumWidth(min(vp_w, 200))

    def refresh(self) -> None:
        """Override in Subclass — lädt Tab-spezifische Daten."""
        pass

    def _make_card(self, title: str = "") -> QtWidgets.QFrame:
        """Erstellt eine Card mit optionalem Titel."""
        c = AppleTheme.current_colors()
        card = QtWidgets.QFrame()
        card.setObjectName("analytics_card")
        card.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
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
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        if title:
            lbl = QtWidgets.QLabel(title)
            lbl.setWordWrap(True)
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

    def _create_responsive_table(self, headers: list[str], row_count: int) -> QtWidgets.QTableWidget:
        """Tabelle, die die Parent-Breite nutzt statt horizontal auszuufern."""
        table = QtWidgets.QTableWidget(row_count, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setWordWrap(False)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        table.setMinimumHeight(min(60 + max(row_count, 1) * 28, 360))

        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        # Erste Spalten stretch/interactive, keine ResizeToContents-Explosion
        for col in range(len(headers)):
            if col == 0:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
            elif col == len(headers) - 1:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
            else:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        return table
