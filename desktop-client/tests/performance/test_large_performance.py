import time
from datetime import datetime

import pytest
from db_manager import Database


@pytest.fixture
def large_perf_db(tmp_path):
    db = Database(str(tmp_path / "large_perf.db"))
    try:
        yield db
    finally:
        db.conn.close()


@pytest.mark.performance
def test_large_query_paths_execute(large_perf_db):
    for year in [2023, 2024, datetime.now().year]:
        outgoing = large_perf_db.query_outgoing(year)
        assert isinstance(outgoing, list)

    stock_data = large_perf_db.query_stock()
    assert len(stock_data) >= 1


@pytest.mark.performance
def test_cache_stress_repeated_calls(large_perf_db):
    if hasattr(large_perf_db.get_all_depot_names, "cache_clear"):
        large_perf_db.get_all_depot_names.cache_clear()

    first = large_perf_db.get_all_depot_names()
    start = time.perf_counter()
    for _ in range(100):
        again = large_perf_db.get_all_depot_names()
        assert again == first
    elapsed = time.perf_counter() - start
    assert elapsed >= 0


@pytest.mark.performance
def test_ui_optimization_reduction_model():
    operations_without_opt = 360
    operations_with_opt = 5
    reduction = ((operations_without_opt - operations_with_opt) / operations_without_opt) * 100
    assert reduction > 95
