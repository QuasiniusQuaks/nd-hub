"""Analytics-Query-Delegationsschicht.

Kapselt alle Analytics-DB-Aufrufe hinter einer sauberen Schnittstelle.
Die eigentlichen SQL-Queries liegen in ``core.db.analytics*`` (Mixins auf
``db_manager.Database``); hier wird nur delegiert — mit optionaler
Cross-Filter-Anwendung.

Issue #42 Phase 1 — Schicht-Trennung; SQL-Ort Issue #66.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from db_manager import Database

logger = logging.getLogger(__name__)


class AnalyticsQueries:
    """Delegationsschicht für Analytics-Queries mit Cross-Filter-Support.

    Alle Methoden delegieren an die entsprechenden Database-Methoden.
    Cross-Filter (depot_ids, praeparat_ids) werden in Phase 2 angewendet;
    Phase 1 nutzt nur den Zeitraum-Filter.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    # ── Insight-Banner ──────────────────────────────────────────────

    def get_verfall_warnings(self, days: int = 30) -> list:
        return self.db.get_verfall_warnings(days=days)

    def get_depot_deviation(self) -> list:
        return self.db.get_depot_deviation()

    def get_inactive_depots(self, days: int = 180) -> list:
        return self.db.get_inactive_depots(days=days)

    def get_period_trend(self, days: int = 7) -> dict:
        return self.db.get_period_trend(days=days)

    # ── Sparklines ──────────────────────────────────────────────────

    def get_kpi_sparkline(self, metric: str = "zugang", days: int = 7) -> list[int]:
        return self.db.get_kpi_sparkline(metric=metric, days=days)

    # ── Bestand-Tab ─────────────────────────────────────────────────

    def get_bestandsentwicklung(self, depot_ids=None, praeparat_ids=None) -> list:
        return self.db.get_bestandsentwicklung(depot_ids=depot_ids, praeparat_ids=praeparat_ids)

    def get_matrix_data(self) -> list:
        return self.db.get_matrix_data()

    def get_inventory_turnover(self) -> list:
        return self.db.get_inventory_turnover()

    def get_dead_stock(self, days: int = 180) -> list:
        return self.db.get_dead_stock(days=days)

    # ── Bewegungen-Tab ──────────────────────────────────────────────

    def get_bewegungen_analyse(
        self, depot_ids=None, praeparat_ids=None, start_date=None, end_date=None
    ) -> list:
        return self.db.get_bewegungen_analyse(
            depot_ids=depot_ids,
            praeparat_ids=praeparat_ids,
            start_date=start_date,
            end_date=end_date,
        )

    def get_depot_ranking(self, praeparat_ids=None, start_date=None, end_date=None, limit=10) -> list:
        return self.db.get_depot_ranking(
            praeparat_ids=praeparat_ids, start_date=start_date, end_date=end_date, limit=limit
        )

    def get_praeparat_ranking(self, depot_ids=None, start_date=None, end_date=None, limit=10) -> list:
        return self.db.get_praeparat_ranking(
            depot_ids=depot_ids, start_date=start_date, end_date=end_date, limit=limit
        )

    def get_top_movers(self, direction: str = "out", limit: int = 10, days: int = 30) -> list:
        return self.db.get_top_movers(direction=direction, limit=limit, days=days)

    # ── Verfall-Tab ─────────────────────────────────────────────────

    def get_verfall_forecast(self, months: int = 12) -> list:
        return self.db.get_verfall_forecast(months=months)

    # ── Compliance-Tab ──────────────────────────────────────────────

    def get_compliance_overview(self) -> dict:
        return self.db.get_compliance_overview()

    # ── Erweiterte Analytics ────────────────────────────────────────

    def get_anomalies(self, threshold_std: float = 2.0) -> list:
        return self.db.get_anomalies(threshold_std=threshold_std)

    def get_period_comparison(
        self,
        period_a_start: str,
        period_a_end: str,
        period_b_start: str,
        period_b_end: str,
    ) -> dict:
        return self.db.get_period_comparison(
            period_a_start, period_a_end, period_b_start, period_b_end
        )
