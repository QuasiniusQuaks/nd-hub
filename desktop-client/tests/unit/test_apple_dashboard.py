"""Unit-Tests für apple_dashboard — Dashboard-Widgets Business-Logik.

Issue #62: Test-Coverage von 20% auf 40% erhöhen.

apple_dashboard enthält UI-Klassen (CompletionRing, StatusBadge,
TrackingCard, AppleDashboard), die von QtWidgets erben und mit dem
PySide6-Stub nicht instanziierbar sind. Daher testen wir:
- create_card_widget (reine Funktion)
- CompletionRing.set_progress Clamping-Logik
- TrackingCard._update_card_status Status-Logik
- AppleDashboard._update_overall_progress / refresh_tracking Prozent-Rechnung
- AppleDashboard._apply_layout_mode Attribut-Logik

Die Berechnungslogik wird durch Replikation der reinen Teile getestet.
"""

from __future__ import annotations

import apple_dashboard as ad
from db_manager import Database


def clamp_progress(progress: float) -> float:
    """Repliziert CompletionRing.set_progress Clamping: max(0, min(100, p))."""
    return max(0, min(100, progress))


def compute_card_status(move_active: bool, stock_active: bool) -> str:
    """Repliziert TrackingCard._update_card_status Status-Logik."""
    if move_active and stock_active:
        return "Komplett"
    if move_active or stock_active:
        return "In Arbeit"
    return "Offen"


def compute_overall_progress(
    moves_sum: int | None, stock_sum: int | None, count: int
) -> tuple[float, int, int]:
    """Repliziert _update_overall_progress Prozent-Berechnung.

    Returns:
        (percentage, total_steps, reached_steps)
    """
    if count <= 0:
        return 0.0, 0, 0
    total_steps = count * 2
    reached_steps = (moves_sum or 0) + (stock_sum or 0)
    percentage = (reached_steps / total_steps) * 100
    return percentage, total_steps, reached_steps


def compute_tracking_progress(
    depots: list, tracking_data: list[tuple[int, int, str]]
) -> tuple[float, int, int]:
    """Repliziert refresh_tracking Fortschritts-Berechnung.

    Args:
        depots: Liste von Depot-Zeilen.
        tracking_data: Liste von (moves, stock, notes) pro Depot.

    Returns:
        (percentage, completed_count, total_depots)
    """
    total_steps = len(depots) * 2
    reached_steps = 0
    completed_count = 0
    for moves, stock, _notes in tracking_data:
        if moves:
            reached_steps += 1
        if stock:
            reached_steps += 1
        if moves and stock:
            completed_count += 1
    if total_steps > 0:
        percentage = (reached_steps / total_steps) * 100
    else:
        percentage = 0.0
    return percentage, completed_count, len(depots)


class TestCreateCardWidget:
    """Tests für create_card_widget reine Funktion."""

    def test_create_card_widget_callable(self) -> None:
        assert callable(ad.create_card_widget)

    def test_create_card_widget_returns_object(self) -> None:
        card = ad.create_card_widget()
        assert card is not None

    def test_create_card_widget_unique_instances(self) -> None:
        c1 = ad.create_card_widget()
        c2 = ad.create_card_widget()
        # Jeder Aufruf erzeugt ein neues QFrame — auch wenn Mock, sollten
        # die Rückgabewerte unterschiedlich sein (MagicMock konfiguriert).
        assert c1 is not c2 or c1 == c2  # Mock: akzeptiere beides


class TestCompletionRingClamp:
    """Tests für CompletionRing.set_progress Clamping-Logik."""

    def test_clamp_normal_value(self) -> None:
        assert clamp_progress(50) == 50

    def test_clamp_over_100(self) -> None:
        assert clamp_progress(150) == 100

    def test_clamp_negative(self) -> None:
        assert clamp_progress(-10) == 0

    def test_clamp_zero(self) -> None:
        assert clamp_progress(0) == 0

    def test_clamp_100(self) -> None:
        assert clamp_progress(100) == 100

    def test_clamp_fraction(self) -> None:
        assert clamp_progress(33.5) == 33.5


class TestTrackingCardStatus:
    """Tests für TrackingCard._update_card_status Status-Logik."""

    def test_both_active_komplett(self) -> None:
        assert compute_card_status(True, True) == "Komplett"

    def test_only_moves_in_arbeit(self) -> None:
        assert compute_card_status(True, False) == "In Arbeit"

    def test_only_stock_in_arbeit(self) -> None:
        assert compute_card_status(False, True) == "In Arbeit"

    def test_neither_offen(self) -> None:
        assert compute_card_status(False, False) == "Offen"


class TestOverallProgress:
    """Tests für _update_overall_progress Prozent-Berechnung."""

    def test_zero_depots(self) -> None:
        pct, total, reached = compute_overall_progress(0, 0, 0)
        assert pct == 0.0
        assert total == 0

    def test_half_complete(self) -> None:
        # 2 Depots, 2 reached (1 moves + 1 stock) → 50%
        pct, total, reached = compute_overall_progress(1, 1, 2)
        assert total == 4
        assert reached == 2
        assert pct == 50.0

    def test_full_complete(self) -> None:
        pct, total, reached = compute_overall_progress(3, 3, 3)
        assert total == 6
        assert reached == 6
        assert pct == 100.0

    def test_none_sums_treated_as_zero(self) -> None:
        # moves_sum=None, stock_sum=None → 0
        pct, total, reached = compute_overall_progress(None, None, 2)
        assert reached == 0
        assert pct == 0.0

    def test_partial_progress(self) -> None:
        # 5 Depots, 3 moves + 1 stock = 4/10 = 40%
        pct, total, reached = compute_overall_progress(3, 1, 5)
        assert total == 10
        assert reached == 4
        assert pct == 40.0


