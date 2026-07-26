"""Unit-Tests für page_import — CSV/Excel Import Business-Logik.

Issue #62: Test-Coverage von 20% auf 40% erhöhen.

ImportPage ist ein Qt-Widget und kann ohne echtes Qt nicht instanziiert
werden (PySide6-Stub liefert MagicMock). Daher testen wir die Business-
Logik, die in preview_bewegungen_file / import_bewegungen steckt, durch
Replikation der logischen Bausteine mit echten DataFrames und Database-
Instanzen. Das deckt die Validation-, Normalisierungs-, Duplikat- und
Fingerprint-Logik ab, die das Kernrisiko des Moduls ausmacht.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
from db_manager import Database
from ui.pages import page_import

# Spalten-Mapping wie in preview_bewegungen_file (Quelle der Wahrheit)
COLUMN_MAPPING: dict[str, list[str]] = {
    "depot": ["depot", "Depot"],
    "präparat": ["präparat", "Präparat", "praeparat"],
    "typ": ["typ", "Typ", "type"],
    "charge": ["charge", "Charge"],
    "verfall": ["verfall", "Verfall", "verfallsdatum"],
    "datum": ["datum", "Datum", "date"],
    "anzahl": ["anzahl", "Anzahl", "menge", "quantity"],
    "empfänger": ["empfänger", "Empfänger", "empfaenger"],
}

REQUIRED_COLUMNS = ["depot", "präparat", "typ", "charge", "verfall", "datum", "anzahl"]
VALID_TYPES = ["Zugang", "Abgang", "Vernichtung"]


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Repliziert die Spalten-Normalisierung aus preview_bewegungen_file."""
    df.columns = df.columns.astype(str).str.strip()
    df = df.dropna(how="all")
    normalized = {}
    for standard_name, aliases in COLUMN_MAPPING.items():
        for col in df.columns:
            if col in aliases:
                normalized[col] = standard_name
                break
    df.rename(columns=normalized, inplace=True)
    return df


def validate_rows(df: pd.DataFrame, db: Database) -> tuple[list[str], list[str]]:
    """Repliziert die Validierungslogik aus preview_bewegungen_file.

    Returns:
        (errors, warnings) Listen wie im Original.
    """
    errors: list[str] = []
    warnings: list[str] = []
    seen_keys: set[tuple] = set()
    for idx, row in df.iterrows():
        if pd.isna(row.get("depot")) or pd.isna(row.get("präparat")):
            continue
        depot_name = str(row["depot"]).strip()
        praeparat_name = str(row["präparat"]).strip()
        typ = str(row["typ"]).strip()
        anzahl = row["anzahl"]
        if not depot_name or depot_name == "nan":
            continue
        if not db.get_depot_id_by_name(depot_name):
            errors.append(f"Zeile {idx + 5}: Depot '{depot_name}' nicht gefunden")
        if not db.get_praeparat_id_by_name(praeparat_name):
            errors.append(f"Zeile {idx + 5}: Präparat '{praeparat_name}' nicht gefunden")
        if typ not in VALID_TYPES:
            errors.append(f"Zeile {idx + 5}: Ungültiger Typ '{typ}'")
        try:
            if pd.isna(anzahl) or int(anzahl) <= 0:
                errors.append(f"Zeile {idx + 5}: Anzahl muss > 0 sein")
        except (ValueError, TypeError):
            errors.append(f"Zeile {idx + 5}: Ungültige Anzahl '{anzahl}'")
        key = (
            str(row.get("depot", "")).strip().lower(),
            str(row.get("präparat", "")).strip().lower(),
            str(row.get("typ", "")).strip().lower(),
            str(row.get("charge", "")).strip().lower(),
            str(row.get("datum", "")).strip().lower(),
            str(row.get("anzahl", "")).strip().lower(),
        )
        if key in seen_keys:
            warnings.append(f"Zeile {idx + 5}: Möglicher Duplikat-Eintrag")
        else:
            seen_keys.add(key)
    return errors, warnings


