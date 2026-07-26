"""AppleDashboard section helpers (Issue #93)."""
from __future__ import annotations

import logging

from apple_theme import AppleTheme
from PySide6 import QtWidgets
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)

def __init__(self, db, verfallmanager=None, parent=None):
    self.db = db
    self.verfallmanager = verfallmanager  # HIER setzen, VOR setupui()
    super().__init__(parent)
    self._setup_ui()

    # Daten laden
    self.refresh_tracking()
    self.refresh_activities()


def _setup_ui(self):
    """UI initialisieren"""
    main_layout = QtWidgets.QVBoxLayout(self)
    main_layout.setContentsMargins(0, 0, 0, 0)

    # Scroll Area
    scroll = QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

    # Container
    self.container = QtWidgets.QWidget()
    self.container.setObjectName("dashboard_container")

    # Vertikales Layout für Sections
    self.sections_layout = QtWidgets.QVBoxLayout(self.container)
    self.sections_layout.setSpacing(AppleTheme.SPACING['md'])
    self.sections_layout.setContentsMargins(
        AppleTheme.SPACING['lg'],
        AppleTheme.SPACING['lg'],
        AppleTheme.SPACING['lg'],
        AppleTheme.SPACING['lg']
    )

    # Header erstellen
    self._create_header()

    # Cards erstellen
    self._create_cards()

    scroll.setWidget(self.container)
    main_layout.addWidget(scroll)