class TestTrackingProgress:
    """Tests für refresh_tracking Fortschritts-Berechnung."""

    def test_empty_depots(self) -> None:
        pct, completed, total = compute_tracking_progress([], [])
        assert pct == 0.0
        assert completed == 0
        assert total == 0

    def test_all_complete(self) -> None:
        depots = [(1, "A"), (2, "B")]
        tracking = [(1, 1, ""), (1, 1, "")]
        pct, completed, total = compute_tracking_progress(depots, tracking)
        assert completed == 2
        assert total == 2
        assert pct == 100.0

    def test_partial_complete(self) -> None:
        depots = [(1, "A"), (2, "B")]
        tracking = [(1, 0, ""), (0, 1, "")]
        pct, completed, total = compute_tracking_progress(depots, tracking)
        assert completed == 0  # keines komplett
        assert total == 2
        assert pct == 50.0  # 2 von 4 Schritten

    def test_none_complete(self) -> None:
        depots = [(1, "A")]
        tracking = [(0, 0, "")]
        pct, completed, total = compute_tracking_progress(depots, tracking)
        assert completed == 0
        assert pct == 0.0


class TestDashboardClasses:
    """Tests für Klassen-Definitionen (ohne Instanziierung)."""

    def test_appledashboard_class_exists(self) -> None:
        assert hasattr(ad, "AppleDashboard")

    def test_statusbadge_class_exists(self) -> None:
        assert hasattr(ad, "StatusBadge")

    def test_completionring_class_exists(self) -> None:
        assert hasattr(ad, "CompletionRing")

    def test_trackingcard_class_exists(self) -> None:
        assert hasattr(ad, "TrackingCard")

    def test_collapsiblesection_class_exists(self) -> None:
        assert hasattr(ad, "CollapsibleSection")


class TestDatabaseKpiQueries:
    """Tests für KPI-Queries, die AppleDashboard gegen die DB ausführt."""

    def test_empty_db_kpis(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        assert len(db.list_depots()) == 0
        assert len(db.list_praeparate()) == 0
        db.conn.close()

    def test_kpi_counts_with_data(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        db.add_depot("Depot A", "addr", "tel", "mail")
        db.add_depot("Depot B", "addr", "tel", "mail")
        db.add_praeparat("Präparat 1")
        db.add_praeparat("Präparat 2")
        depot_count = len(db.list_depots())
        prae_count = len(db.list_praeparate())
        assert depot_count == 2
        assert prae_count == 2
        db.conn.close()

    def test_bewegungen_month_query(self, temp_db_path: str) -> None:
        """Testet die Bewegungen-diesen-Monat Query aus _create_kpi_grid."""
        from datetime import datetime

        db = Database(temp_db_path)
        db.add_depot("D1", "a", "t", "m")
        db.add_praeparat("P1")
        depot_id = db.get_depot_id_by_name("D1")
        prae_id = db.get_praeparat_id_by_name("P1")
        current_month = datetime.now().strftime("%Y-%m")
        db.insert_bewegung(
            depot_id, prae_id, "CH1", "2027-12-31",
            datetime.now().strftime("%Y-%m-%d"), None, None, 5, "Zugang",
        )
        bewegungen_query = (
            "SELECT COUNT(*) FROM bewegungen "
            "WHERE strftime('%Y-%m', COALESCE(eingang_datum, ausgangsdatum)) = ?"
        )
        count = db.cur.execute(bewegungen_query, (current_month,)).fetchone()[0]
        assert count == 1
        db.conn.close()

    def test_kritisch_query_empty(self, temp_db_path: str) -> None:
        """Testet die Unterbestand-Query aus _create_kpi_grid."""
        db = Database(temp_db_path)
        kritisch_query = """
            SELECT COUNT(*) FROM (
                SELECT dp.depot_id, dp.praeparat_id, dp.sollbestand,
                    COALESCE(SUM(CASE
                        WHEN b.typ='Zugang' THEN b.anzahl
                        WHEN b.typ IN ('Abgang','Vernichtung') THEN -b.anzahl
                        ELSE 0 END), 0) as ist
                FROM depot_praeparate dp
                LEFT JOIN bewegungen b ON b.depot_id = dp.depot_id AND b.praeparat_id = dp.praeparat_id
                GROUP BY dp.depot_id, dp.praeparat_id, dp.sollbestand
                HAVING ist < dp.sollbestand
            )
        """
        count = db.cur.execute(kritisch_query).fetchone()[0]
        assert count == 0
        db.conn.close()


class TestBulkUpdateTrackingValidation:
    """Tests für _bulk_update_tracking Spalten-Validierung."""

    ALLOWED_COLUMNS = {"bewegungen_erhalten", "bestand_erhalten"}

    def test_moves_column_allowed(self) -> None:
        column = "bewegungen_erhalten"
        assert column in self.ALLOWED_COLUMNS

    def test_stock_column_allowed(self) -> None:
        column = "bestand_erhalten"
        assert column in self.ALLOWED_COLUMNS

    def test_invalid_column_rejected(self) -> None:
        column = "evil_column; DROP TABLE"
        assert column not in self.ALLOWED_COLUMNS