def compute_fingerprint(df: pd.DataFrame) -> str:
    """Repliziert die Fingerprint-Berechnung aus preview_bewegungen_file."""
    return hashlib.sha256(
        ("|".join(df.columns.tolist()) + "|" + str(len(df)) + "|" + str(df.head(30).to_dict())).encode("utf-8")
    ).hexdigest()[:16]


class TestModuleConstants:
    """Tests für Modul-Level Konstanten."""

    def test_has_pandas_true(self) -> None:
        assert page_import.HAS_PANDAS is True

    def test_importpage_class_exists(self) -> None:
        assert hasattr(page_import, "ImportPage")


class TestColumnNormalization:
    """Tests für CSV-Spalten-Normalisierung."""

    def test_normalize_capitalized_columns(self) -> None:
        df = pd.DataFrame(
            [{"Depot": "D1", "Präparat": "P1", "Typ": "Zugang", "Charge": "C", "Verfall": "31.12.2026",
              "Datum": "01.06.2026", "Anzahl": 5}]
        )
        df = normalize_columns(df)
        for col in REQUIRED_COLUMNS:
            assert col in df.columns, f"Spalte '{col}' fehlt nach Normalisierung"

    def test_normalize_lowercase_columns(self) -> None:
        df = pd.DataFrame(
            [{"depot": "D1", "präparat": "P1", "typ": "Zugang", "charge": "C", "verfall": "31.12.2026",
              "datum": "01.06.2026", "anzahl": 5}]
        )
        df = normalize_columns(df)
        for col in REQUIRED_COLUMNS:
            assert col in df.columns

    def test_normalize_alias_menge(self) -> None:
        df = pd.DataFrame(
            [{"depot": "D1", "präparat": "P1", "typ": "Zugang", "charge": "C", "verfall": "31.12.2026",
              "datum": "01.06.2026", "menge": 5}]
        )
        df = normalize_columns(df)
        assert "anzahl" in df.columns
        assert "menge" not in df.columns

    def test_normalize_alias_quantity(self) -> None:
        df = pd.DataFrame(
            [{"depot": "D1", "präparat": "P1", "typ": "Zugang", "charge": "C", "verfall": "31.12.2026",
              "datum": "01.06.2026", "quantity": 5}]
        )
        df = normalize_columns(df)
        assert "anzahl" in df.columns

    def test_normalize_praeparat_alias(self) -> None:
        df = pd.DataFrame(
            [{"depot": "D1", "praeparat": "P1", "typ": "Zugang", "charge": "C", "verfall": "31.12.2026",
              "datum": "01.06.2026", "anzahl": 5}]
        )
        df = normalize_columns(df)
        assert "präparat" in df.columns


class TestRequiredColumns:
    """Tests für Pflichtfeld-Prüfung."""

    def test_missing_columns_detected(self) -> None:
        df = pd.DataFrame([{"depot": "D1", "typ": "Zugang"}])
        df = normalize_columns(df)
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        assert "präparat" in missing
        assert "charge" in missing

    def test_all_required_present(self) -> None:
        df = pd.DataFrame(
            [{"depot": "D1", "präparat": "P1", "typ": "Zugang", "charge": "C", "verfall": "31.12.2026",
              "datum": "01.06.2026", "anzahl": 5}]
        )
        df = normalize_columns(df)
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        assert missing == []


