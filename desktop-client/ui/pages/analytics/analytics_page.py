"""Analytics Control Center — Hauptseite.

Ersetzt die alte `page_auswertungen.py` (1374 Zeilen Monolith) durch
ein dreistufiges Erlebnis:
  1. Insight-Banner (4 Smart-Cards)
  2. Globale Filter-Leiste (sticky)
  3. 4-Tab-Cluster (Bestand / Bewegungen / Verfall / Compliance)

Issue #42 Phase 1 — Foundation.
"""

from __future__ import annotations

import logging

from PySide6 import QtWidgets

from apple_theme import AppleTheme
from db_manager import Database

from ._db.analytics_queries import AnalyticsQueries
from ._filters.global_filter_bar import GlobalFilterBar
from ._filters.layout_persistence import LayoutPersistence
from ._widgets.insight_banner import InsightBanner
from ._widgets.insights_panel import InsightsPanel
from .tabs.tab_bestand import TabBestand
from .tabs.tab_bewegungen import TabBewegungen
from .tabs.tab_compliance import TabCompliance
from .tabs.tab_email import TabEmailSchedule
from .tabs.tab_sql import TabSqlEditor
from .tabs.tab_verfall import TabVerfall

logger = logging.getLogger(__name__)


class AnalyticsPage(QtWidgets.QWidget):
    """Analytics Control Center — Container mit Insight-Banner + Tabs."""

    def __init__(self, db: Database, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.db = db
        self.queries = AnalyticsQueries(db)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Scroll-Container für die gesamte Seite
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        layout.addWidget(scroll)

        content = QtWidgets.QWidget()
        scroll.setWidget(content)

        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(20)

        # Titel
        title = QtWidgets.QLabel("📊 Analytics Control Center")
        title.setProperty("class", "page-title")
        c = AppleTheme.current_colors()
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {c['label']};")
        content_layout.addWidget(title)

        # 1. Insight-Banner (Hero-Layer)
        self.insight_banner = InsightBanner(db)
        content_layout.addWidget(self.insight_banner)

        # 1b. Auto-Insights Panel (Phase 3 — "Was ist passiert?")
        self.insights_panel = InsightsPanel(db)
        content_layout.addWidget(self.insights_panel)

        # Layout-Persistenz (Phase 2)
        self.layout_persistence = LayoutPersistence(data_dir=".")

        # 2. Globale Filter-Leiste (sticky)
        self.filter_bar = GlobalFilterBar(db)
        content_layout.addWidget(self.filter_bar)

        # 3. Tab-Cluster
        self.tabs = QtWidgets.QTabWidget()
        self.tab_bestand = TabBestand(db, self.queries)
        self.tab_bewegungen = TabBewegungen(db, self.queries)
        self.tab_verfall = TabVerfall(db, self.queries)
        self.tab_compliance = TabCompliance(db, self.queries)
        self.tab_sql = TabSqlEditor(db, self.queries)
        self.tab_email = TabEmailSchedule(db, self.queries)

        self.tabs.addTab(self.tab_bestand, "📦 Bestand")
        self.tabs.addTab(self.tab_bewegungen, "🔄 Bewegungen")
        self.tabs.addTab(self.tab_verfall, "⏳ Verfall")
        self.tabs.addTab(self.tab_compliance, "🛡️ Compliance")
        self.tabs.addTab(self.tab_sql, "🔍 SQL")
        self.tabs.addTab(self.tab_email, "📧 Email")
        content_layout.addWidget(self.tabs)

        # Signal-Verkabelung
        self.filter_bar.filtersChanged.connect(self._on_filters_changed)
        self.insight_banner.insightClicked.connect(self._on_insight_clicked)

        # Initiale Daten laden
        self._load_layout()
        self.refresh()

    def refresh(self) -> None:
        """Lädt alle Daten neu (Insight-Banner + Insights-Panel + aktiver Tab)."""
        self.insight_banner.refresh()
        self.insights_panel.refresh()
        self._refresh_active_tab()

    def _refresh_active_tab(self) -> None:
        """Aktualisiert nur den aktuell sichtbaren Tab."""
        idx = self.tabs.currentIndex()
        tab = self.tabs.widget(idx)
        if hasattr(tab, "refresh"):
            tab.refresh()

    def _on_filters_changed(self) -> None:
        """Filter geändert → aktiven Tab neu laden."""
        self._refresh_active_tab()

    def _on_insight_clicked(self, insight_type: str) -> None:
        """Insight-Karte geklickt → zum passenden Tab wechseln."""
        tab_map = {
            "verfall": 2,       # ⏳ Verfall
            "deviation": 0,     # 📦 Bestand
            "inactive": 0,      # 📦 Bestand
            "trend": 1,         # 🔄 Bewegungen
        }
        idx = tab_map.get(insight_type, 0)
        self.tabs.setCurrentIndex(idx)
        self._refresh_active_tab()

    # ── Layout-Persistenz (Phase 2) ─────────────────────────────────

    def _load_layout(self) -> None:
        """Lädt gespeicherten Layout-State (aktiver Tab + Filter)."""
        state = self.layout_persistence.load_layout()
        if state is None:
            return

        try:
            idx = state.get("active_tab", 0)
            if 0 <= idx < self.tabs.count():
                self.tabs.setCurrentIndex(idx)
        except Exception:
            logger.debug("Layout-Load: Tab-Index ungültig")

    def save_layout(self) -> None:
        """Speichert aktuellen Layout-State (für App-Close oder manuellen Save)."""
        from ._filters.cross_filter_state import CrossFilterState

        filter_state = CrossFilterState.instance()
        state = {
            "active_tab": self.tabs.currentIndex(),
            "date_range_days": filter_state.state.date_range_days,
            "depot_ids": list(filter_state.state.depot_ids),
            "praeparat_ids": list(filter_state.state.praeparat_ids),
            "compare_mode": self.filter_bar.is_compare_mode(),
        }
        self.layout_persistence.save_layout(state)
