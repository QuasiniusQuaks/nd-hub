"""Auswertungen & Analytics — Shim für Rückwärtskompatibilität.

Diese Datei war ursprünglich ein 1374-Zeilen-Monolith. Sie wurde durch
das Analytics Control Center (ui/pages/analytics/) ersetzt.

Issue #42 Phase 1 — Architektur-Refactor.

Für die Übergangszeit bleibt AuswertungenPage als Alias für AnalyticsPage
erhalten, damit externe Importe nicht brechen.
"""

from __future__ import annotations

from ui.pages.analytics.analytics_page import AnalyticsPage as AuswertungenPage

__all__ = ["AuswertungenPage"]
