import pytest

from db_manager import Database


@pytest.fixture
def verification_db(tmp_path):
    db = Database(str(tmp_path / "verify.db"))
    try:
        yield db
    finally:
        db.conn.close()


@pytest.mark.integration
def test_core_optimization_methods_exist(verification_db):
    required_methods = [
        "get_all_praeparate_names",
        "get_all_depot_names",
        "query_stock",
        "bulk_insert_bewegungen",
        "list_depots",
        "list_praeparate",
    ]
    for method in required_methods:
        assert hasattr(verification_db, method)


@pytest.mark.integration
def test_cache_returns_consistent_data(verification_db):
    cache_targets = [
        "get_all_praeparate_names",
        "get_all_depot_names",
        "list_depots",
        "list_praeparate",
    ]
    for name in cache_targets:
        method = getattr(verification_db, name)
        if hasattr(method, "cache_clear"):
            method.cache_clear()
        first = method()
        second = method()
        assert first == second


@pytest.mark.integration
def test_query_interfaces_return_expected_shapes(verification_db):
    stock = verification_db.query_stock()
    outgoing = verification_db.query_outgoing(2024)

    assert isinstance(stock, list)
    assert len(stock) >= 1
    assert stock[0] == ("Depot", "Präparat", "Soll", "Ist", "Differenz")
    assert isinstance(outgoing, list)
