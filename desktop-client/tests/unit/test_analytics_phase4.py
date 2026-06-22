"""Tests für Phase 4 Features: Custom-SQL, Saved Queries, Email-Schedule.

Issue #42 Phase 4 — Power-User.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from db_manager import Database


@pytest.fixture
def test_db():
    """Erstellt eine Test-DB mit Schema +少量 Daten."""
    db_path = tempfile.mktemp(suffix="_phase4_test.db")
    db = Database(db_path)
    cur = db.conn.cursor()
    cur.execute("INSERT INTO depots (id, name) VALUES (1, 'Berlin')")
    cur.execute("INSERT INTO praeparate (id, name) VALUES (1, 'Morphin')")
    cur.execute(
        "INSERT INTO bewegungen (depot_id, praeparat_id, charge, verfall, eingang_datum, anzahl, typ) "
        "VALUES (1, 1, 'C1', '2026-12-01', '2026-06-01', 50, 'Zugang')"
    )
    db.conn.commit()
    yield db
    db.conn.close()
    Path(db_path).unlink(missing_ok=True)


class TestSavedQueriesCRUD:
    """Tests für analytics_saved_queries."""

    def test_save_and_get_query(self, test_db):
        sql = "SELECT COUNT(*) FROM bewegungen"
        assert test_db.save_query("Test-Query", sql, "Zählt Bewegungen")

        q = test_db.get_saved_query("Test-Query")
        assert q is not None
        assert q["name"] == "Test-Query"
        assert "COUNT" in q["sql_text"]

    def test_upsert_existing_query(self, test_db):
        test_db.save_query("Upsert-Test", "SELECT 1")
        test_db.save_query("Upsert-Test", "SELECT 2")

        q = test_db.get_saved_query("Upsert-Test")
        assert "SELECT 2" in q["sql_text"]

    def test_reject_non_select_statement(self, test_db):
        """Security: INSERT/DELETE/DROP dürfen nicht gespeichert werden."""
        assert not test_db.save_query("Bad-Insert", "INSERT INTO depots VALUES (1, 'x')")
        assert not test_db.save_query("Bad-Delete", "DELETE FROM bewegungen")
        assert not test_db.save_query("Bad-Drop", "DROP TABLE depots")

        # SELECT ist erlaubt
        assert test_db.save_query("Good-Select", "SELECT * FROM depots")

    def test_get_all_queries(self, test_db):
        test_db.save_query("Q1", "SELECT 1")
        test_db.save_query("Q2", "SELECT 2")
        test_db.save_query("Q3", "SELECT 3")

        queries = test_db.get_saved_queries()
        assert len(queries) == 3

    def test_delete_query(self, test_db):
        test_db.save_query("Zu-Löschen", "SELECT 1")
        assert test_db.delete_saved_query("Zu-Löschen")
        assert test_db.get_saved_query("Zu-Löschen") is None

    def test_delete_nonexistent_returns_false(self, test_db):
        assert test_db.delete_saved_query("Existiert-Nicht") is False

    def test_run_saved_query(self, test_db):
        """Gespeicherte Query ausführen + Ergebnis."""
        test_db.save_query("Count-Bewegungen", "SELECT COUNT(*) AS total FROM bewegungen")
        rows, columns = test_db.run_saved_query("Count-Bewegungen")
        assert len(rows) == 1
        assert rows[0][0] == 1  # Eine Bewegung im Fixture
        assert "total" in columns

    def test_run_saved_query_updates_last_run(self, test_db):
        test_db.save_query("Last-Run-Test", "SELECT 1")
        test_db.run_saved_query("Last-Run-Test")
        q = test_db.get_saved_query("Last-Run-Test")
        assert q["last_run"] is not None

    def test_run_nonexistent_query_returns_empty(self, test_db):
        rows, columns = test_db.run_saved_query("Existiert-Nicht")
        assert rows == []
        assert columns == []

    def test_run_query_returns_columns(self, test_db):
        test_db.save_query("Depot-Names", "SELECT name FROM depots ORDER BY name")
        rows, columns = test_db.run_saved_query("Depot-Names")
        assert "name" in columns
        assert len(rows) == 1
        assert rows[0][0] == "Berlin"


class TestEmailScheduleCRUD:
    """Tests für analytics_email_schedule."""

    def test_save_and_get_schedule(self, test_db):
        assert test_db.save_email_schedule(
            "Wochenreport", "a@b.de, c@d.de", "weekly", "pdf"
        )

        schedules = test_db.get_email_schedules()
        assert len(schedules) == 1
        s = schedules[0]
        assert s["name"] == "Wochenreport"
        assert s["recipients"] == "a@b.de, c@d.de"
        assert s["schedule"] == "weekly"
        assert s["report_type"] == "pdf"
        assert s["enabled"] == 1

    def test_multiple_schedules(self, test_db):
        test_db.save_email_schedule("Daily", "a@b.de", "daily", "html")
        test_db.save_email_schedule("Monthly", "c@d.de", "monthly", "pdf")
        test_db.save_email_schedule("Weekly", "e@f.de", "weekly", "pdf")

        schedules = test_db.get_email_schedules()
        assert len(schedules) == 3

    def test_update_sent_timestamp(self, test_db):
        test_db.save_email_schedule("Test-Sent", "a@b.de", "weekly", "pdf")
        schedules = test_db.get_email_schedules()
        schedule_id = schedules[0]["id"]
        assert schedules[0]["last_sent"] is None

        assert test_db.update_email_schedule_sent(schedule_id)

        schedules = test_db.get_email_schedules()
        assert schedules[0]["last_sent"] is not None

    def test_delete_schedule(self, test_db):
        test_db.save_email_schedule("Zu-Löschen", "a@b.de", "weekly", "pdf")
        schedules = test_db.get_email_schedules()
        schedule_id = schedules[0]["id"]

        assert test_db.delete_email_schedule(schedule_id)
        assert len(test_db.get_email_schedules()) == 0

    def test_toggle_schedule(self, test_db):
        test_db.save_email_schedule("Toggle-Test", "a@b.de", "weekly", "pdf")
        schedules = test_db.get_email_schedules()
        schedule_id = schedules[0]["id"]
        assert schedules[0]["enabled"] == 1

        # Deaktivieren
        test_db.toggle_email_schedule(schedule_id, enabled=False)
        schedules = test_db.get_email_schedules()
        assert schedules[0]["enabled"] == 0

        # Wieder aktivieren
        test_db.toggle_email_schedule(schedule_id, enabled=True)
        schedules = test_db.get_email_schedules()
        assert schedules[0]["enabled"] == 1

    def test_delete_nonexistent_schedule(self, test_db):
        assert test_db.delete_email_schedule(999) is False
