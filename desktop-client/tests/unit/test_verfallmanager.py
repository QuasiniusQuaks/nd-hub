"""Unit-Tests für VerfallManager — Betäubungsmittel-Verfall-Management.

Issue #62: Test-Coverage von 20% auf 40% erhöhen.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from db_manager import Database
from verfallmanager import VerfallManager


def _seed_data(db: Database) -> None:
    """Legt ein Depot, ein Präparat und mehrere Bewegungen an."""
    db.add_depot("Notfalldepot A", "Musterstr. 1", "0301234567", "depot@a.de")
    db.add_praeparat("Fentanyl")
    depot_id = db.get_depot_id_by_name("Notfalldepot A")
    prae_id = db.get_praeparat_id_by_name("Fentanyl")

    heute = datetime.now().date()
    # Kritisch: in 10 Tagen verfallen
    db.insert_bewegung(
        depot_id, prae_id, "CH-001", (heute + timedelta(days=10)).isoformat(),
        heute.isoformat(), None, None, 5, "Zugang",
    )
    # Warnung: in 60 Tagen verfallen
    db.insert_bewegung(
        depot_id, prae_id, "CH-002", (heute + timedelta(days=60)).isoformat(),
        heute.isoformat(), None, None, 3, "Zugang",
    )
    # Achtung: in 150 Tagen verfallen
    db.insert_bewegung(
        depot_id, prae_id, "CH-003", (heute + timedelta(days=150)).isoformat(),
        heute.isoformat(), None, None, 2, "Zugang",
    )
    # OK: in 300 Tagen verfallen (sollte nicht in 'verfallende' Liste)
    db.insert_bewegung(
        depot_id, prae_id, "CH-004", (heute + timedelta(days=300)).isoformat(),
        heute.isoformat(), None, None, 1, "Zugang",
    )


class TestVerfallManagerInit:
    """Tests für Initialisierung und Schema-Erkennung."""

    def test_init_with_database_shares_connection(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        vm = VerfallManager(database=db)
        assert vm._owns_connection is False
        assert vm.conn is db.conn
        assert vm.cur is db.cur
        vm.close()
        db.conn.close()

    def test_init_with_db_path_legacy_mode(self, temp_db_path: str) -> None:
        Database(temp_db_path)  # schema erstellen
        vm = VerfallManager(db_path=temp_db_path)
        assert vm._owns_connection is True
        assert vm.db_path == temp_db_path
        vm.close()

    def test_init_without_args_raises(self) -> None:
        try:
            VerfallManager()
        except TypeError:
            return
        raise AssertionError("TypeError erwartet bei fehlendem db_path / database")

    def test_schema_detection_recognizes_columns(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        vm = VerfallManager(database=db)
        # bewegungen hat 'anzahl', 'verfall', 'typ'
        assert vm.menge_column == "anzahl"
        assert vm.datum_column == "verfall"
        assert vm.typ_column == "typ"
        # praeparate / depots vorhanden
        assert vm.has_praeparate_table is True
        assert vm.has_depots_table is True
        assert vm.praeparat_name_column == "name"
        assert vm.depot_name_column == "name"
        vm.close()
        db.conn.close()

    def test_warnung_einstellungen_table_created(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        vm = VerfallManager(database=db)
        tables = [
            r[0]
            for r in db.cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "warnung_einstellungen" in tables
        vm.close()
        db.conn.close()


class TestVerfallManagerFindColumn:
    """Tests für _find_column Synonym-Erkennung."""

    def test_find_column_finds_synonym(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        vm = VerfallManager(database=db)
        result = vm._find_column("bewegungen", ["anzahl", "typ", "verfall"], "menge")
        assert result == "anzahl"
        vm.close()
        db.conn.close()

    def test_find_column_returns_none_for_missing(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        vm = VerfallManager(database=db)
        result = vm._find_column("bewegungen", ["typ", "verfall"], "menge")
        assert result is None
        vm.close()
        db.conn.close()

    def test_find_column_case_insensitive(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        vm = VerfallManager(database=db)
        # 'Anzahl' sollte als Synonym für 'menge' erkannt werden
        result = vm._find_column("test", ["Anzahl"], "menge")
        assert result == "Anzahl"
        vm.close()
        db.conn.close()


class TestVerfallManagerValidateColumn:
    """Tests für SQL-Injection-Schutz via Whitelist."""

    def test_validate_column_name_accepts_whitelisted(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        vm = VerfallManager(database=db)
        assert vm._validate_column_name("anzahl") is True
        assert vm._validate_column_name("verfall") is True
        assert vm._validate_column_name("id") is True
        vm.close()
        db.conn.close()

    def test_validate_column_name_rejects_injection(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        vm = VerfallManager(database=db)
        assert vm._validate_column_name("anzahl; DROP TABLE bewegungen") is False
        assert vm._validate_column_name("' OR '1'='1") is False
        vm.close()
        db.conn.close()

    def test_validate_column_name_none_passes(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        vm = VerfallManager(database=db)
        assert vm._validate_column_name(None) is True
        vm.close()
        db.conn.close()


class TestVerfallManagerQueries:
    """Tests für getverfallendepraeparate und abgeleitete Methoden."""

    def test_getverfallendepraeparate_empty_db(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        vm = VerfallManager(database=db)
        result = vm.getverfallendepraeparate()
        assert result == []
        vm.close()
        db.conn.close()

    def test_getverfallendepraeparate_with_data(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        _seed_data(db)
        vm = VerfallManager(database=db)
        result = vm.getverfallendepraeparate()
        # 3 verfallend (kritisch, warnung, achtung); das 'ok' Präparat nicht
        assert len(result) == 3
        kategorien = {item["kategorie"] for item in result}
        assert "kritisch" in kategorien
        assert "warnung" in kategorien
        assert "achtung" in kategorien
        vm.close()
        db.conn.close()

    def test_getverfallendepraeparate_filter_kritisch(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        _seed_data(db)
        vm = VerfallManager(database=db)
        result = vm.getverfallendepraeparate(kategorie="kritisch")
        assert len(result) == 1
        assert result[0]["kategorie"] == "kritisch"
        vm.close()
        db.conn.close()

    def test_getstatistics(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        _seed_data(db)
        vm = VerfallManager(database=db)
        stats = vm.getstatistics()
        assert stats["kritisch"] == 1
        assert stats["warnung"] == 1
        assert stats["achtung"] == 1
        assert stats["gesamt"] == 3
        vm.close()
        db.conn.close()

    def test_getstatistics_empty(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        vm = VerfallManager(database=db)
        stats = vm.getstatistics()
        assert stats == {"kritisch": 0, "warnung": 0, "achtung": 0, "gesamt": 0}
        vm.close()
        db.conn.close()

    def test_getverfallendebydepot(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        _seed_data(db)
        vm = VerfallManager(database=db)
        by_depot = vm.getverfallendebydepot()
        assert len(by_depot) == 1
        depot_id = db.get_depot_id_by_name("Notfalldepot A")
        assert depot_id in by_depot
        assert len(by_depot[depot_id]) == 3
        vm.close()
        db.conn.close()

    def test_getkritischedepots(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        _seed_data(db)
        vm = VerfallManager(database=db)
        kritische = vm.getkritischedepots()
        assert len(kritische) == 1
        assert kritische[0][1] == 1  # ein kritisches Präparat
        vm.close()
        db.conn.close()

    def test_getnaechsteverfaelle_limit(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        _seed_data(db)
        vm = VerfallManager(database=db)
        result = vm.getnaechsteverfaelle(limit=2)
        assert len(result) == 2
        vm.close()
        db.conn.close()

    def test_has_kritische_praeparate_true(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        _seed_data(db)
        vm = VerfallManager(database=db)
        assert vm.has_kritische_praeparate() is True
        vm.close()
        db.conn.close()

    def test_has_kritische_praeparate_false(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        vm = VerfallManager(database=db)
        assert vm.has_kritische_praeparate() is False
        vm.close()
        db.conn.close()


class TestVerfallManagerUpdate:
    """Tests für update_verfallsdatum und update_settings."""

    def test_update_verfallsdatum_valid(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        _seed_data(db)
        vm = VerfallManager(database=db)
        rows = vm.getverfallendepraeparate()
        first_id = rows[0]["id"]
        ok = vm.update_verfallsdatum(first_id, "2027-12-31")
        assert ok is True
        row = db.cur.execute(
            "SELECT verfall FROM bewegungen WHERE id = ?", (first_id,)
        ).fetchone()
        assert row[0] == "2027-12-31"
        vm.close()
        db.conn.close()

    def test_update_verfallsdatum_invalid_format(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        _seed_data(db)
        vm = VerfallManager(database=db)
        rows = vm.getverfallendepraeparate()
        first_id = rows[0]["id"]
        ok = vm.update_verfallsdatum(first_id, "31.12.2025")
        assert ok is False  # Format muss YYYY-MM-DD sein
        vm.close()
        db.conn.close()

    def test_update_settings(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        vm = VerfallManager(database=db)
        ok = vm.update_settings(kritisch=14, warnung=45, achtung=120)
        assert ok is True
        assert vm.KRITISCH == 14
        assert vm.WARNUNG == 45
        assert vm.ACHTUNG == 120
        # Persistenz prüfen
        row = db.cur.execute(
            "SELECT kritisch_tage, warnung_tage, achtung_tage FROM warnung_einstellungen WHERE id = 1"
        ).fetchone()
        assert row[0] == 14
        assert row[1] == 45
        assert row[2] == 120
        vm.close()
        db.conn.close()

    def test_update_settings_partial(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        vm = VerfallManager(database=db)
        ok = vm.update_settings(warnung=60)
        assert ok is True
        assert vm.WARNUNG == 60
        # KRITISCH unverändert
        assert vm.KRITISCH == 30
        vm.close()
        db.conn.close()


class TestVerfallManagerClose:
    """Tests für close()-Verhalten."""

    def test_close_owned_connection(self, temp_db_path: str) -> None:
        Database(temp_db_path)
        vm = VerfallManager(db_path=temp_db_path)
        assert vm._owns_connection is True
        vm.close()
        # conn sollte geschlossen sein — execute schlägt fehl
        try:
            vm.cur.execute("SELECT 1")
        except Exception:
            return
        raise AssertionError("Connection sollte nach close() geschlossen sein")

    def test_close_borrowed_connection_noop(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        vm = VerfallManager(database=db)
        vm.close()
        # db.conn sollte noch funktionieren
        db.cur.execute("SELECT 1").fetchone()
        db.conn.close()
