"""Globale Filter-Leiste — sticky oben im Analytics Control Center.

Zeigt: Zeitraum-Picker (7T / 30T / 90T / 1J / Custom), Depot-Filter,
Präparat-Filter und Refresh-Button. Wirkt auf alle Tabs und Charts.

Issue #42 Phase 1 — Tab-Layer.
"""

from __future__ import annotations

import logging

from PySide6 import QtCore, QtWidgets

from apple_theme import AppleTheme
from db_manager import Database

from ._filters.cross_filter_state import CrossFilterState

logger = logging.getLogger(__name__)

# Zeitraum-Optionen: (Label, Tage)
_DATE_RANGES = [
    ("7 Tage", 7),
    ("30 Tage", 30),
    ("90 Tage", 90),
    ("1 Jahr", 365),
]


class GlobalFilterBar(QtWidgets.QWidget):
    """Sticky Filter-Leiste mit Zeitraum-Picker, Depot- und Präparat-Filter."""

    filtersChanged = QtCore.Signal()

    def __init__(self, db: Database, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self.filter_state = CrossFilterState.instance()

        self.setObjectName("filter_bar")
        self._apply_style()

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(16)

        # Zeitraum-Picker
        lbl_zeit = QtWidgets.QLabel("Zeitraum:")
        c = AppleTheme.current_colors()
        lbl_zeit.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {c['secondary_label']};")
        layout.addWidget(lbl_zeit)

        self.combo_zeitraum = QtWidgets.QComboBox()
        for label, days in _DATE_RANGES:
            self.combo_zeitraum.addItem(label, days)
        self.combo_zeitraum.setCurrentIndex(1)  # Default: 30 Tage
        self.combo_zeitraum.currentIndexChanged.connect(self._on_filter_changed)
        layout.addWidget(self.combo_zeitraum)

        # Separator
        layout.addWidget(self._make_separator())

        # Depot-Filter (Multi-Select ComboBox — vereinfacht als Checkable ComboBox)
        lbl_depot = QtWidgets.QLabel("Depots:")
        lbl_depot.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {c['secondary_label']};")
        layout.addWidget(lbl_depot)

        self.combo_depot = self._create_multi_select_combo("Alle Depots")
        self._populate_depot_combo()
        layout.addWidget(self.combo_depot)

        # Präparat-Filter
        lbl_praep = QtWidgets.QLabel("Präparate:")
        lbl_praep.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {c['secondary_label']};")
        layout.addWidget(lbl_praep)

        self.combo_praeparat = self._create_multi_select_combo("Alle Präparate")
        self._populate_praeparat_combo()
        layout.addWidget(self.combo_praeparat)

        layout.addStretch()

        # Refresh-Button
        self.btn_refresh = QtWidgets.QPushButton("↻ Aktualisieren")
        self.btn_refresh.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self._on_refresh)
        layout.addWidget(self.btn_refresh)

    def _apply_style(self) -> None:
        c = AppleTheme.current_colors()
        self.setStyleSheet(
            f"""
            #filter_bar {{
                background-color: {c.get('card_bg', c.get('background', '#ffffff'))};
                border-bottom: 1px solid {c.get('separator', '#e0e0e0')};
            }}
            """
        )

    def _make_separator(self) -> QtWidgets.QFrame:
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.VLine)
        sep.setFixedWidth(1)
        c = AppleTheme.current_colors()
        sep.setStyleSheet(f"color: {c.get('separator', '#e0e0e0')};")
        return sep

    def _create_multi_select_combo(self, placeholder: str) -> QtWidgets.QComboBox:
        """Erstellt eine vereinfachte Multi-Select-ComboBox (Phase 1: single-select)."""
        combo = QtWidgets.QComboBox()
        combo.addItem(placeholder)
        combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        combo.setMinimumWidth(180)
        return combo

    def _populate_depot_combo(self) -> None:
        """Lädt alle Depots in die ComboBox."""
        try:
            rows = self.db.cur.execute("SELECT id, name FROM depots ORDER BY name").fetchall()
            for row in rows:
                self.combo_depot.addItem(f"  {row[1]}", row[0])
        except Exception:
            logger.exception("Depot-Combo-Population fehlgeschlagen")

    def _populate_praeparat_combo(self) -> None:
        """Lädt alle Präparate in die ComboBox."""
        try:
            rows = self.db.cur.execute("SELECT id, name FROM praeparate ORDER BY name").fetchall()
            for row in rows:
                self.combo_praeparat.addItem(f"  {row[1]}", row[0])
        except Exception:
            logger.exception("Präparat-Combo-Population fehlgeschlagen")

    def _on_filter_changed(self) -> None:
        """Filter geändert → CrossFilterState updaten + Signal emit."""
        days = self.combo_zeitraum.currentData()
        self.filter_state.set_date_range(days)
        self.filtersChanged.emit()

    def _on_refresh(self) -> None:
        """Refresh-Button → Signal emit (Page lädt alle Tabs neu)."""
        self.filtersChanged.emit()

    def get_date_range_days(self) -> int:
        """Gibt den aktuell gewählten Zeitraum in Tagen zurück."""
        return self.combo_zeitraum.currentData() or 30

    def refresh_theme(self) -> None:
        """Bei Theme-Wechsel neu stylen."""
        self._apply_style()
