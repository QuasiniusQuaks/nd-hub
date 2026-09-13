"""Database-Layer für die ND-Hub Desktop-Anwendung.

.. note::
   Dieses Modul verwendet ``cachetools.TTLCache`` über
   ``core.cache_helpers.cached_method`` für Lookup-Methoden (siehe Issue #35).
   Der Decorator legt pro Instanz einen TTL-Cache an und bietet zwei
   Vorteile gegenüber ``functools.lru_cache``:

   1. **TTL-basierte Eviction**: Einträge verfallen automatisch nach
      konfigurierbarer Zeit (Standard 300s für Stammdaten), was
      veraltete Werte reduziert.
   2. **Explizite Invalidierung**: ``clear_all_caches(self)`` leert alle
      Method-Caches einer Instanz auf einmal.

   Trotzdem muss ``_clear_lookup_caches()`` nach jeder schreibenden
   Operation explizit aufgerufen werden, damit der nächste Lesezugriff
   garantiert frische Daten sieht.
"""
import logging
import sqlite3
import uuid

from core.cache_helpers import clear_all_caches
from core.db.analytics import AnalyticsMixin
from core.db.analytics_charts import AnalyticsChartsMixin
from core.db.analytics_saved import AnalyticsSavedMixin
from core.db.bewegungen import BewegungenMixin
from core.db.constants import DB, SettingKey, TableName
from core.db.email_service import EmailServiceMixin
from core.db.lookups import LookupsMixin
from core.db.setup_wizard import SetupWizardMixin
from core.db.stammdaten import StammdatenMixin
from core.db.sync_apply import SyncApplyMixin
from core.db.sync_outbox import SyncOutboxMixin
from core.db.test_data import TestDataMixin
from PySide6 import QtWidgets
from PySide6.QtCore import QDate, Qt

logger = logging.getLogger(__name__)

__all__ = ["DB", "Database", "SettingKey", "TableName", "fill_table", "to_iso"]


