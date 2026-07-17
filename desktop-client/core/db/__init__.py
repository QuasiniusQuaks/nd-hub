"""Desktop DB-Layer Split (Issue #66) — Mixins für ``db_manager.Database``.
"""
from core.db.analytics import AnalyticsMixin
from core.db.analytics_charts import AnalyticsChartsMixin
from core.db.analytics_saved import AnalyticsSavedMixin

__all__ = ["AnalyticsMixin", "AnalyticsChartsMixin", "AnalyticsSavedMixin"]
