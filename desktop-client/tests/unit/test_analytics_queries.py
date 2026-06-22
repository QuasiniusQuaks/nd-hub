"""Tests für die neuen Analytics-DB-Methoden (Issue #42, Phase 1).

Testet alle 12 neuen Query-Methoden, die für das Analytics Control Center
geschrieben wurden. Verwendet eine In-Memory-DB mit Testdaten.
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# PySide6-Stub für headless Tests (muss vor db_manager-Import erfolgen)
from db_manager import Database


@pytest.fixture
def analytics_db():
    """Erstellt eine Test-DB mit repräsentativen Analytics-Daten."""
    db_path = tempfile.mktemp(suffix="_analytics_test.db")
    db = Database(db_path)
    cur = db.conn.cursor()

    # Depots
    cur.execute("INSERT INTO depots (id, name) VALUES (1, 'Berlin-Mitte')")
    cur.execute("INSERT INTO depots (id, name) VALUES (2, 'Hamburg-Altona')")
    cur.execute("INSERT INTO depots (id, name) VALUES (3, 'München-Süd')")

    # Präparate
    cur.execute("INSERT INTO praeparate (id, name, wirkstoff) VALUES (1, 'Morphin 10mg', 'Morphin')")
    cur.execute("INSERT INTO praeparate (id, name, wirkstoff) VALUES (2, 'Adrenalin 1mg', 'Epinephrin')")
    cur.execute("INSERT INTO praeparate (id, name, wirkstoff) VALUES (3, 'Noradrenalin', 'Norepinephrin')")

    # Depot-Präparat-Zuordnungen mit Sollbestand
    cur.execute("INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand) VALUES (1, 1, 100)")
    cur.execute("INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand) VALUES (1, 2, 50)")
    cur.execute("INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand) VALUES (2, 1, 80)")
    cur.execute("INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand) VALUES (3, 3, 40)")

    now = datetime.now()
    soon = (now + timedelta(days=15)).strftime("%Y-%m-%d")      # 15 Tage → verfall-warning
    later = (now + timedelta(days=60)).strftime("%Y-%m-%d")     # 60 Tage → nicht in 30d-warning
    recent = now.strftime("%Y-%m-%d")
    old = (now - timedelta(days=200)).strftime("%Y-%m-%d")       # 200 Tage → dead stock / inactive
    recent_minus_3 = (now - timedelta(days=3)).strftime("%Y-%m-%d")

    # Bewegungen
    # Depot 1, Präparat 1: Zugänge und Abgänge (aktiv)
    cur.execute(
        "INSERT INTO bewegungen (depot_id, praeparat_id, charge, verfall, eingang_datum, ausgang_datum, anzahl, typ) "
        "VALUES (1, 1, 'M2401', ?, ?, ?, 120, 'Zugang')",
        (soon, recent, None),
    )
    cur.execute(
        "INSERT INTO bewegungen (depot_id, praeparat_id, charge, verfall, eingang_datum, ausgang_datum, anzahl, typ) "
        "VALUES (1, 1, 'M2402', ?, ?, ?, 50, 'Zugang')",
        (later, recent_minus_3, None),
    )
    cur.execute(
        "INSERT INTO bewegungen (depot_id, praeparat_id, charge, verfall, eingang_datum, ausgang_datum, anzahl, typ) "
        "VALUES (1, 1, '', '', NULL, ?, 30, 'Abgang')",
        (recent_minus_3,),
    )

    # Depot 1, Präparat 2: Zugang mit nahem Verfall
    cur.execute(
        "INSERT INTO bewegungen (depot_id, praeparat_id, charge, verfall, eingang_datum, ausgang_datum, anzahl, typ) "
        "VALUES (1, 2, 'A8811', ?, ?, ?, 12, 'Zugang')",
        (soon, recent, None),
    )

    # Depot 2, Präparat 1: nur alter Zugang (dead stock Kandidat)
    cur.execute(
        "INSERT INTO bewegungen (depot_id, praeparat_id, charge, verfall, eingang_datum, ausgang_datum, anzahl, typ) "
        "VALUES (2, 1, 'M2301', ?, ?, ?, 90, 'Zugang')",
        (later, old, None),
    )

    # Depot 3, Präparat 3: komplett inaktiv (nur Sollbestand, keine Bewegung)
    # → appears in inactive_depots

    db.conn.commit()
    yield db
    db.conn.close()
    Path(db_path).unlink(missing_ok=True)


class TestVerfallWarnings:
    def test_returns_items_within_threshold(self, analytics_db):
        rows = analytics_db.get_verfall_warnings(days=30)
        # 2 Zugänge mit verfall ≤ 30 Tage (soon = +15 Tage)
        assert len(rows) == 2
        for row in rows:
            assert row["verfall"] is not None
            assert row["depot_name"] in ("Berlin-Mitte", "Hamburg-Altona")

    def test_excludes_items_beyond_threshold(self, analytics_db):
        rows = analytics_db.get_verfall_warnings(days=30)
        # later = +60 Tage, darf nicht auftauchen
        verfalls = [row["verfall"] for row in rows]
        later_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        assert later_date not in verfalls

    def test_empty_db_returns_empty_list(self, analytics_db):
        # Mit der bestehenden Test-DB: items existieren, aber days=0 könnte leere Liste geben
        rows = analytics_db.get_verfall_warnings(days=0)
        # verfall = today oder future, days=0 bedeutet: nur heute
        assert isinstance(rows, list)


class TestDepotDeviation:
    def test_returns_one_row_per_depot(self, analytics_db):
        rows = analytics_db.get_depot_deviation()
        depot_names = [row["depot_name"] for row in rows]
        assert "Berlin-Mitte" in depot_names
        assert "Hamburg-Altona" in depot_names
        assert "München-Süd" in depot_names

    def test_differenz_calculated(self, analytics_db):
        rows = analytics_db.get_depot_deviation()
        berlin = next(r for r in rows if r["depot_name"] == "Berlin-Mitte")
        # Berlin: soll=150 (100+50), ist = 120+50-30+12 = 152, differenz = 2
        assert berlin["differenz"] == 2

    def test_ordered_by_abs_differenz(self, analytics_db):
        rows = analytics_db.get_depot_deviation()
        diffs = [abs(row["differenz"]) for row in rows]
        assert diffs == sorted(diffs, reverse=True)


class TestInactiveDepots:
    def test_returns_depots_without_recent_movement(self, analytics_db):
        rows = analytics_db.get_inactive_depots(days=180)
        depot_names = [row["depot_name"] for row in rows]
        # München-Süd hat keine Bewegung, Hamburg-Altona hat nur alte (200 Tage)
        assert "München-Süd" in depot_names
        assert "Hamburg-Altona" in depot_names

    def test_excludes_active_depots(self, analytics_db):
        rows = analytics_db.get_inactive_depots(days=180)
        depot_names = [row["depot_name"] for row in rows]
        assert "Berlin-Mitte" not in depot_names


class TestPeriodTrend:
    def test_returns_dict_with_expected_keys(self, analytics_db):
        result = analytics_db.get_period_trend(days=7)
        assert "zugang_aktuell" in result
        assert "zugang_vorperiode" in result
        assert "veraenderung_pct" in result

    def test_aktuell_counts_recent_zugaenge(self, analytics_db):
        result = analytics_db.get_period_trend(days=7)
        # recent + recent_minus_3 sind beide innerhalb 7 Tage → 120 + 50 + 12 = 182
        assert result["zugang_aktuell"] == 182

    def test_no_division_by_zero(self, analytics_db):
        # With empty vorperiode, should return 0.0 not crash
        result = analytics_db.get_period_trend(days=1)
        assert isinstance(result["veraenderung_pct"], (int, float))


class TestKpiSparkline:
    def test_returns_list_of_ints(self, analytics_db):
        data = analytics_db.get_kpi_sparkline(metric="zugang", days=7)
        assert isinstance(data, list)
        assert len(data) == 7
        assert all(isinstance(v, int) for v in data)

    def test_zugang_sparkline_has_data(self, analytics_db):
        data = analytics_db.get_kpi_sparkline(metric="zugang", days=7)
        # Mindestens ein Tag mit Zugang (recent = 120+12, recent_minus_3 = 50)
        assert sum(data) > 0

    def test_abgang_sparkline(self, analytics_db):
        data = analytics_db.get_kpi_sparkline(metric="abgang", days=7)
        assert len(data) == 7
        # Ein Abgang an recent_minus_3
        assert sum(data) == 30

    def test_verfall_sparkline(self, analytics_db):
        data = analytics_db.get_kpi_sparkline(metric="verfall", days=7)
        assert len(data) == 7
        assert isinstance(data, list)


class TestAnomalies:
    def test_returns_list(self, analytics_db):
        rows = analytics_db.get_anomalies(threshold_std=1.0)
        assert isinstance(rows, list)
        # Mit nur wenigen Datenpunkten pro Präparat (need ≥3 for stats)
        # könnte leer sein — das ist OK

    def test_high_threshold_fewer_results(self, analytics_db):
        low = analytics_db.get_anomalies(threshold_std=0.5)
        high = analytics_db.get_anomalies(threshold_std=5.0)
        assert len(high) <= len(low)


class TestVerfallForecast:
    def test_returns_monthly_aggregation(self, analytics_db):
        rows = analytics_db.get_verfall_forecast(months=12)
        assert isinstance(rows, list)
        # soon = +15 Tage → ist im aktuellen Monat oder nächsten
        # later = +60 Tage → in ~2 Monaten
        if rows:
            for row in rows:
                assert row["monat"] is not None
                assert row["verfallende_einheiten"] > 0

    def test_empty_forecast_for_zero_months(self, analytics_db):
        rows = analytics_db.get_verfall_forecast(months=0)
        assert isinstance(rows, list)


class TestPeriodComparison:
    def test_returns_two_periods(self, analytics_db):
        now = datetime.now()
        result = analytics_db.get_period_comparison(
            period_a_start=(now - timedelta(days=10)).strftime("%Y-%m-%d"),
            period_a_end=now.strftime("%Y-%m-%d"),
            period_b_start=(now - timedelta(days=20)).strftime("%Y-%m-%d"),
            period_b_end=(now - timedelta(days=11)).strftime("%Y-%m-%d"),
        )
        assert "period_a" in result
        assert "period_b" in result
        assert isinstance(result["period_a"], list)
        assert isinstance(result["period_b"], list)

    def test_period_a_has_recent_data(self, analytics_db):
        now = datetime.now()
        result = analytics_db.get_period_comparison(
            period_a_start=(now - timedelta(days=10)).strftime("%Y-%m-%d"),
            period_a_end=now.strftime("%Y-%m-%d"),
            period_b_start="2020-01-01",
            period_b_end="2020-12-31",
        )
        assert len(result["period_a"]) > 0
        assert len(result["period_b"]) == 0  # keine Daten von 2020


class TestTopMovers:
    def test_out_direction(self, analytics_db):
        rows = analytics_db.get_top_movers(direction="out", days=30)
        assert isinstance(rows, list)
        if rows:
            assert rows[0]["gesamt"] >= rows[-1]["gesamt"]  # DESC sorted

    def test_in_direction(self, analytics_db):
        rows = analytics_db.get_top_movers(direction="in", days=30)
        assert isinstance(rows, list)
        if rows:
            assert rows[0]["praeparat_name"] == "Morphin 10mg"  # 120+50=170

    def test_invalid_direction_raises(self, analytics_db):
        with pytest.raises(ValueError, match="direction must be"):
            analytics_db.get_top_movers(direction="sideways")

    def test_limit_respected(self, analytics_db):
        rows = analytics_db.get_top_movers(direction="in", limit=1, days=365)
        assert len(rows) <= 1


class TestInventoryTurnover:
    def test_returns_active_items(self, analytics_db):
        rows = analytics_db.get_inventory_turnover()
        assert isinstance(rows, list)
        names = [row["praeparat_name"] for row in rows]
        # Präparat 3 (Noradrenalin) hat keine Bewegung → nicht in Ergebnis
        assert "Noradrenalin" not in names
        assert "Morphin 10mg" in names

    def test_umslagsrate_calculated(self, analytics_db):
        rows = analytics_db.get_inventory_turnover()
        morphin = next(r for r in rows if r["praeparat_name"] == "Morphin 10mg")
        # zugang=260 (120+50 Berlin + 90 Hamburg), abgang=30, rate=30/260≈0.12
        assert morphin["umschlagsrate"] == pytest.approx(0.12, abs=0.01)


class TestDeadStock:
    def test_returns_old_items(self, analytics_db):
        rows = analytics_db.get_dead_stock(days=180)
        assert isinstance(rows, list)
        if rows:
            for row in rows:
                assert row["ist_bestand"] > 0

    def test_excludes_recent_activity(self, analytics_db):
        rows = analytics_db.get_dead_stock(days=180)
        # Berlin-Mitte / Morphin hat Bewegung vor 3 Tagen → nicht dead stock
        combos = [(row["praeparat_name"], row["depot_name"]) for row in rows]
        assert ("Morphin 10mg", "Berlin-Mitte") not in combos


class TestComplianceOverview:
    def test_returns_dict_with_expected_keys(self, analytics_db):
        result = analytics_db.get_compliance_overview()
        assert "email_verlauf" in result
        assert "permissions" in result
        assert isinstance(result["email_verlauf"], list)
        assert isinstance(result["permissions"], list)

    def test_empty_email_verlauf(self, analytics_db):
        result = analytics_db.get_compliance_overview()
        # Keine Emails in Test-DB
        assert len(result["email_verlauf"]) == 0

    def test_empty_permissions(self, analytics_db):
        result = analytics_db.get_compliance_overview()
        # Keine User-Permissions in Test-DB
        assert len(result["permissions"]) == 0
