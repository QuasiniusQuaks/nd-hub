from db_manager import Database


def test_schema_tables_exist(tmp_path):
    db = Database(str(tmp_path / "integration.db"))
    try:
        rows = db.cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        tables = {row[0] for row in rows}
        expected = {
            "depots",
            "kontakte",
            "praeparate",
            "depot_praeparate",
            "bewegungen",
            "email_verlauf",
            "meldungs_tracking",
        }
        assert expected.issubset(tables)
    finally:
        db.conn.close()


def test_sqlite_integrity_and_fk_enabled(tmp_path):
    db = Database(str(tmp_path / "integrity.db"))
    try:
        fk_enabled = db.cur.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk_enabled == 1

        integrity = db.cur.execute("PRAGMA integrity_check").fetchone()[0]
        assert integrity == "ok"
    finally:
        db.conn.close()


def test_integrity_queries_compatible(tmp_path):
    db = Database(str(tmp_path / "query_compat.db"))
    try:
        # Portiert aus tests/integrity_check.py in pytest-Assertions.
        cte_query = """
            WITH v_saldo AS (
                SELECT depot_id, praeparat_id,
                       SUM(CASE WHEN typ='Zugang' THEN anzahl
                           WHEN typ IN ('Abgang','Vernichtung') THEN -anzahl ELSE 0 END) AS saldo
                FROM bewegungen GROUP BY depot_id, praeparat_id
            )
            SELECT COUNT(*) FROM v_saldo
        """
        result = db.cur.execute(cte_query).fetchone()[0]
        assert result == 0

        assert db.list_depots() == []
        assert db.list_praeparate() == []
        assert db.get_all_depot_names() == []
        assert db.get_all_praeparate_names() == []
        assert len(db.query_stock()) == 1
    finally:
        db.conn.close()
