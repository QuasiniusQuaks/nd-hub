"""Insights-Panel — zeigt Auto-Insight Bullet-Points an.

"Was ist passiert?" — 3 NL-generierte Bullet-Points im Insight-Banner-Bereich.

Issue #42 Phase 3 — Wow-Features.
"""

from __future__ import annotations

import logging

from PySide6 import QtCore, QtWidgets

from apple_theme import AppleTheme
from db_manager import Database

from .._insights.auto_insights import AutoInsightsGenerator, Insight

logger = logging.getLogger(__name__)

_SEVERITY_COLORS = {
    "danger": "red",
    "warning": "orange",
    "success": "green",
    "info": "blue",
}

_SEVERITY_BG = {
    "danger": "rgba(231, 76, 60, 0.08)",
    "warning": "rgba(255, 149, 0, 0.08)",
    "success": "rgba(39, 174, 96, 0.08)",
    "info": "rgba(52, 152, 219, 0.08)",
}


class InsightsPanel(QtWidgets.QFrame):
    """Panel mit 3 Auto-Insight Bullet-Points."""

    insightsUpdated = QtCore.Signal()

    def __init__(self, db: Database, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self.generator = AutoInsightsGenerator(db)
        self.setObjectName("insights_panel")
        self._apply_style()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header
        c = AppleTheme.current_colors()
        header = QtWidgets.QLabel("💡 Was ist passiert?")
        header.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {c['label']};"
        )
        layout.addWidget(header)

        subtitle = QtWidgets.QLabel("Automatisch generierte Insights aus deinen Daten")
        subtitle.setStyleSheet(
            f"font-size: 11px; color: {c['tertiary_label']};"
        )
        layout.addWidget(subtitle)

        # Bullet-Point Container
        self.bullets_layout = QtWidgets.QVBoxLayout()
        self.bullets_layout.setSpacing(8)
        layout.addLayout(self.bullets_layout)

        self._insight_labels: list[QtWidgets.QLabel] = []

    def _apply_style(self) -> None:
        c = AppleTheme.current_colors()
        self.setStyleSheet(
            f"""
            #insights_panel {{
                background-color: {c.get('card_bg', c.get('background', '#ffffff'))};
                border-radius: 12px;
                border: 1px solid {c.get('separator', '#e0e0e0')};
            }}
            """
        )

    def refresh(self, days: int = 7) -> None:
        """Generiert neue Insights und aktualisiert das Panel."""
        insights = self.generator.generate(days=days)

        # Alte Labels entfernen
        for label in self._insight_labels:
            label.deleteLater()
        self._insight_labels.clear()

        c = AppleTheme.current_colors()

        if not insights:
            empty = QtWidgets.QLabel("✅ Alles im grünen Bereich — keine Auffälligkeiten.")
            empty.setStyleSheet(
                f"font-size: 13px; color: {c['green']}; padding: 8px;"
            )
            self.bullets_layout.addWidget(empty)
            self._insight_labels.append(empty)
        else:
            for insight in insights:
                label = self._create_bullet_label(insight)
                self.bullets_layout.addWidget(label)
                self._insight_labels.append(label)

        self.insightsUpdated.emit()

    def _create_bullet_label(self, insight: Insight) -> QtWidgets.QLabel:
        """Erstellt ein formatiertes Label für einen Insight-Bullet."""
        c = AppleTheme.current_colors()
        color_key = _SEVERITY_COLORS.get(insight.severity, "blue")
        bg = _SEVERITY_BG.get(insight.severity, "rgba(52, 152, 219, 0.08)")
        color = c.get(color_key, c["blue"])

        label = QtWidgets.QLabel(f"{insight.icon}  {insight.text}")
        label.setWordWrap(True)
        label.setStyleSheet(
            f"""
            font-size: 13px;
            color: {c['label']};
            padding: 10px 12px;
            border-radius: 8px;
            background-color: {bg};
            border-left: 3px solid {color};
            """
        )
        return label

    def refresh_theme(self) -> None:
        """Bei Theme-Wechsel neu stylen."""
        self._apply_style()