class Database(
    AnalyticsChartsMixin,
    AnalyticsMixin,
    AnalyticsSavedMixin,
    SyncOutboxMixin,
    SyncApplyMixin,
    SetupWizardMixin,
    StammdatenMixin,
    LookupsMixin,
    BewegungenMixin,
    EmailServiceMixin,
    TestDataMixin,
):
    def __init__(self, path: str):
        self.path = path
        self.db_path = path  # Für Kompatibilität
        self.session_id = str(uuid.uuid4())
        self.write_lease_owner = False
        self._connect()
        self._create_schema()
        self._migrate_depots_institution_column()
        self._migrate_address_split_columns()
        self._migrate_praeparate_extended_columns()
        self._add_attachment_column()
        self._create_email_table()
        self._migrate_email_delivery_columns()
        self._create_write_lease_table()
        self._create_sync_outbox_table()
        self._ensure_default_institution()

    def _connect(self):
        """Verbindung zur Datenbank herstellen und SQLite für maximale Performance (WAL) konfigurieren"""
        try:
            # Hauptverbindung mit erhöhtem Timeout
            self.conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.cur = self.conn.cursor()

            # Journal-Modus auf WAL setzen für drastisch verbesserte Performance (gleichzeitiges Lesen/Schreiben)
            try:
                result = self.cur.execute("PRAGMA journal_mode=WAL").fetchone()
                print(f"Journal-Mode: {result[0]}")

                # Performance-Optimierungen
                self.cur.execute("PRAGMA synchronous=NORMAL")  # Sicherer aber tausendfach schneller als FULL bei WAL
                self.cur.execute("PRAGMA cache_size=-64000")   # ~64MB Cache (Wert ist negativ für KB)
                self.cur.execute("PRAGMA mmap_size=268435456") # 256MB Memory-Mapping für extrem schnelles Lesen
                self.cur.execute("PRAGMA temp_store=MEMORY")   # Temporäre Indizes/Suchen im RAM statt auf SSD

            except sqlite3.OperationalError as e:
                print(f"⚠ Performance PRAGMA Warnung: {e} - überspringe")

            # Foreign Keys aktivieren
            self.cur.execute("PRAGMA foreign_keys=ON")

        except sqlite3.Error as e:
            raise Exception(f"Datenbankverbindung fehlgeschlagen: {e}")

    def _create_schema(self):
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS depots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                adresse TEXT,
                telefon TEXT,
                email TEXT,
                institution_id INTEGER
            )
        """)
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS institutions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                adresse TEXT,
                latitude REAL,
                longitude REAL
            )
        """)
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS user_depot_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                depot_id INTEGER NOT NULL,
                can_read INTEGER NOT NULL DEFAULT 0,
                can_write INTEGER NOT NULL DEFAULT 0,
                UNIQUE(username, depot_id),
                FOREIGN KEY(depot_id) REFERENCES depots(id)
            )
        """)

        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS kontakte (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                depot_id INTEGER,
                name TEXT,
                rolle TEXT,
                telefon TEXT,
                email TEXT,
                FOREIGN KEY(depot_id) REFERENCES depots(id)
            )
        """)

        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS praeparate (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                wirkstoff TEXT,
                darreichungsform TEXT,
                staerke TEXT,
                einheit TEXT,
                pzn TEXT,
                hersteller TEXT
            )
        """)

        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS depot_praeparate (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                depot_id INTEGER,
                praeparat_id INTEGER,
                sollbestand INTEGER DEFAULT 0,
                FOREIGN KEY(depot_id) REFERENCES depots(id),
                FOREIGN KEY(praeparat_id) REFERENCES praeparate(id)
            )
        """)

        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS bewegungen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                depot_id INTEGER,
                praeparat_id INTEGER,
                charge TEXT,
                verfall TEXT,
                eingang_datum TEXT,
                ausgang_datum TEXT,
                empfaenger TEXT,
                anzahl INTEGER,
                typ TEXT CHECK(typ IN ('Zugang','Abgang','Vernichtung')),
                FOREIGN KEY(depot_id) REFERENCES depots(id),
                FOREIGN KEY(praeparat_id) REFERENCES praeparate(id)
            )
        """)
        self.conn.commit()

        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS meldungs_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                depot_id INTEGER,
                jahr INTEGER,
                bewegungen_erhalten INTEGER DEFAULT 0,
                bestand_erhalten INTEGER DEFAULT 0,
                notizen TEXT,
                FOREIGN KEY(depot_id) REFERENCES depots(id)
            )
        """)
        self.conn.commit()

        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS einstellungen (
                schluessel TEXT PRIMARY KEY,
                wert TEXT
            )
        """)
        self.conn.commit()

        # Analytics Saved Views (Issue #42 Phase 2)
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS analytics_saved_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                filter_json TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        self.conn.commit()

        # Analytics Saved Queries (Issue #42 Phase 4 — Custom SQL)
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS analytics_saved_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                sql_text TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                last_run TEXT
            )
        """)
        self.conn.commit()

        # Analytics Email-Schedule (Issue #42 Phase 4 — Email-Schedule)
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS analytics_email_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                report_type TEXT NOT NULL DEFAULT 'pdf',
                recipients TEXT NOT NULL,
                schedule TEXT NOT NULL DEFAULT 'weekly',
                last_sent TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        self.conn.commit()

        # Indizes für Performance (Phase 2 Optimierung)
        self.cur.execute("CREATE INDEX IF NOT EXISTS idx_bewegungen_depot ON bewegungen(depot_id)")
        self.cur.execute("CREATE INDEX IF NOT EXISTS idx_bewegungen_praeparat ON bewegungen(praeparat_id)")
        self.cur.execute("CREATE INDEX IF NOT EXISTS idx_bewegungen_datum ON bewegungen(eingang_datum, ausgang_datum)")
        self.conn.commit()

    def _migrate_depots_institution_column(self):
        depots_columns = [r[1] for r in self.cur.execute("PRAGMA table_info(depots)").fetchall()]
        needs_column = "institution_id" not in depots_columns
        if needs_column:
            self.cur.execute("ALTER TABLE depots ADD COLUMN institution_id INTEGER")
            self.conn.commit()

    def _migrate_address_split_columns(self):
        """Split-Adresse + Geo (Paritaet mit ndhub-web / Sync-Pull)."""
        inst_cols = [r[1] for r in self.cur.execute("PRAGMA table_info(institutions)").fetchall()]
        changed = False
        if "strasse" not in inst_cols:
            self.cur.execute("ALTER TABLE institutions ADD COLUMN strasse TEXT")
            changed = True
        if "hausnummer" not in inst_cols:
            self.cur.execute("ALTER TABLE institutions ADD COLUMN hausnummer TEXT")
            changed = True
        if "postleitzahl" not in inst_cols:
            self.cur.execute("ALTER TABLE institutions ADD COLUMN postleitzahl TEXT")
            changed = True
        if "stadt" not in inst_cols:
            self.cur.execute("ALTER TABLE institutions ADD COLUMN stadt TEXT")
            changed = True
        dep_cols = [r[1] for r in self.cur.execute("PRAGMA table_info(depots)").fetchall()]
        if "strasse" not in dep_cols:
            self.cur.execute("ALTER TABLE depots ADD COLUMN strasse TEXT")
            changed = True
        if "hausnummer" not in dep_cols:
            self.cur.execute("ALTER TABLE depots ADD COLUMN hausnummer TEXT")
            changed = True
        if "postleitzahl" not in dep_cols:
            self.cur.execute("ALTER TABLE depots ADD COLUMN postleitzahl TEXT")
            changed = True
        if "stadt" not in dep_cols:
            self.cur.execute("ALTER TABLE depots ADD COLUMN stadt TEXT")
            changed = True
        if "latitude" not in dep_cols:
            self.cur.execute("ALTER TABLE depots ADD COLUMN latitude REAL")
            changed = True
        if "longitude" not in dep_cols:
            self.cur.execute("ALTER TABLE depots ADD COLUMN longitude REAL")
            changed = True
        if changed:
            self.conn.commit()

    def _migrate_praeparate_extended_columns(self):
        cols = [r[1] for r in self.cur.execute("PRAGMA table_info(praeparate)").fetchall()]
        changed = False
        if "wirkstoff" not in cols:
            self.cur.execute("ALTER TABLE praeparate ADD COLUMN wirkstoff TEXT")
            changed = True
        if "darreichungsform" not in cols:
            self.cur.execute("ALTER TABLE praeparate ADD COLUMN darreichungsform TEXT")
            changed = True
        if "staerke" not in cols:
            self.cur.execute("ALTER TABLE praeparate ADD COLUMN staerke TEXT")
            changed = True
        if "einheit" not in cols:
            self.cur.execute("ALTER TABLE praeparate ADD COLUMN einheit TEXT")
            changed = True
        if "pzn" not in cols:
            self.cur.execute("ALTER TABLE praeparate ADD COLUMN pzn TEXT")
            changed = True
        if "hersteller" not in cols:
            self.cur.execute("ALTER TABLE praeparate ADD COLUMN hersteller TEXT")
            changed = True
        if changed:
            self.conn.commit()

    def _add_attachment_column(self):
        try:
            self.cur.execute("ALTER TABLE bewegungen ADD COLUMN datei_pfad TEXT")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass

    def _create_email_table(self):
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS email_verlauf (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                datum TEXT,
                betreff TEXT,
                nachricht TEXT,
                empfaenger_depots TEXT,
                empfaenger_emails TEXT,
                anzahl_empfaenger INTEGER,
                send_now INTEGER DEFAULT 0,
                delivery_status TEXT DEFAULT 'draft',
                delivery_channel TEXT DEFAULT 'outlook',
                delivery_error TEXT
            )
        """)
        self.conn.commit()

    def _migrate_email_delivery_columns(self):
        cols = [r[1] for r in self.cur.execute("PRAGMA table_info(email_verlauf)").fetchall()]
        if "send_now" not in cols:
            self.cur.execute("ALTER TABLE email_verlauf ADD COLUMN send_now INTEGER DEFAULT 0")
        if "delivery_status" not in cols:
            self.cur.execute("ALTER TABLE email_verlauf ADD COLUMN delivery_status TEXT DEFAULT 'draft'")
        if "delivery_channel" not in cols:
            self.cur.execute("ALTER TABLE email_verlauf ADD COLUMN delivery_channel TEXT DEFAULT 'outlook'")
        if "delivery_error" not in cols:
            self.cur.execute("ALTER TABLE email_verlauf ADD COLUMN delivery_error TEXT")
        self.conn.commit()

    def _create_write_lease_table(self):
        """Erstellt Tabelle für exklusiven Schreib-Lease (ein Writer, viele Reader)."""
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS app_write_lease (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                session_id TEXT,
                username TEXT,
                acquired_at TEXT,
                heartbeat_at TEXT
            )
        """)
        self.conn.commit()

    def _create_sync_outbox_table(self):
        """Puffer fuer lokale Aenderungen, die spaeter per API synchronisiert werden."""
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS sync_outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_name TEXT NOT NULL,
                operation TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                dedupe_key TEXT,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                retry_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT
            )
        """)
        self.cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_sync_outbox_status_created "
            "ON sync_outbox(status, created_at, id)"
        )
        self.cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_sync_outbox_dedupe "
            "ON sync_outbox(dedupe_key) WHERE dedupe_key IS NOT NULL"
        )
        self.conn.commit()

    def _ensure_default_institution(self):
        row = self.cur.execute("SELECT id FROM institutions ORDER BY id ASC LIMIT 1").fetchone()
        if row is None:
            self.cur.execute(
                "INSERT INTO institutions (name, adresse, latitude, longitude) VALUES (?, ?, ?, ?)",
                ("Standard-Institution", None, None, None),
            )
            default_id = int(self.cur.lastrowid)
        else:
            default_id = int(row[0])
        self.cur.execute("UPDATE depots SET institution_id = ? WHERE institution_id IS NULL", (default_id,))
        self.conn.commit()


    def set_query_only(self, enabled: bool):
        """Schaltet SQLite in nur-Lesen Modus für diese Verbindung."""
        if enabled:
            self.cur.execute("PRAGMA query_only=ON")
        else:
            self.cur.execute("PRAGMA query_only=OFF")
        self.conn.commit()

    def is_read_only_mode(self) -> bool:
        return not self.write_lease_owner


    def _clear_lookup_caches(self):
        """Leert alle TTL-Caches, die von Stammdaten-Abfragen abhängen."""
        clear_all_caches(self)


    # ─────────────────────────────────────────────────────────────────────
    # Email-Schedule CRUD (Issue #42 Phase 4 — Email-Schedule)
    # ─────────────────────────────────────────────────────────────────────


    # In der Database-Klasse:


# =============================================================================
# Helper Functions
# =============================================================================

def to_iso(date: QDate | None) -> str | None:
    if not date or not date.isValid():
        return None
    return f"{date.year():04d}-{date.month():02d}-{date.day():02d}"

def fill_table(table: QtWidgets.QTableWidget, data):
    table.clear()
    header = data[0]
    rows = data[1:]
    table.setColumnCount(len(header))
    table.setRowCount(len(rows))
    table.setHorizontalHeaderLabels(header)
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            item = QtWidgets.QTableWidgetItem(str(val) if val is not None else "")
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            table.setItem(r, c, item)
    table.resizeColumnsToContents()
    table.horizontalHeader().setStretchLastSection(True)