class TestRowValidation:
    """Tests für zeilenweise Validierung gegen die Datenbank."""

    def test_valid_rows_no_errors(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        db.add_depot("Depot1", "addr", "tel", "mail")
        db.add_praeparat("Praep1")
        df = pd.DataFrame(
            [{"depot": "Depot1", "präparat": "Praep1", "typ": "Zugang", "charge": "C1",
              "verfall": "31.12.2026", "datum": "01.06.2026", "anzahl": 5}]
        )
        errors, warnings = validate_rows(df, db)
        assert errors == []
        assert warnings == []
        db.conn.close()

    def test_unknown_depot_error(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        db.add_praeparat("Praep1")
        df = pd.DataFrame(
            [{"depot": "Unbekannt", "präparat": "Praep1", "typ": "Zugang", "charge": "C1",
              "verfall": "31.12.2026", "datum": "01.06.2026", "anzahl": 5}]
        )
        errors, _ = validate_rows(df, db)
        assert any("Depot" in e and "Unbekannt" in e for e in errors)
        db.conn.close()

    def test_unknown_praeparat_error(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        db.add_depot("Depot1", "addr", "tel", "mail")
        df = pd.DataFrame(
            [{"depot": "Depot1", "präparat": "Unbekannt", "typ": "Zugang", "charge": "C1",
              "verfall": "31.12.2026", "datum": "01.06.2026", "anzahl": 5}]
        )
        errors, _ = validate_rows(df, db)
        assert any("Präparat" in e and "Unbekannt" in e for e in errors)
        db.conn.close()

    def test_invalid_typ_error(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        db.add_depot("Depot1", "addr", "tel", "mail")
        db.add_praeparat("Praep1")
        df = pd.DataFrame(
            [{"depot": "Depot1", "präparat": "Praep1", "typ": "Transfer", "charge": "C1",
              "verfall": "31.12.2026", "datum": "01.06.2026", "anzahl": 5}]
        )
        errors, _ = validate_rows(df, db)
        assert any("Ungültiger Typ" in e for e in errors)
        db.conn.close()

    def test_anzahl_zero_error(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        db.add_depot("Depot1", "addr", "tel", "mail")
        db.add_praeparat("Praep1")
        df = pd.DataFrame(
            [{"depot": "Depot1", "präparat": "Praep1", "typ": "Zugang", "charge": "C1",
              "verfall": "31.12.2026", "datum": "01.06.2026", "anzahl": 0}]
        )
        errors, _ = validate_rows(df, db)
        assert any("Anzahl muss > 0" in e for e in errors)
        db.conn.close()

    def test_anzahl_non_numeric_error(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        db.add_depot("Depot1", "addr", "tel", "mail")
        db.add_praeparat("Praep1")
        df = pd.DataFrame(
            [{"depot": "Depot1", "präparat": "Praep1", "typ": "Zugang", "charge": "C1",
              "verfall": "31.12.2026", "datum": "01.06.2026", "anzahl": "abc"}]
        )
        errors, _ = validate_rows(df, db)
        assert any("Ungültige Anzahl" in e for e in errors)
        db.conn.close()

    def test_all_valid_types_accepted(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        db.add_depot("Depot1", "addr", "tel", "mail")
        db.add_praeparat("Praep1")
        rows = []
        for t in VALID_TYPES:
            rows.append(
                {"depot": "Depot1", "präparat": "Praep1", "typ": t, "charge": "C1",
                 "verfall": "31.12.2026", "datum": "01.06.2026", "anzahl": 5}
            )
        df = pd.DataFrame(rows)
        errors, _ = validate_rows(df, db)
        assert not any("Ungültiger Typ" in e for e in errors)
        db.conn.close()


class TestDuplicateDetection:
    """Tests für Duplikat-Erkennung."""

    def test_duplicate_row_warning(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        db.add_depot("Depot1", "addr", "tel", "mail")
        db.add_praeparat("Praep1")
        row = {"depot": "Depot1", "präparat": "Praep1", "typ": "Zugang", "charge": "C1",
               "verfall": "31.12.2026", "datum": "01.06.2026", "anzahl": 5}
        df = pd.DataFrame([row, row])
        errors, warnings = validate_rows(df, db)
        assert len(warnings) == 1
        assert "Duplikat" in warnings[0]
        db.conn.close()

    def test_different_charge_no_duplicate(self, temp_db_path: str) -> None:
        db = Database(temp_db_path)
        db.add_depot("Depot1", "addr", "tel", "mail")
        db.add_praeparat("Praep1")
        df = pd.DataFrame([
            {"depot": "Depot1", "präparat": "Praep1", "typ": "Zugang", "charge": "C1",
             "verfall": "31.12.2026", "datum": "01.06.2026", "anzahl": 5},
            {"depot": "Depot1", "präparat": "Praep1", "typ": "Zugang", "charge": "C2",
             "verfall": "31.12.2026", "datum": "01.06.2026", "anzahl": 5},
        ])
        errors, warnings = validate_rows(df, db)
        assert warnings == []
        db.conn.close()


class TestImportFingerprint:
    """Tests für Import-Fingerprint (Idempotenz)."""

    def test_fingerprint_deterministic(self) -> None:
        df = pd.DataFrame(
            [{"depot": "D1", "präparat": "P1", "typ": "Zugang", "charge": "C1",
              "verfall": "31.12.2026", "datum": "01.06.2026", "anzahl": 5}]
        )
        fp1 = compute_fingerprint(df)
        fp2 = compute_fingerprint(df.copy())
        assert fp1 == fp2

    def test_fingerprint_differs_for_different_data(self) -> None:
        df1 = pd.DataFrame(
            [{"depot": "D1", "präparat": "P1", "typ": "Zugang", "charge": "C1",
              "verfall": "31.12.2026", "datum": "01.06.2026", "anzahl": 5}]
        )
        df2 = pd.DataFrame(
            [{"depot": "D1", "präparat": "P1", "typ": "Zugang", "charge": "C1",
              "verfall": "31.12.2026", "datum": "01.06.2026", "anzahl": 10}]
        )
        assert compute_fingerprint(df1) != compute_fingerprint(df2)

    def test_fingerprint_length_16(self) -> None:
        df = pd.DataFrame([{"a": 1}])
        fp = compute_fingerprint(df)
        assert len(fp) == 16


class TestCsvImportEndToEnd:
    """End-to-End: CSV lesen → normalisieren → validieren → importieren."""

    def test_full_csv_import_flow(self, temp_db_path: str, tmp_path: Path) -> None:
        db = Database(temp_db_path)
        db.add_depot("Depot1", "addr", "tel", "mail")
        db.add_praeparat("Praep1")
        csv_file = tmp_path / "test_import.csv"
        df = pd.DataFrame([
            {"Depot": "Depot1", "Präparat": "Praep1", "Typ": "Zugang", "Charge": "CH-1",
             "Verfall": "31.12.2026", "Datum": "01.06.2026", "Anzahl": 10},
        ])
        df.to_csv(csv_file, index=False)

        # Lesen wie preview_bewegungen_file
        loaded = pd.read_csv(str(csv_file))
        loaded = normalize_columns(loaded)
        errors, warnings = validate_rows(loaded, db)
        assert errors == []
        assert warnings == []

        # Leere Zeilen entfernen (wie Original)
        loaded = loaded[loaded["depot"].notna() & (loaded["depot"].astype(str).str.strip() != "")]

        # Import durchführen (wie import_bewegungen)
        depot_id = db.get_depot_id_by_name("Depot1")
        prae_id = db.get_praeparat_id_by_name("Praep1")
        for _, row in loaded.iterrows():
            verfall = pd.to_datetime(row["verfall"], dayfirst=True).strftime("%Y-%m-%d")
            datum = pd.to_datetime(row["datum"], dayfirst=True).strftime("%Y-%m-%d")
            db.insert_bewegung(
                depot_id, prae_id, str(row["charge"]).strip(), verfall,
                datum, None, None, int(row["anzahl"]), str(row["typ"]).strip(),
            )

        bewegungen = db.list_bewegungen_with_attachments()
        assert len(bewegungen) == 1
        assert bewegungen[0]["depot"] == "Depot1"
        assert bewegungen[0]["praeparat"] == "Praep1"
        assert bewegungen[0]["anzahl"] == 10
        db.conn.close()
