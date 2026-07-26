"""AppleDashboard section helpers (Issue #93)."""
from __future__ import annotations

import logging

from apple_theme import AppleTheme
from icon_manager import IconManager
from PySide6 import QtWidgets
from PySide6.QtCore import Qt

from .widgets import (
    create_card_widget,
)

logger = logging.getLogger(__name__)

def _create_activities_section(self):
    """Letzte Aktivitäten Section"""
    card = create_card_widget()
    card.setMinimumHeight(300)
    layout = QtWidgets.QVBoxLayout(card)
    layout.setContentsMargins(
        AppleTheme.SPACING['md'],
        AppleTheme.SPACING['md'],
        AppleTheme.SPACING['md'],
        AppleTheme.SPACING['md']
    )

    # Header mit Refresh Button
    header_layout = QtWidgets.QHBoxLayout()
    title = QtWidgets.QLabel("🕐 Letzte Aktivitäten")
    title.setFont(AppleTheme.get_font('headline'))
    header_layout.addWidget(title)
    header_layout.addStretch()

    self.btn_refresh = QtWidgets.QPushButton("")
    self.btn_refresh.setIcon(IconManager.get_icon("refresh"))
    self.btn_refresh.setObjectName("btn_secondary")
    self.btn_refresh.setFixedSize(36, 36)
    self.btn_refresh.clicked.connect(self.refresh_activities)
    header_layout.addWidget(self.btn_refresh)

    layout.addLayout(header_layout)

    # Scroll Area für Aktivitäten
    activity_scroll = QtWidgets.QScrollArea()
    activity_scroll.setWidgetResizable(True)
    activity_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
    activity_scroll.setMinimumHeight(240)

    self.activity_widget = QtWidgets.QWidget()
    self.activity_layout = QtWidgets.QVBoxLayout(self.activity_widget)
    self.activity_layout.setSpacing(AppleTheme.SPACING['xs'])

    activity_scroll.setWidget(self.activity_widget)
    layout.addWidget(activity_scroll)

    return card


def refresh_activities(self):
    """Lädt die letzten Bewegungen als Aktivitätenliste."""
    if not hasattr(self, "activity_layout"):
        return

    while self.activity_layout.count():
        item = self.activity_layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()

    try:
        rows = self.db.list_bewegungen_with_attachments()[:12]
    except Exception as e:
        error_label = QtWidgets.QLabel(f"Aktivitäten konnten nicht geladen werden: {e}")
        error_label.setWordWrap(True)
        error_label.setStyleSheet(f"color: {AppleTheme.current_colors()['status_red']};")
        self.activity_layout.addWidget(error_label)
        self.activity_layout.addStretch()
        return

    if not rows:
        empty_label = QtWidgets.QLabel("Noch keine Aktivitäten vorhanden.")
        empty_label.setStyleSheet(
            f"color: {AppleTheme.current_colors()['secondary_label']}; padding: 12px 8px;"
        )
        self.activity_layout.addWidget(empty_label)
        self.activity_layout.addStretch()
        return

    c = AppleTheme.current_colors()
    for row in rows:
        (
            _id,
            depot,
            praeparat,
            typ,
            _charge,
            _verfall,
            eingang,
            ausgang,
            empfaenger,
            anzahl,
            _pdf,
        ) = row

        when = eingang or ausgang or "-"
        if len(when) > 10:
            when = when[:10]

        item = QtWidgets.QFrame()
        item.setObjectName("activity_item")
        item.setStyleSheet(
            f"QFrame#activity_item {{ background-color: {c['bg_tertiary']}; border-radius: 10px; }}"
        )
        row_layout = QtWidgets.QHBoxLayout(item)
        row_layout.setContentsMargins(12, 10, 12, 10)
        row_layout.setSpacing(10)

        typ_color = c["blue"]
        if typ == "Zugang":
            typ_color = c["green"]
        elif typ in ("Abgang", "Vernichtung"):
            typ_color = c["red"] if typ == "Vernichtung" else c["orange"]

        badge = QtWidgets.QLabel(typ)
        badge.setStyleSheet(
            f"background-color: {typ_color}22; color: {typ_color}; border-radius: 8px; "
            "padding: 3px 8px; font-weight: 600; min-width: 84px;"
        )
        badge.setAlignment(Qt.AlignCenter)
        row_layout.addWidget(badge)

        info = QtWidgets.QLabel(f"{depot} - {praeparat} - {anzahl} EH")
        info.setStyleSheet(f"color: {c['label']}; font-weight: 500;")
        info.setWordWrap(True)
        row_layout.addWidget(info, 1)

        meta_text = when
        if empfaenger:
            meta_text += f" | {empfaenger}"
        meta = QtWidgets.QLabel(meta_text)
        meta.setStyleSheet(f"color: {c['secondary_label']}; font-size: 12px;")
        meta.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row_layout.addWidget(meta)

        self.activity_layout.addWidget(item)

    self.activity_layout.addStretch()

