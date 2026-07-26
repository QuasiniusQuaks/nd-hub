"""Tests für Phase 2 Features: Saved Views, CrossFilterState, LayoutPersistence.

Issue #42 Phase 2 — Interaktivität.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from db_manager import Database


@pytest.fixture
def test_db():
    """Erstellt eine Test-DB für Saved-Views-CRUD."""
    db_path = tempfile.mktemp(suffix="_savedviews_test.db")
    db = Database(db_path)
    yield db
    db.conn.close()
    Path(db_path).unlink(missing_ok=True)


class TestSavedViewsCRUD:
    """Tests für die analytics_saved_views-Tabelle."""

    def test_save_and_get_view(self, test_db):
        """View speichern und laden."""
        filter_json = json.dumps({"date_range_days": 30, "depot_ids": [1, 2]})
        success = test_db.save_analytics_view("Mein Morgen-Report", filter_json)
        assert success

        view = test_db.get_analytics_view("Mein Morgen-Report")
        assert view is not None
        assert view["name"] == "Mein Morgen-Report"
        assert json.loads(view["filter_json"])["date_range_days"] == 30

    def test_upsert_existing_view(self, test_db):
        """View mit gleichem Namen wird überschrieben (upsert)."""
        test_db.save_analytics_view("Test-View", json.dumps({"days": 7}))
        test_db.save_analytics_view("Test-View", json.dumps({"days": 30}))

        view = test_db.get_analytics_view("Test-View")
        assert json.loads(view["filter_json"])["days"] == 30

    def test_get_all_views(self, test_db):
        """Mehrere Views speichern und alle laden."""
        test_db.save_analytics_view("View A", json.dumps({"a": 1}))
        test_db.save_analytics_view("View B", json.dumps({"b": 2}))
        test_db.save_analytics_view("View C", json.dumps({"c": 3}))

        views = test_db.get_analytics_views()
        assert len(views) == 3
        names = [v["name"] for v in views]
        assert "View A" in names
        assert "View B" in names
        assert "View C" in names

    def test_get_nonexistent_view_returns_none(self, test_db):
        """Nicht-existierende View → None."""
        view = test_db.get_analytics_view("Existiert-Nicht")
        assert view is None

    def test_delete_view(self, test_db):
        """View löschen."""
        test_db.save_analytics_view("Zu-Löschen", json.dumps({"x": 1}))
        assert test_db.delete_analytics_view("Zu-Löschen")
        assert test_db.get_analytics_view("Zu-Löschen") is None

    def test_delete_nonexistent_returns_false(self, test_db):
        """Nicht-existierende View löschen → False."""
        assert test_db.delete_analytics_view("Existiert-Nicht") is False

    def test_view_has_created_at(self, test_db):
        """created_at wird automatisch gesetzt."""
        test_db.save_analytics_view("Timestamp-Test", json.dumps({}))
        view = test_db.get_analytics_view("Timestamp-Test")
        assert view["created_at"] is not None
        assert len(view["created_at"]) > 0


class TestCrossFilterState:
    """Tests für den CrossFilterState-Singleton."""

    def test_singleton_returns_same_instance(self):
        from ui.pages.analytics._filters.cross_filter_state import CrossFilterState

        CrossFilterState.reset_instance()
        s1 = CrossFilterState.instance()
        s2 = CrossFilterState.instance()
        assert s1 is s2

    def test_set_depot_filter(self):
        from ui.pages.analytics._filters.cross_filter_state import CrossFilterState

        CrossFilterState.reset_instance()
        state = CrossFilterState.instance()
        state.set_depot_filter({1, 2, 3})
        assert state.state.depot_ids == {1, 2, 3}

    def test_set_praeparat_filter(self):
        from ui.pages.analytics._filters.cross_filter_state import CrossFilterState

        CrossFilterState.reset_instance()
        state = CrossFilterState.instance()
        state.set_praeparat_filter({10, 20})
        assert state.state.praeparat_ids == {10, 20}

    def test_set_date_range(self):
        from ui.pages.analytics._filters.cross_filter_state import CrossFilterState

        CrossFilterState.reset_instance()
        state = CrossFilterState.instance()
        state.set_date_range(90)
        assert state.state.date_range_days == 90

    def test_clear_all(self):
        from ui.pages.analytics._filters.cross_filter_state import CrossFilterState

        CrossFilterState.reset_instance()
        state = CrossFilterState.instance()
        state.set_depot_filter({1})
        state.set_praeparat_filter({2})
        state.set_date_range(365)
        state.clear_all()
        assert state.state.is_empty()
        assert state.state.date_range_days == 30  # Default

    def test_listener_called_on_change(self):
        from ui.pages.analytics._filters.cross_filter_state import CrossFilterState

        CrossFilterState.reset_instance()
        state = CrossFilterState.instance()
        called = []
        state.add_listener(lambda s: called.append(s.depot_ids))
        state.set_depot_filter({5})
        assert len(called) == 1
        assert called[0] == {5}

    def test_listener_not_called_on_noop(self):
        from ui.pages.analytics._filters.cross_filter_state import CrossFilterState

        CrossFilterState.reset_instance()
        state = CrossFilterState.instance()
        state.set_depot_filter({1})
        called = []
        state.add_listener(lambda s: called.append(True))
        state.set_depot_filter({1})  # Gleicher Wert → kein Notify
        assert len(called) == 0

    def test_filter_state_is_empty(self):
        from ui.pages.analytics._filters.cross_filter_state import FilterState

        fs = FilterState()
        assert fs.is_empty()
        fs.depot_ids.add(1)
        assert not fs.is_empty()
        fs.clear()
        assert fs.is_empty()


class TestLayoutPersistence:
    """Tests für die Layout-Persistenz."""

    def test_save_and_load_layout(self, tmp_path):
        from ui.pages.analytics._filters.layout_persistence import LayoutPersistence

        lp = LayoutPersistence(data_dir=str(tmp_path))
        state = {
            "active_tab": 2,
            "date_range_days": 90,
            "depot_ids": [1, 3],
            "praeparat_ids": [],
            "compare_mode": True,
        }
        assert lp.save_layout(state)
        assert lp.exists()

        loaded = lp.load_layout()
        assert loaded is not None
        assert loaded["active_tab"] == 2
        assert loaded["date_range_days"] == 90
        assert loaded["depot_ids"] == [1, 3]
        assert loaded["compare_mode"] is True

    def test_load_nonexistent_returns_none(self, tmp_path):
        from ui.pages.analytics._filters.layout_persistence import LayoutPersistence

        lp = LayoutPersistence(data_dir=str(tmp_path))
        assert lp.load_layout() is None
        assert not lp.exists()

    def test_clear_layout(self, tmp_path):
        from ui.pages.analytics._filters.layout_persistence import LayoutPersistence

        lp = LayoutPersistence(data_dir=str(tmp_path))
        lp.save_layout({"active_tab": 0})
        assert lp.exists()
        assert lp.clear_layout()
        assert not lp.exists()

    def test_creates_parent_directory(self, tmp_path):
        from ui.pages.analytics._filters.layout_persistence import LayoutPersistence

        nested = tmp_path / "nested" / "analytics"
        lp = LayoutPersistence(data_dir=str(nested))
        assert lp.save_layout({"active_tab": 1})
        assert lp.exists()
        assert lp.load_layout()["active_tab"] == 1

    def test_file_path_property(self, tmp_path):
        from ui.pages.analytics._filters.layout_persistence import LayoutPersistence

        lp = LayoutPersistence(data_dir=str(tmp_path))
        assert lp.file_path.name == "analytics_layout.json"
        assert str(tmp_path) in str(lp.file_path)
