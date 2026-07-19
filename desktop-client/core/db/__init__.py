"""Desktop DB-Layer Split (Issue #66) — Mixins für ``db_manager.Database``."""
from core.db.analytics import AnalyticsMixin
from core.db.analytics_charts import AnalyticsChartsMixin
from core.db.analytics_saved import AnalyticsSavedMixin
from core.db.constants import DB, SettingKey, TableName
from core.db.setup_wizard import SetupWizardMixin
from core.db.sync_apply import SyncApplyMixin
from core.db.sync_outbox import SyncOutboxMixin

__all__ = [
    "AnalyticsMixin",
    "AnalyticsChartsMixin",
    "AnalyticsSavedMixin",
    "DB",
    "SettingKey",
    "SetupWizardMixin",
    "SyncApplyMixin",
    "SyncOutboxMixin",
    "TableName",
]
