"""AppleDashboard section helpers (Issue #93)."""
from __future__ import annotations

import logging

from apple_theme import AppleTheme
from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from verfall_widget import VerfallWidget

from ui.dialogs.embedded_dialog_host import exec_embedded_dialog
from ui.dialogs.verfall_detail_dialog import VerfallDetailDialog

from .widgets import (
    create_card_widget,
)

logger = logging.getLogger(__name__)

def _create_verfall_section(self):
    """Verfallswarnungen Section - Nutzt externes VerfallWidget"""
    card = create_card_widget()
    # Keine feste Mindesthöhe hier, damit es responsiv bleibt
    card.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)

    layout = QtWidgets.QVBoxLayout(card)
    layout.setContentsMargins(0, 0, 0, 0)

    card.setStyleSheet("QFrame { border: none; }")  # ← NEU!

    # Prüfe ob VerfallManager verfügbar ist
    if hasattr(self, 'verfallmanager') and self.verfallmanager:
        # Erstelle VerfallWidget
        self.verfall_widget = VerfallWidget(self.verfallmanager)

        # Verbinde Signal mit Dialog
        self.verfall_widget.detailsrequested.connect(self.show_verfall_details)

        layout.addWidget(self.verfall_widget)
    else:
        # Fallback wenn kein Manager verfügbar
        no_data = QtWidgets.QLabel("Verfallmanager nicht verfügbar")
        no_data.setAlignment(Qt.AlignCenter)
        no_data.setStyleSheet(f"""
            color: {AppleTheme.current_colors()['tertiary_label']};
            font-style: italic;
            padding: 30px;
        """)
        layout.addWidget(no_data)

    return card


def show_verfall_details(self):
    """Öffnet Verfall-Details als integrierten Overlay-Dialog."""
    try:
        dialog = VerfallDetailDialog(self.verfallmanager, self)
        exec_embedded_dialog(self, dialog)
        if hasattr(self, "verfall_widget"):
            self.verfall_widget.refresh()
    except Exception as e:
        QtWidgets.QMessageBox.critical(
            self,
            "Fehler",
            f"Konnte Verfall-Details nicht öffnen:\n{str(e)}"
        )
        import logging
        logging.error(f"Fehler in show_verfall_details: {e}")

