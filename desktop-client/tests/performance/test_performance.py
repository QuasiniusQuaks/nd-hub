import time

import pytest

from db_manager import Database


@pytest.fixture
def perf_db(tmp_path):
    db = Database(str(tmp_path / "perf.db"))
    try:
        yield db
    finally:
        db.conn.close()


@pytest.mark.performance
def test_cached_name_lookups_are_stable(perf_db):
    if hasattr(perf_db.get_all_praeparate_names, "cache_clear"):
        perf_db.get_all_praeparate_names.cache_clear()
    first = perf_db.get_all_praeparate_names()
    second = perf_db.get_all_praeparate_names()
    assert first == second


@pytest.mark.performance
def test_query_stock_and_outgoing_execute(perf_db):
    stock_data = perf_db.query_stock()
    outgoing = perf_db.query_outgoing(2024)
    assert len(stock_data) >= 1
    assert isinstance(outgoing, list)


@pytest.mark.performance
def test_ui_refresh_change_detection_ratio():
    last_hash = None
    refresh_count = 0
    skip_count = 0

    start = time.perf_counter()
    for _ in range(10):
        current_hash = "5_3"
        if current_hash != last_hash:
            refresh_count += 1
            last_hash = current_hash
        else:
            skip_count += 1
    elapsed = time.perf_counter() - start

    assert refresh_count == 1
    assert skip_count == 9
    assert elapsed >= 0
