"""Glass-Card-Widget mit Glassmorphismus-Look.

Semi-transparente Card mit backdrop-blur-Effekt (simuliert via Qt-Stylesheet),
16px Border-Radius, subtilem Shadow und 1px Hairline-Border.

Issue #42 Phase 1 — Design-System.
"""

from __future__ import annotations

from apple_theme import AppleTheme
from PySide6 import QtWidgets


class GlassCard(QtWidgets.QFrame):
    """Glassmorphismus-Card mit Border-Radius, Shadow und Hairline-Border."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("glass_card")
        self._apply_style()

    def _apply_style(self) -> None:
        c = AppleTheme.current_colors()
        # backdrop-filter wird von Qt nicht nativ unterstützt;
        # semi-transparente Background-Color simuliert den Effekt.
        self.setStyleSheet(
            f"""
            #glass_card {{
                background-color: rgba({self._hex_to_rgb(c.get('card_bg', c.get('background', '#ffffff')))}, 0.85);
                border-radius: 16px;
                border: 1px solid rgba({self._hex_to_rgb(c.get('separator', '#e0e0e0'))}, 0.3);
            }}
            """
        )

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> str:
        """Konvertiert #RRGGBB nach 'r, g, b' für rgba()."""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 6:
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            return f"{r}, {g}, {b}"
        return "255, 255, 255"

    def refresh_theme(self) -> None:
        """Bei Theme-Wechsel neu stylen."""
        self._apply_style()
