"""
VerfallManager - Verwaltung von Verfallsdatum-Warnungen
Version: 1.2 - Mit automatischer Synonym-Erkennung
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from db_manager import Database

logger = logging.getLogger(__name__)


class VerfallManager:
    """
    Verwaltet Verfallsdatum-Warnungen für Notfalldepots
    SMART: Erkennt automatisch Synonyme (menge/anzahl, etc.)
    """

    # Warnungs-Schwellwerte (Tage)
    KRITISCH = 30   # Rot
    WARNUNG = 90    # Orange
    ACHTUNG = 180   # Gelb

    # Synonym-Definitionen
    SYNONYME = {
        'menge': ['menge', 'anzahl', 'quantity', 'qty', 'stueck', 'stück'],
        'verfallsdatum': ['verfall', 'ablaufdatum', 'expiry_date', 'expiry', 'verfallsdatum', 'ablauf'],
        'praeparat_name': ['name', 'bezeichnung', 'praeparat_name', 'description', 'desc'],
        'depot_name': ['name', 'bezeichnung', 'depot_name', 'standort', 'location'],
        'pzn': ['pzn', 'pharmazentralnummer', 'artikelnummer', 'article_no'],
        'typ': ['typ', 'type', 'bewegungstyp', 'art']
    }

    def __init__(self, db_path: str = "", *, database: Optional["Database"] = None):
        """
        Initialisiert den VerfallManager

        Args:
            db_path: Pfad zur Datenbank (Legacy-Modus — eigene Connection).
                     Wenn ``database`` übergeben wird, ist ``db_path`` optional.
            database: Optional, eine bestehende ``Database``-Instanz. Wenn
                      übergeben, wird deren Connection geteilt (kein Lock-Contention).
                      Issue #18: Architektur-Audit-Befund.

        Backwards-Kompatibilität:
            Aufrufer ohne ``database``-Argument funktionieren weiterhin
            (eigene Connection). Das ist der Default für Tests und
            Backend-Kontexte, die keine ``Database``-Instanz haben.
        """
        if database is not None:
            # Geteilte Connection — kein zusätzliches connect()
            self._db = database
            self.db_path = database.path
            self.conn = database.conn
            self.cur = database.cur
            self._owns_connection = False
        else:
            # Legacy: eigene Connection
            if not db_path:
                raise TypeError(
                    "VerfallManager benötigt entweder 'db_path' (nicht-leer) oder 'database'"
                )
            self._db = None
            self.db_path = db_path
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.cur = self.conn.cursor()
            self._owns_connection = True

        # Erkenne Schema mit Synonymen
        self._detect_schema_smart()

        # OVERRIDE: Nutze 'verfall' statt 'verfallsdatum'
        self.datum_column = 'verfall'

        # Validiere alle erkannten Spaltennamen gegen die Datenbank (SQL-Injection-Schutz)
        self._validate_all_columns()

        # Erstelle Einstellungen-Tabelle
        self._create_tables()
        self._load_settings()

        logger.info(
            "VerfallManager initialisiert (Smart-Modus, %s)",
            "geteilt mit Database" if self._owns_connection is False else "eigene Connection",
        )

    # Whitelist: Nur diese Spaltennamen sind in dynamischem SQL erlaubt
    ALLOWED_COLUMNS = frozenset([
        'menge', 'anzahl', 'quantity', 'qty', 'stueck', 'stück',
        'verfall', 'ablaufdatum', 'expiry_date', 'expiry', 'verfallsdatum', 'ablauf',
        'name', 'bezeichnung', 'praeparat_name', 'description', 'desc',
        'depot_name', 'standort', 'location',
        'pzn', 'pharmazentralnummer', 'artikelnummer', 'article_no',
        'typ', 'type', 'bewegungstyp', 'art',
        'id', 'depot_id', 'praeparat_id',
    ])

    def _validate_column_name(self, column_name: str) -> bool:
        """
        Prüft ob ein Spaltenname in der Whitelist enthalten ist.
        Verhindert SQL-Injection über dynamische Spaltennamen.
        """
        if column_name is None:
            return True  # None wird beim Query-Bau ohnehin übersprungen
        clean = column_name.lower().strip()
        if clean not in self.ALLOWED_COLUMNS:
            logger.error(f"SICHERHEIT: Spaltenname '{column_name}' ist NICHT in der Whitelist! Abgelehnt.")
            return False
        return True

    def _validate_all_columns(self):
        """Validiert alle erkannten Spaltennamen gegen die Whitelist."""
        for attr_name in ('menge_column', 'datum_column', 'typ_column',
                          'praeparat_name_column', 'depot_name_column', 'pzn_column'):
            col = getattr(self, attr_name, None)
            if col and not self._validate_column_name(col):
                logger.warning(f"Setze {attr_name} auf None (Whitelist-Verletzung)")
                setattr(self, attr_name, None)

    def _find_column(self, table_name: str, column_names: list[str], synonym_key: str) -> str:
        """
        Findet eine Spalte anhand von Synonymen

        Args:
            table_name: Name der Tabelle (für Logging)
            column_names: Verfügbare Spaltennamen
            synonym_key: Key in SYNONYME dict

        Returns:
            Gefundener Spaltenname oder None
        """
        synonyms = self.SYNONYME.get(synonym_key, [])

        # Normalisiere Spaltennamen (lowercase, ohne Unterstriche)
        normalized = {col.lower().replace('_', ''): col for col in column_names}

        # Suche nach Synonym
        for synonym in synonyms:
            normalized_synonym = synonym.lower().replace('_', '')
            if normalized_synonym in normalized:
                found = normalized[normalized_synonym]
                logger.info(f"✓ {table_name}.{synonym_key}: '{found}' (Synonym: '{synonym}')")
                return found

        logger.warning(f"✗ {table_name}.{synonym_key}: Nicht gefunden! Gesucht: {synonyms}")
        return None

    def _detect_schema_smart(self):
        """Erkennt das Datenbank-Schema mit Synonym-Unterstützung"""
        try:
            # === BEWEGUNGEN TABELLE ===
            logger.info("="*60)
            logger.info("Erkenne Schema: BEWEGUNGEN")
            logger.info("="*60)

            columns = self.cur.execute("PRAGMA table_info(bewegungen)").fetchall()
            column_names = [col[1] for col in columns]
            logger.info(f"Verfügbare Spalten: {column_names}")

            # Finde Spalten mit Synonymen
            self.menge_column = self._find_column('bewegungen', column_names, 'menge')
            self.datum_column = self._find_column('bewegungen', column_names, 'verfallsdatum')
            self.typ_column = self._find_column('bewegungen', column_names, 'typ')

            # === TABELLEN-CHECK ===
            logger.info("="*60)
            logger.info("Erkenne Tabellen")
            logger.info("="*60)

            tables = self.cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [t[0] for t in tables]
            logger.info(f"Verfügbare Tabellen: {table_names}")

            self.has_praeparate_table = 'praeparate' in table_names
            self.has_depots_table = 'depots' in table_names

            # === PRAEPARATE TABELLE ===
            if self.has_praeparate_table:
                logger.info("="*60)
                logger.info("Erkenne Schema: PRAEPARATE")
                logger.info("="*60)

                prae_columns = self.cur.execute("PRAGMA table_info(praeparate)").fetchall()
                prae_column_names = [col[1] for col in prae_columns]
                logger.info(f"Verfügbare Spalten: {prae_column_names}")

                self.praeparat_name_column = self._find_column('praeparate', prae_column_names, 'praeparat_name')
                self.pzn_column = self._find_column('praeparate', prae_column_names, 'pzn')

                self.has_pzn = self.pzn_column is not None
            else:
                logger.warning("Tabelle 'praeparate' nicht gefunden")
                self.praeparat_name_column = None
                self.pzn_column = None
                self.has_pzn = False

            # === DEPOTS TABELLE ===
            if self.has_depots_table:
                logger.info("="*60)
                logger.info("Erkenne Schema: DEPOTS")
                logger.info("="*60)

                depot_columns = self.cur.execute("PRAGMA table_info(depots)").fetchall()
                depot_column_names = [col[1] for col in depot_columns]
                logger.info(f"Verfügbare Spalten: {depot_column_names}")

                self.depot_name_column = self._find_column('depots', depot_column_names, 'depot_name')
            else:
                logger.warning("Tabelle 'depots' nicht gefunden")
                self.depot_name_column = None

            # === ZUSAMMENFASSUNG ===
            logger.info("="*60)
            logger.info("Schema-Erkennung abgeschlossen")
            logger.info("="*60)
            logger.info(f"Menge-Spalte: {self.menge_column}")
            logger.info(f"Datum-Spalte: {self.datum_column}")
            logger.info(f"Typ-Spalte: {self.typ_column}")
            logger.info(f"Präparat-Name: {self.praeparat_name_column}")
            logger.info(f"Depot-Name: {self.depot_name_column}")
            logger.info(f"PZN: {self.pzn_column}")
            logger.info("="*60)

        except Exception as e:
            logger.error(f"Fehler beim Schema-Erkennung: {e}")
            # Sicherer Fallback: Spalten NICHT hartcoden — das wäre ein Bug,
            # wenn die Spalte im echten Schema anders heißt. Stattdessen None
            # setzen, damit Query-Builder die Spalte überspringt und ein
            # sprechender Fehler geworfen wird, statt SQL-Fehlermeldungen
            # zur Laufzeit.
            self.menge_column = None
            self.datum_column = None
            self.typ_column = None
            self.has_praeparate_table = False
            self.has_depots_table = False
            self.praeparat_name_column = None
            self.depot_name_column = None
            self.pzn_column = None
            self.has_pzn = False
            # Konsistenz-Check gegen die Whitelist (Security)
            self._validate_all_columns()

    def _create_tables(self):
        """Erstellt die Tabellen für Warnungs-Einstellungen"""
        # Prüfe/erstelle Datum-Spalte
        if not self.datum_column:
            logger.warning("Füge verfallsdatum-Spalte hinzu")
            try:
                self.cur.execute("ALTER TABLE bewegungen ADD COLUMN verfallsdatum TEXT")
                self.conn.commit()
                self.datum_column = 'verfallsdatum'
            except sqlite3.OperationalError as e:
                logger.error(f"Konnte Spalte nicht hinzufügen: {e}")

        # Einstellungen-Tabelle
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS warnung_einstellungen (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                kritisch_tage INTEGER DEFAULT 30,
                warnung_tage INTEGER DEFAULT 90,
                achtung_tage INTEGER DEFAULT 180,
                email_benachrichtigung INTEGER DEFAULT 0,
                email_adresse TEXT,
                letzter_versand TEXT
            )
        """)
        self.conn.commit()

    def _load_settings(self):
        """Lädt die Warnungs-Einstellungen"""
        row = self.cur.execute(
            "SELECT kritisch_tage, warnung_tage, achtung_tage FROM warnung_einstellungen WHERE id = 1"
        ).fetchone()

        if row:
            self.KRITISCH, self.WARNUNG, self.ACHTUNG = row
        else:
            # Erstelle Standard-Einstellungen
            self.cur.execute("""
                INSERT INTO warnung_einstellungen (id, kritisch_tage, warnung_tage, achtung_tage)
                VALUES (1, 30, 90, 180)
            """)
            self.conn.commit()
            logger.info("Standard-Warnungs-Einstellungen erstellt")

    def getverfallendepraeparate(self, kategorie: str = None) -> list[dict]:
        """
        Holt alle verfallenden Präparate aus bestehendem System
        SMART: Nutzt automatisch erkannte Spaltennamen

        Args:
            kategorie: Optional - "kritisch", "warnung", "achtung" oder None (alle)

        Returns:
            Liste von Dicts mit Informationen über verfallende Präparate
        """
        if not self.datum_column:
            logger.error("Keine Datum-Spalte verfügbar")
            return []

        if not self.menge_column:
            logger.error("Keine Mengen-Spalte verfügbar")
            return []

        heute = datetime.now().date()

        # Berechne Grenzwerte
        kritisch_datum = (heute + timedelta(days=self.KRITISCH)).isoformat()
        warnung_datum = (heute + timedelta(days=self.WARNUNG)).isoformat()
        achtung_datum = (heute + timedelta(days=self.ACHTUNG)).isoformat()

        try:
            # === QUERY BAUEN ===

            # SELECT Teil
            select_parts = [
                "b.id",
                "b.depot_id",
            ]

            # Depot-Name
            if self.has_depots_table and self.depot_name_column:
                select_parts.append(f"COALESCE(d.{self.depot_name_column}, 'Depot ' || b.depot_id) as depot_name")
            else:
                select_parts.append("'Depot ' || b.depot_id as depot_name")

            # Präparat-ID und Name
            select_parts.append("b.praeparat_id")

            if self.has_praeparate_table and self.praeparat_name_column:
                select_parts.append(f"COALESCE(p.{self.praeparat_name_column}, 'Präparat ' || b.praeparat_id) as praeparat_name")
            else:
                select_parts.append("'Präparat ' || b.praeparat_id as praeparat_name")

            # PZN (optional)
            if self.has_pzn and self.pzn_column:
                select_parts.append(f"COALESCE(p.{self.pzn_column}, '') as pzn")
            else:
                select_parts.append("'' as pzn")

            # Menge und Datum
            select_parts.append(f"b.{self.menge_column} as menge")
            select_parts.append(f"b.{self.datum_column} as verfallsdatum")

            # Kategorie und Tage bis Verfall
            select_parts.append(f"""
                CASE
                    WHEN b.{self.datum_column} <= ? THEN 'kritisch'
                    WHEN b.{self.datum_column} <= ? THEN 'warnung'
                    WHEN b.{self.datum_column} <= ? THEN 'achtung'
                    ELSE 'ok'
                END as kategorie
            """)

            select_parts.append(f"""
                CAST((julianday(b.{self.datum_column}) - julianday('now')) AS INTEGER) as tage_bis_verfall
            """)

            # FROM und JOIN Teil
            from_part = "FROM bewegungen b"

            if self.has_depots_table:
                from_part += " LEFT JOIN depots d ON b.depot_id = d.id"

            if self.has_praeparate_table:
                from_part += " LEFT JOIN praeparate p ON b.praeparat_id = p.id"

            # WHERE Teil
            where_parts = []

            # Typ prüfen
            if self.typ_column:
                where_parts.append(f"b.{self.typ_column} = 'Zugang'")

            # Menge > 0
            where_parts.append(f"b.{self.menge_column} > 0")

            # Datum <= Achtung (zeigt auch verfallene Präparate)
            where_parts.append(f"b.{self.datum_column} <= ?")

            # Datum nicht leer
            where_parts.append(f"b.{self.datum_column} IS NOT NULL")
            where_parts.append(f"b.{self.datum_column} != ''")

            where_clause = "WHERE " + " AND ".join(where_parts)

            # Komplette Query
            query = f"""  # nosec B608: column names validated against ALLOWED_COLUMNS
                SELECT
                    {', '.join(select_parts)}
                {from_part}
                {where_clause}
                ORDER BY b.{self.datum_column} ASC
            """

            logger.info("Ausgeführte Query (gekürzt):")
            logger.info(query[:500] + "..." if len(query) > 500 else query)

            params = (kritisch_datum, warnung_datum, achtung_datum, achtung_datum)
            rows = self.cur.execute(query, params).fetchall()

        except sqlite3.OperationalError as e:
            logger.error(f"Datenbankfehler: {e}")
            logger.info("Versuche Minimal-Query...")

            # Absolut minimale Query
            try:
                if not self._validate_column_name(self.menge_column) or not self._validate_column_name(self.datum_column):
                    raise ValueError("Ungültiger Spaltenname für Minimal-Query")
                menge_col = self.menge_column
                datum_col = self.datum_column
                query = (
                    "SELECT\n"  # nosec B608: menge_col and datum_col validated above
                    "    id,\n"
                    "    depot_id,\n"
                    "    'Depot' as depot_name,\n"
                    "    praeparat_id,\n"
                    "    'Präparat' as praeparat_name,\n"
                    "    '' as pzn,\n"
                    "    " + menge_col + " as menge,\n"
                    "    " + datum_col + " as verfallsdatum,\n"
                    "    'achtung' as kategorie,\n"
                    "    0 as tage_bis_verfall\n"
                    "FROM bewegungen\n"
                    "WHERE " + menge_col + " > 0\n"
                    "  AND " + datum_col + " IS NOT NULL\n"
                    "  AND " + datum_col + " != ''\n"
                    "  AND " + datum_col + " <= ?"
                )

                rows = self.cur.execute(query, (achtung_datum,)).fetchall()
                logger.info("Minimal-Query erfolgreich")

            except Exception as e2:
                logger.error(f"Auch Minimal-Query fehlgeschlagen: {e2}")
                return []

        result = []
        for row in rows:
            data = {
                'id': row[0],
                'depot_id': row[1],
                'depot_name': row[2],
                'praeparat_id': row[3],
                'praeparat_name': row[4],
                'pzn': row[5] or '',
                'menge': row[6],
                'verfallsdatum': row[7],
                'kategorie': row[8],
                'tage_bis_verfall': row[9]
            }

            # Filtere nach Kategorie wenn angegeben
            if kategorie is None or data['kategorie'] == kategorie:
                result.append(data)

        logger.info(f"✓ {len(result)} verfallende Präparate gefunden")
        return result

    def getstatistics(self) -> dict:
        """Gibt Statistiken über verfallende Präparate zurück"""
        verfallende = self.getverfallendepraeparate()

        stats = {
            'kritisch': 0,
            'warnung': 0,
            'achtung': 0,
            'gesamt': len(verfallende)
        }

        for item in verfallende:
            kategorie = item['kategorie']
            if kategorie in stats:
                stats[kategorie] += 1

        return stats

    def getverfallendebydepot(self) -> dict[int, list[dict]]:
        """Gruppiert verfallende Präparate nach Depot"""
        verfallende = self.getverfallendepraeparate()

        by_depot = {}
        for item in verfallende:
            depot_id = item['depot_id']
            if depot_id not in by_depot:
                by_depot[depot_id] = []
            by_depot[depot_id].append(item)

        return by_depot

    def getkritischedepots(self) -> list[tuple[str, int]]:
        """Gibt Depots mit den meisten kritischen Präparaten zurück"""
        kritische = self.getverfallendepraeparate(kategorie='kritisch')

        depot_count = {}
        for item in kritische:
            depot_name = item['depot_name']
            depot_count[depot_name] = depot_count.get(depot_name, 0) + 1

        sorted_depots = sorted(depot_count.items(), key=lambda x: x[1], reverse=True)

        return sorted_depots

    def update_verfallsdatum(self, bewegung_id: int, verfallsdatum: str) -> bool:
        """Aktualisiert das Verfallsdatum einer Bewegung"""
        if not self.datum_column:
            logger.error("Keine Datum-Spalte verfügbar")
            return False

        try:
            datetime.strptime(verfallsdatum, '%Y-%m-%d')

            if not self._validate_column_name(self.datum_column):
                raise ValueError("Ungültiger Spaltenname für Verfallsdatum-Update")
            self.cur.execute(
                "UPDATE bewegungen SET " + self.datum_column + " = ? WHERE id = ?",  # nosec B608: datum_column validated against ALLOWED_COLUMNS
                (verfallsdatum, bewegung_id)
            )
            self.conn.commit()

            logger.info(f"Verfallsdatum für Bewegung {bewegung_id} aktualisiert: {verfallsdatum}")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren: {e}")
            return False

    def update_settings(self, kritisch: int = None, warnung: int = None, achtung: int = None) -> bool:
        """Aktualisiert die Warnungs-Schwellwerte"""
        updates = []
        params = []

        if kritisch is not None:
            updates.append("kritisch_tage = ?")
            params.append(kritisch)
            self.KRITISCH = kritisch

        if warnung is not None:
            updates.append("warnung_tage = ?")
            params.append(warnung)
            self.WARNUNG = warnung

        if achtung is not None:
            updates.append("achtung_tage = ?")
            params.append(achtung)
            self.ACHTUNG = achtung

        if updates:
            query = "UPDATE warnung_einstellungen SET " + ", ".join(updates) + " WHERE id = 1"  # nosec B608: updates built from hardcoded column=? strings
            self.cur.execute(query, params)
            self.conn.commit()

            logger.info("Warnungs-Einstellungen aktualisiert")

        return True

    def export_to_excel(self, filename: str, kategorie: str = None) -> bool:
        """Exportiert verfallende Präparate nach Excel"""
        try:
            import pandas as pd

            verfallende = self.getverfallendepraeparate(kategorie=kategorie)

            if not verfallende:
                logger.warning("Keine verfallenden Präparate zum Exportieren")
                return False

            df = pd.DataFrame(verfallende)
            df = df.sort_values('verfallsdatum')

            # Wähle relevante Spalten
            if self.has_pzn and df['pzn'].any():
                columns = ['depot_name', 'praeparat_name', 'pzn', 'menge',
                          'verfallsdatum', 'tage_bis_verfall', 'kategorie']
                column_names = ['Depot', 'Präparat', 'PZN', 'Menge',
                               'Verfallsdatum', 'Tage bis Verfall', 'Kategorie']
            else:
                columns = ['depot_name', 'praeparat_name', 'menge',
                          'verfallsdatum', 'tage_bis_verfall', 'kategorie']
                column_names = ['Depot', 'Präparat', 'Menge',
                               'Verfallsdatum', 'Tage bis Verfall', 'Kategorie']

            df = df[columns]
            df.columns = column_names

            df.to_excel(filename, index=False, engine='openpyxl')

            logger.info(f"Export erfolgreich: {filename}")
            return True
        except ImportError:
            logger.error("pandas/openpyxl nicht installiert")
            return False
        except Exception as e:
            logger.error(f"Fehler beim Excel-Export: {e}")
            return False

    def getnaechsteverfaelle(self, limit: int = 10) -> list[dict]:
        """Gibt die nächsten X verfallenden Präparate zurück"""
        verfallende = self.getverfallendepraeparate()
        return verfallende[:limit]

    def has_kritische_praeparate(self) -> bool:
        """Prüft ob es kritische (< 30 Tage) Präparate gibt"""
        kritische = self.getverfallendepraeparate(kategorie='kritisch')
        return len(kritische) > 0

    def close(self):
        """Schließt die Datenbankverbindung — aber nur, wenn wir sie besitzen.

        Issue #18: Falls die Connection von einer Database-Instanz geliehen
        ist, dürfen wir sie nicht schließen (Database kümmert sich darum).
        """
        if not getattr(self, "_owns_connection", True):
            return  # Connection ist geliehen, Database schließt sie
        if self.conn:
            try:
                self.conn.close()
            except Exception as exc:  # noqa: BLE001
                logger.debug("VerfallManager close fehlgeschlagen: %s", exc)
            logger.info("VerfallManager geschlossen")
