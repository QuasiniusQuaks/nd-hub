"""Desktop DB-Layer Split (Issue #66) — Mixins für ``db_manager.Database``."""
from core.db.analytics import AnalyticsMixin
from core.db.analytics_charts import AnalyticsChartsMixin
from core.db.analytics_saved import AnalyticsSavedMixin
from core.db.bewegungen import BewegungenMixin
from core.db.constants import DB, SettingKey, TableName
from core.db.email_service import EmailServiceMixin
from core.db.lookups import LookupsMixin
from core.db.setup_wizard import SetupWizardMixin
from core.db.stammdaten import StammdatenMixin
from core.db.sync_apply import SyncApplyMixin
from core.db.sync_outbox import SyncOutboxMixin
from core.db.test_data import TestDataMixin

__all__ = [
    "AnalyticsMixin",
    "AnalyticsChartsMixin",
    "AnalyticsSavedMixin",
    "BewegungenMixin",
    "DB",
    "EmailServiceMixin",
    "LookupsMixin",
    "SettingKey",
    "SetupWizardMixin",
    "StammdatenMixin",
    "SyncApplyMixin",
    "SyncOutboxMixin",
    "TableName",
    "TestDataMixin",
]
