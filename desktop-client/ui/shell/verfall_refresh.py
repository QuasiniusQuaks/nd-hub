"""MainWindow shell helpers (Issue #93)."""
from __future__ import annotations

import logging

logger = logging.getLogger("ND-Hub")
perf_logger = logging.getLogger("perf")

def _get_verfall_data_hash(self):
    """Berechnet Hash der aktuellen Verfalldaten für Change-Detection"""
    try:
        # Einfache Heuristik: Anzahl der kritischen Verfallsdaten
        kritische = self.verfallmanager.getverfallendepraeparate(kategorie='kritisch')
        achtung = self.verfallmanager.getverfallendepraeparate(kategorie='achtung')
        kritisch_count = len(kritische)
        achtung_count = len(achtung)
        return f"{kritisch_count}_{achtung_count}"
    except Exception as e:
        logger.error(f"Fehler beim Berechnen des Verfall-Hash: {e}")
        return "error"


def refresh_verfall_widgets(self) -> None:
    """Aktualisiert Verfall-Widgets nur bei tatsächlichen Änderungen (Timer-Callback)"""
    try:
        current_hash = self._get_verfall_data_hash()

        # Nur aktualisieren, wenn sich Daten geändert haben
        if current_hash != self.cache._last_verfall_hash:
            if hasattr(self.page_dashboard, 'verfall_widget'):
                self.page_dashboard.verfall_widget.refresh()

            if hasattr(self, 'verfall_indicator'):
                self.verfall_indicator.refresh()

            self.cache._last_verfall_hash = current_hash
            perf_logger.info("Verfall-Widgets aktualisiert (Daten geändert)")
        else:
            perf_logger.debug("Verfall-Widgets: Keine Änderungen, Skip Refresh")

    except Exception as e:
        logger.error(f"Fehler beim Refresh: {e}", exc_info=True)

# ============================================================
# USER ACTIONS
# ============================================================
