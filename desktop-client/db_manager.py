"""Database-Layer für die ND-Hub Desktop-Anwendung.

.. note::
   Dieses Modul verwendet ``functools.lru_cache`` an mehreren Stellen für
   Lookup-Methoden (siehe Issue #11). Die Methode ist auf **Instanzen**
   der ``Database``-Klasse angewendet, was zwei bekannte Risiken hat:

   1. **Memory-Leak pro Instanz**: ``self`` ist Teil des Cache-Keys,
      daher hält jede ``Database``-Instanz ihren eigenen Cache. Bei
      vielen kurzlebigen Instanzen sammelt sich Cache bis zum GC.
      Mitigation: ``Database`` wird als Singleton verwendet (siehe
      ``nd_hub.py`` → ``self.db = Database(db_path)``).
   2. **Stale Cache bei DB-Mutationen**: ``lru_cache`` invalidiert nicht
      automatisch bei ``UPDATE``/``INSERT``/``DELETE``. Die
      ``_clear_lookup_caches()``-Methode ist die zentrale Anlaufstelle
      nach Mutationen — sie MUSS nach jedem schreibenden Query aufgerufen
      werden. Bekannte Aufrufer sind in dieser Datei mit
      ``self._clear_lookup_caches()`` markiert.

   Für den Wechsel auf ``cachetools.TTLCache`` (TTL-basiertes Caching)
   siehe Issue #17 — bewusst aufgeschoben, weil lru_cache für den
   Single-User-Desktop gut funktioniert und die Risiken durch das
   Singleton-Pattern mitigiert sind.
"""
import json
import os
import shutil
import smtplib
import sqlite3
import time
import uuid
from datetime import datetime
from email.message import EmailMessage
from functools import lru_cache
from typing import Any

from PySide6 import QtWidgets
from PySide6.QtCore import QDate, Qt


def _sync_payload_str(data: dict[str, Any], key: str) -> Any:
    v = data.get(key)
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _sync_payload_float(data: dict[str, Any], key: str) -> Any:
    v = data.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _coerce_opt_float(v: Any) -> Any:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


_MISSING = object()


class DB:
    TABLE_DEPOTS = "depots"
    TABLE_KONTAKTE = "kontakte"
    TABLE_PRAEPARATE = "praeparate"
    TABLE_DEPOT_PRAEPARATE = "depot_praeparate"
    TABLE_BEWEGUNGEN = "bewegungen"
    TABLE_EMAIL_VERLAUF = "email_verlauf"
    TABLE_EINSTELLUNGEN = "einstellungen"
    TABLE_TRACKING = "meldungs_tracking"
    TYP_ZUGANG = "Zugang"
    TYP_ABGANG = "Abgang"
    TYP_VERNICHTUNG = "Vernichtung"
    SETTING_AUTO_BACKUP = "auto_backup"
    SETTING_LETZTES_BACKUP = "letztes_backup"
    SETTING_PASSWORD_HASH = "password_hash"  # gitleaks:allow nosec B105: settings KEY name, not a secret
    SETTING_MAX_BACKUPS = "max_backups"
    SETTING_SMTP_HOST = "smtp_host"
    SETTING_SMTP_PORT = "smtp_port"
    SETTING_SMTP_USERNAME = "smtp_username"
    SETTING_SMTP_PASSWORD = "smtp_password"  # gitleaks:allow nosec B105: settings KEY name, not a secret
    SETTING_SMTP_USE_TLS = "smtp_use_tls"
    SETTING_SMTP_USE_SSL = "smtp_use_ssl"
    SETTING_SMTP_FROM_ADDRESS = "smtp_from_address"
    SETTING_SMTP_FROM_NAME = "smtp_from_name"
    SETTING_SETUP_WIZARD_COMPLETED = "setup_wizard_completed"
    SETTING_SETUP_WIZARD_LAST_STEP = "setup_wizard_last_step"
    SETTING_SETUP_WIZARD_DRAFT = "setup_wizard_draft"


class Database:
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
        for col, sql_type in (
            ("strasse", "TEXT"),
            ("hausnummer", "TEXT"),
            ("postleitzahl", "TEXT"),
            ("stadt", "TEXT"),
        ):
            if col not in inst_cols:
                self.cur.execute(f"ALTER TABLE institutions ADD COLUMN {col} {sql_type}")
                changed = True
        dep_cols = [r[1] for r in self.cur.execute("PRAGMA table_info(depots)").fetchall()]
        for col, sql_type in (
            ("strasse", "TEXT"),
            ("hausnummer", "TEXT"),
            ("postleitzahl", "TEXT"),
            ("stadt", "TEXT"),
            ("latitude", "REAL"),
            ("longitude", "REAL"),
        ):
            if col not in dep_cols:
                self.cur.execute(f"ALTER TABLE depots ADD COLUMN {col} {sql_type}")
                changed = True
        if changed:
            self.conn.commit()

    def _migrate_praeparate_extended_columns(self):
        cols = [r[1] for r in self.cur.execute("PRAGMA table_info(praeparate)").fetchall()]
        additions = {
            "wirkstoff": "TEXT",
            "darreichungsform": "TEXT",
            "staerke": "TEXT",
            "einheit": "TEXT",
            "pzn": "TEXT",
            "hersteller": "TEXT",
        }
        changed = False
        for name, sql_type in additions.items():
            if name not in cols:
                self.cur.execute(f"ALTER TABLE praeparate ADD COLUMN {name} {sql_type}")
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

    def record_sync_outbox(self, entity_name: str, operation: str, payload: dict[str, Any], dedupe_key: str = None) -> int:
        """Speichert eine lokale Aenderung fuer den spaeteren Sync."""
        payload_json = json.dumps(payload or {}, ensure_ascii=False)
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cur.execute(
            """
            INSERT OR IGNORE INTO sync_outbox (entity_name, operation, payload_json, dedupe_key, created_at, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
            """,
            (entity_name, operation, payload_json, dedupe_key, now_ts),
        )
        self.conn.commit()

        if self.cur.lastrowid:
            return int(self.cur.lastrowid)

        if dedupe_key:
            row = self.cur.execute(
                "SELECT id FROM sync_outbox WHERE dedupe_key = ?",
                (dedupe_key,),
            ).fetchone()
            if row:
                return int(row["id"])
        return 0

    def enqueue_sync_change(self, entity_name: str, operation: str, payload: dict[str, Any], dedupe_key: str = None) -> int:
        """Erzeugt einen eindeutigen Outbox-Eintrag fuer spaeteren Sync."""
        if not dedupe_key:
            dedupe_key = f"{entity_name}:{operation}:{int(time.time() * 1000)}:{uuid.uuid4().hex[:8]}"
        return self.record_sync_outbox(
            entity_name=entity_name,
            operation=operation,
            payload=payload,
            dedupe_key=dedupe_key,
        )

    def list_pending_sync_outbox(self, limit: int = 200) -> list[dict[str, Any]]:
        """Liefert ausstehende Outbox-Eintraege fuer Push-Runs."""
        safe_limit = max(1, min(int(limit or 200), 2000))
        rows = self.cur.execute(
            """
            SELECT id, entity_name, operation, payload_json, dedupe_key, created_at, status, retry_count
            FROM sync_outbox
            WHERE status IN ('pending', 'retry')
            ORDER BY created_at ASC, id ASC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
        result = []
        for row in rows:
            payload = {}
            try:
                payload = json.loads(row["payload_json"] or "{}")
            except json.JSONDecodeError:
                payload = {}
            result.append(
                {
                    "id": int(row["id"]),
                    "entity_name": row["entity_name"],
                    "operation": row["operation"],
                    "payload": payload,
                    "dedupe_key": row["dedupe_key"],
                    "created_at": row["created_at"],
                    "status": row["status"],
                    "retry_count": int(row["retry_count"] or 0),
                }
            )
        return result

    def get_sync_outbox_stats(self) -> dict[str, Any]:
        """Liefert aggregierte Outbox-Statistiken fuer Monitoring/Support."""
        status_rows = self.cur.execute(
            """
            SELECT status, COUNT(*) AS cnt
            FROM sync_outbox
            GROUP BY status
            """
        ).fetchall()
        counts = {str(row["status"]): int(row["cnt"] or 0) for row in status_rows}
        oldest_pending_row = self.cur.execute(
            """
            SELECT created_at
            FROM sync_outbox
            WHERE status IN ('pending', 'retry')
            ORDER BY created_at ASC, id ASC
            LIMIT 1
            """
        ).fetchone()
        latest_done_row = self.cur.execute(
            """
            SELECT created_at
            FROM sync_outbox
            WHERE status = 'done'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        latest_error_row = self.cur.execute(
            """
            SELECT status, last_error, created_at
            FROM sync_outbox
            WHERE COALESCE(last_error, '') <> ''
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        return {
            "counts": {
                "pending": int(counts.get("pending", 0)),
                "retry": int(counts.get("retry", 0)),
                "conflict": int(counts.get("conflict", 0)),
                "done": int(counts.get("done", 0)),
                "total": int(sum(counts.values())),
            },
            "oldest_pending_at": str(oldest_pending_row["created_at"]) if oldest_pending_row else None,
            "latest_success_at": str(latest_done_row["created_at"]) if latest_done_row else None,
            "latest_error": (
                {
                    "status": str(latest_error_row["status"]),
                    "message": str(latest_error_row["last_error"]),
                    "at": str(latest_error_row["created_at"]),
                }
                if latest_error_row
                else None
            ),
        }

    def mark_sync_outbox_done(self, outbox_id: int):
        self.cur.execute("UPDATE sync_outbox SET status = 'done', last_error = NULL WHERE id = ?", (outbox_id,))
        self.conn.commit()

    def remap_local_entity_id(self, entity_name: str, old_id: int, new_id: int) -> bool:
        """Remappt lokale IDs auf serverseitige IDs nach erfolgreichem Create-Push."""
        safe_entity = str(entity_name or "").strip().lower()
        old_val = int(old_id or 0)
        new_val = int(new_id or 0)
        if old_val <= 0 or new_val <= 0 or old_val == new_val:
            return False
        try:
            self.cur.execute("BEGIN")
            if safe_entity == "depots":
                conflict = self.cur.execute("SELECT id FROM depots WHERE id = ?", (new_val,)).fetchone()
                if conflict is not None:
                    self.cur.execute("ROLLBACK")
                    return False
                self.cur.execute("UPDATE depots SET id = ? WHERE id = ?", (new_val, old_val))
                if self.cur.rowcount <= 0:
                    self.cur.execute("ROLLBACK")
                    return False
                self.cur.execute("UPDATE kontakte SET depot_id = ? WHERE depot_id = ?", (new_val, old_val))
                self.cur.execute("UPDATE bewegungen SET depot_id = ? WHERE depot_id = ?", (new_val, old_val))
                self.cur.execute("UPDATE depot_praeparate SET depot_id = ? WHERE depot_id = ?", (new_val, old_val))
                self.cur.execute("UPDATE user_depot_permissions SET depot_id = ? WHERE depot_id = ?", (new_val, old_val))
            elif safe_entity == "praeparate":
                conflict = self.cur.execute("SELECT id FROM praeparate WHERE id = ?", (new_val,)).fetchone()
                if conflict is not None:
                    self.cur.execute("ROLLBACK")
                    return False
                self.cur.execute("UPDATE praeparate SET id = ? WHERE id = ?", (new_val, old_val))
                if self.cur.rowcount <= 0:
                    self.cur.execute("ROLLBACK")
                    return False
                self.cur.execute("UPDATE bewegungen SET praeparat_id = ? WHERE praeparat_id = ?", (new_val, old_val))
                self.cur.execute(
                    "UPDATE depot_praeparate SET praeparat_id = ? WHERE praeparat_id = ?",
                    (new_val, old_val),
                )
            elif safe_entity == "kontakte":
                conflict = self.cur.execute("SELECT id FROM kontakte WHERE id = ?", (new_val,)).fetchone()
                if conflict is not None:
                    self.cur.execute("ROLLBACK")
                    return False
                self.cur.execute("UPDATE kontakte SET id = ? WHERE id = ?", (new_val, old_val))
                if self.cur.rowcount <= 0:
                    self.cur.execute("ROLLBACK")
                    return False
            elif safe_entity == "institutions":
                conflict = self.cur.execute("SELECT id FROM institutions WHERE id = ?", (new_val,)).fetchone()
                if conflict is not None:
                    self.cur.execute("ROLLBACK")
                    return False
                self.cur.execute("UPDATE institutions SET id = ? WHERE id = ?", (new_val, old_val))
                if self.cur.rowcount <= 0:
                    self.cur.execute("ROLLBACK")
                    return False
                self.cur.execute("UPDATE depots SET institution_id = ? WHERE institution_id = ?", (new_val, old_val))
            else:
                self.cur.execute("ROLLBACK")
                return False
            self.cur.execute("COMMIT")
            self._clear_lookup_caches()
            return True
        except Exception:
            try:
                self.cur.execute("ROLLBACK")
            except Exception:
                logger.warning("Rollback after ID-Remap failure failed", exc_info=True)
            logger.exception(
                "ID-Remap fehlgeschlagen: entity=%s old=%s new=%s",
                safe_entity,
                old_val,
                new_val,
            )
            return False

    def mark_sync_outbox_retry(self, outbox_id: int, error_message: str):
        self.cur.execute(
            """
            UPDATE sync_outbox
            SET status = 'retry',
                retry_count = retry_count + 1,
                last_error = ?
            WHERE id = ?
            """,
            (error_message[:1000], outbox_id),
        )
        self.conn.commit()

    def mark_sync_outbox_conflict(self, outbox_id: int, error_message: str):
        self.cur.execute(
            """
            UPDATE sync_outbox
            SET status = 'conflict',
                last_error = ?
            WHERE id = ?
            """,
            (error_message[:1000], outbox_id),
        )
        self.conn.commit()

    def requeue_sync_outbox_conflicts(self, limit: int = 100) -> int:
        """Setzt Konflikt-Eintraege wieder auf retry, z.B. nach manueller Korrektur."""
        safe_limit = max(1, min(int(limit or 100), 1000))
        rows = self.cur.execute(
            """
            SELECT id
            FROM sync_outbox
            WHERE status = 'conflict'
            ORDER BY id ASC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
        ids = [int(row["id"]) for row in rows]
        for outbox_id in ids:
            self.cur.execute(
                """
                UPDATE sync_outbox
                SET status = 'retry',
                    last_error = NULL
                WHERE id = ?
                """,
                (outbox_id,),
            )
        self.conn.commit()
        return len(ids)

    def apply_remote_sync_change(self, entity_name: str, operation: str, payload: dict[str, Any]) -> bool:
        """Wendet vom Server gepullte Aenderungen lokal an (ohne Outbox-Queueing)."""
        entity = (entity_name or "").strip().lower()
        op = (operation or "").strip().lower()
        data = dict(payload or {})

        if entity == "depots":
            depot_id = int(data.get("id") or 0)
            if op == "delete":
                if depot_id > 0:
                    self.cur.execute("DELETE FROM depots WHERE id = ?", (depot_id,))
                    self.conn.commit()
                    self._clear_lookup_caches()
                return True
            if depot_id <= 0:
                return False
            existing = self.cur.execute("SELECT id FROM depots WHERE id = ?", (depot_id,)).fetchone()
            values = (
                str(data.get("name") or ""),
                data.get("adresse"),
                _sync_payload_str(data, "strasse"),
                _sync_payload_str(data, "hausnummer"),
                _sync_payload_str(data, "postleitzahl"),
                _sync_payload_str(data, "stadt"),
                data.get("telefon"),
                data.get("email"),
                int(data.get("institution_id")) if data.get("institution_id") is not None else None,
                _sync_payload_float(data, "latitude"),
                _sync_payload_float(data, "longitude"),
                depot_id,
            )
            if existing:
                self.cur.execute(
                    """
                    UPDATE depots SET name = ?, adresse = ?, strasse = ?, hausnummer = ?, postleitzahl = ?, stadt = ?,
                        telefon = ?, email = ?, institution_id = ?, latitude = ?, longitude = ?
                    WHERE id = ?
                    """,
                    values,
                )
            else:
                self.cur.execute(
                    """
                    INSERT INTO depots (
                        name, adresse, strasse, hausnummer, postleitzahl, stadt, telefon, email, institution_id,
                        latitude, longitude, id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            self.conn.commit()
            self._clear_lookup_caches()
            return True

        if entity == "institutions":
            institution_id = int(data.get("id") or 0)
            if op == "delete":
                if institution_id > 0:
                    self.cur.execute("DELETE FROM institutions WHERE id = ?", (institution_id,))
                    self.conn.commit()
                    self._clear_lookup_caches()
                return True
            if institution_id <= 0:
                return False
            existing = self.cur.execute("SELECT id FROM institutions WHERE id = ?", (institution_id,)).fetchone()
            values = (
                str(data.get("name") or ""),
                data.get("adresse"),
                _sync_payload_str(data, "strasse"),
                _sync_payload_str(data, "hausnummer"),
                _sync_payload_str(data, "postleitzahl"),
                _sync_payload_str(data, "stadt"),
                _sync_payload_float(data, "latitude"),
                _sync_payload_float(data, "longitude"),
                institution_id,
            )
            if existing:
                self.cur.execute(
                    """
                    UPDATE institutions SET name = ?, adresse = ?, strasse = ?, hausnummer = ?, postleitzahl = ?, stadt = ?,
                        latitude = ?, longitude = ?
                    WHERE id = ?
                    """,
                    values,
                )
            else:
                self.cur.execute(
                    """
                    INSERT INTO institutions (
                        name, adresse, strasse, hausnummer, postleitzahl, stadt, latitude, longitude, id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            self.conn.commit()
            self._clear_lookup_caches()
            return True

        if entity == "praeparate":
            prae_id = int(data.get("id") or 0)
            if op == "delete":
                if prae_id > 0:
                    self.cur.execute("DELETE FROM praeparate WHERE id = ?", (prae_id,))
                    self.conn.commit()
                    self._clear_lookup_caches()
                return True
            if prae_id <= 0:
                return False
            existing = self.cur.execute("SELECT id FROM praeparate WHERE id = ?", (prae_id,)).fetchone()
            values = (
                str(data.get("name") or ""),
                data.get("wirkstoff"),
                data.get("darreichungsform"),
                data.get("staerke"),
                data.get("einheit"),
                data.get("pzn"),
                data.get("hersteller"),
                prae_id,
            )
            if existing:
                self.cur.execute(
                    """
                    UPDATE praeparate
                    SET name = ?, wirkstoff = ?, darreichungsform = ?, staerke = ?, einheit = ?, pzn = ?, hersteller = ?
                    WHERE id = ?
                    """,
                    values,
                )
            else:
                self.cur.execute(
                    """
                    INSERT INTO praeparate (name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller, id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            self.conn.commit()
            self._clear_lookup_caches()
            return True

        if entity == "kontakte":
            kontakt_id = int(data.get("id") or 0)
            if op == "delete":
                if kontakt_id > 0:
                    self.cur.execute("DELETE FROM kontakte WHERE id = ?", (kontakt_id,))
                    self.conn.commit()
                return True
            if kontakt_id <= 0:
                return False
            depot_id = int(data.get("depot_id") or 0)
            existing = self.cur.execute("SELECT id FROM kontakte WHERE id = ?", (kontakt_id,)).fetchone()
            values = (
                depot_id,
                str(data.get("name") or ""),
                data.get("rolle"),
                data.get("telefon"),
                data.get("email"),
                kontakt_id,
            )
            if existing:
                self.cur.execute(
                    "UPDATE kontakte SET depot_id = ?, name = ?, rolle = ?, telefon = ?, email = ? WHERE id = ?",
                    values,
                )
            else:
                self.cur.execute(
                    "INSERT INTO kontakte (depot_id, name, rolle, telefon, email, id) VALUES (?, ?, ?, ?, ?, ?)",
                    values,
                )
            self.conn.commit()
            return True

        if entity == "bewegungen":
            bewegung_id = int(data.get("id") or 0)
            if op == "delete":
                if bewegung_id > 0:
                    self.cur.execute("DELETE FROM bewegungen WHERE id = ?", (bewegung_id,))
                    self.conn.commit()
                return True
            if bewegung_id <= 0:
                return False
            typ_raw = str(data.get("typ") or "").strip()
            typ = {
                "zugang": "Zugang",
                "abgang": "Abgang",
                "vernichtung": "Vernichtung",
            }.get(typ_raw.lower(), typ_raw)
            datum = data.get("datum")
            eingang = datum if typ == "Zugang" else None
            ausgang = datum if typ in {"Abgang", "Vernichtung"} else None

            depot_id = int(data.get("depot_id") or 0)
            praeparat_id = int(data.get("praeparat_id") or 0)
            depot_name = str(data.get("depot_name") or "").strip()
            praeparat_name = str(data.get("praeparat_name") or "").strip()

            if depot_name:
                mapped_depot = self.get_depot_id_by_name(depot_name)
                if mapped_depot:
                    depot_id = int(mapped_depot)
            elif depot_id > 0:
                depot_exists = self.cur.execute("SELECT id FROM depots WHERE id = ?", (depot_id,)).fetchone()
                if depot_exists is None:
                    depot_id = 0

            if praeparat_name:
                mapped_praeparat = self.get_praeparat_id_by_name(praeparat_name)
                if mapped_praeparat:
                    praeparat_id = int(mapped_praeparat)
            elif praeparat_id > 0:
                prae_exists = self.cur.execute("SELECT id FROM praeparate WHERE id = ?", (praeparat_id,)).fetchone()
                if prae_exists is None:
                    praeparat_id = 0

            if depot_id <= 0 or praeparat_id <= 0 or typ not in {"Zugang", "Abgang", "Vernichtung"}:
                return False

            existing = self.cur.execute("SELECT id FROM bewegungen WHERE id = ?", (bewegung_id,)).fetchone()
            values = (
                depot_id,
                praeparat_id,
                str(data.get("charge") or ""),
                str(data.get("verfall") or ""),
                eingang,
                ausgang,
                data.get("empfaenger"),
                int(data.get("anzahl") or 0),
                typ,
                bewegung_id,
            )
            if existing:
                self.cur.execute(
                    """
                    UPDATE bewegungen
                    SET depot_id = ?, praeparat_id = ?, charge = ?, verfall = ?, eingang_datum = ?, ausgang_datum = ?,
                        empfaenger = ?, anzahl = ?, typ = ?
                    WHERE id = ?
                    """,
                    values,
                )
            else:
                self.cur.execute(
                    """
                    INSERT INTO bewegungen (
                        depot_id, praeparat_id, charge, verfall, eingang_datum, ausgang_datum,
                        empfaenger, anzahl, typ, id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            self.conn.commit()
            return True

        if entity == "depot_praeparate":
            depot_id = int(data.get("depot_id") or 0)
            praeparat_id = int(data.get("praeparat_id") or 0)
            if op == "delete":
                if depot_id > 0 and praeparat_id > 0:
                    self.cur.execute(
                        "DELETE FROM depot_praeparate WHERE depot_id = ? AND praeparat_id = ?",
                        (depot_id, praeparat_id),
                    )
                else:
                    assignment_id = int(data.get("id") or 0)
                    if assignment_id <= 0:
                        return False
                    self.cur.execute("DELETE FROM depot_praeparate WHERE id = ?", (assignment_id,))
                self.conn.commit()
                return True
            if depot_id <= 0 or praeparat_id <= 0:
                return False
            sollbestand = max(0, int(data.get("sollbestand") or 0))
            existing = self.cur.execute(
                "SELECT id FROM depot_praeparate WHERE depot_id = ? AND praeparat_id = ?",
                (depot_id, praeparat_id),
            ).fetchone()
            if existing:
                self.cur.execute(
                    "UPDATE depot_praeparate SET sollbestand = ? WHERE depot_id = ? AND praeparat_id = ?",
                    (sollbestand, depot_id, praeparat_id),
                )
            else:
                self.cur.execute(
                    "INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand) VALUES (?, ?, ?)",
                    (depot_id, praeparat_id, sollbestand),
                )
            self.conn.commit()
            return True

        return False

    def set_query_only(self, enabled: bool):
        """Schaltet SQLite in nur-Lesen Modus für diese Verbindung."""
        self.cur.execute(f"PRAGMA query_only={'ON' if enabled else 'OFF'}")
        self.conn.commit()

    def is_read_only_mode(self) -> bool:
        return not self.write_lease_owner

    def acquire_write_lease(self, username: str, ttl_seconds: int = 30) -> bool:
        """
        Versucht exklusiven Schreib-Lease zu erwerben.
        Gibt True zurück wenn diese Session schreiben darf, sonst False (read-only).
        """
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            self.cur.execute("BEGIN IMMEDIATE")
            row = self.cur.execute(
                "SELECT session_id, heartbeat_at FROM app_write_lease WHERE id = 1"
            ).fetchone()
            if row is None:
                self.cur.execute(
                    """
                    INSERT INTO app_write_lease (id, session_id, username, acquired_at, heartbeat_at)
                    VALUES (1, ?, ?, ?, ?)
                    """,
                    (self.session_id, username, now_ts, now_ts),
                )
                self.conn.commit()
                self.write_lease_owner = True
                self.set_query_only(False)
                return True

            owner_session, heartbeat_at = row
            stale = False
            if heartbeat_at:
                try:
                    hb = datetime.strptime(heartbeat_at, "%Y-%m-%d %H:%M:%S")
                    stale = (datetime.now() - hb).total_seconds() > ttl_seconds
                except ValueError:
                    stale = True

            if owner_session == self.session_id or stale:
                self.cur.execute(
                    """
                    UPDATE app_write_lease
                    SET session_id = ?, username = ?, heartbeat_at = ?, acquired_at = COALESCE(acquired_at, ?)
                    WHERE id = 1
                    """,
                    (self.session_id, username, now_ts, now_ts),
                )
                self.conn.commit()
                self.write_lease_owner = True
                self.set_query_only(False)
                return True

            self.conn.rollback()
            self.write_lease_owner = False
            self.set_query_only(True)
            return False
        except sqlite3.Error:
            try:
                self.conn.rollback()
            except sqlite3.Error:
                pass
            self.write_lease_owner = False
            self.set_query_only(True)
            return False

    def refresh_write_lease(self, username: str, ttl_seconds: int = 30) -> bool:
        """
        Aktualisiert Heartbeat für aktuellen Lease.
        Rückgabe True wenn Lease noch gültig/erworben, False bei Fallback auf read-only.
        """
        if not self.write_lease_owner:
            return False
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            self.cur.execute(
                """
                UPDATE app_write_lease
                SET heartbeat_at = ?, username = ?
                WHERE id = 1 AND session_id = ?
                """,
                (now_ts, username, self.session_id),
            )
            self.conn.commit()
            if self.cur.rowcount == 0:
                self.write_lease_owner = False
                self.set_query_only(True)
                return False
            return True
        except sqlite3.Error:
            self.write_lease_owner = False
            self.set_query_only(True)
            return False

    def release_write_lease(self):
        """Gibt den Schreib-Lease dieser Session frei."""
        if not self.write_lease_owner:
            return
        try:
            self.cur.execute(
                "DELETE FROM app_write_lease WHERE id = 1 AND session_id = ?",
                (self.session_id,),
            )
            self.conn.commit()
        except sqlite3.Error:
            pass
        self.write_lease_owner = False

    def _clear_lookup_caches(self):
        """Leert Caches, die von Stammdaten-Abfragen abhängen."""
        cache_methods = [
            self.list_depots,
            self.list_praeparate,
            self.get_depot_name,
            self.get_all_depot_names,
            self.get_all_praeparate_names,
            self.get_depot_id_by_name,
            self.get_praeparat_id_by_name,
        ]
        for method in cache_methods:
            if hasattr(method, "cache_clear"):
                method.cache_clear()

    # ----- Depots -----
    @lru_cache(maxsize=64)
    def list_depots(self):
        return self.cur.execute(
            """
            SELECT id, name, adresse, strasse, hausnummer, postleitzahl, stadt, telefon, email, institution_id,
                   latitude, longitude
            FROM depots ORDER BY name
            """
        ).fetchall()

    def list_depots_for_scope(self, security_manager=None):
        """
        Depots fuer die aktuelle Sicht. Single-Tenant-Desktop: identisch zu list_depots.
        Hook fuer spaeteres Filtern nach Institution, wenn cross_institution_read fehlt.
        """
        if security_manager is not None and hasattr(
            security_manager, "can_view_cross_institution_masterdata"
        ):
            _ = security_manager.can_view_cross_institution_masterdata()
        return self.list_depots()

    def add_depot(
        self,
        name,
        adresse,
        telefon,
        email,
        institution_id=None,
        strasse=None,
        hausnummer=None,
        postleitzahl=None,
        stadt=None,
        latitude=None,
        longitude=None,
    ):
        s_str = str(strasse).strip() or None if strasse is not None else None
        s_hnr = str(hausnummer).strip() or None if hausnummer is not None else None
        s_plz = str(postleitzahl).strip() or None if postleitzahl is not None else None
        s_stadt = str(stadt).strip() or None if stadt is not None else None
        lat = _coerce_opt_float(latitude)
        lon = _coerce_opt_float(longitude)
        self.cur.execute(
            """
            INSERT INTO depots (
                name, adresse, telefon, email, institution_id, strasse, hausnummer, postleitzahl, stadt, latitude, longitude
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                name,
                adresse,
                telefon,
                email,
                institution_id,
                s_str,
                s_hnr,
                s_plz,
                s_stadt,
                lat,
                lon,
            ),
        )
        self.conn.commit()
        depot_id = self.cur.lastrowid
        self.enqueue_sync_change(
            entity_name="depots",
            operation="create",
            payload={
                "id": int(depot_id),
                "name": name,
                "adresse": adresse,
                "strasse": s_str,
                "hausnummer": s_hnr,
                "postleitzahl": s_plz,
                "stadt": s_stadt,
                "telefon": telefon,
                "email": email,
                "institution_id": institution_id,
                "latitude": lat,
                "longitude": lon,
            },
        )
        self._clear_lookup_caches()
        return depot_id

    def update_depot(
        self,
        depot_id,
        name,
        adresse,
        telefon,
        email,
        institution_id=None,
        strasse=_MISSING,
        hausnummer=_MISSING,
        postleitzahl=_MISSING,
        stadt=_MISSING,
        latitude=_MISSING,
        longitude=_MISSING,
    ):
        prev = self.cur.execute(
            "SELECT strasse, hausnummer, postleitzahl, stadt, latitude, longitude FROM depots WHERE id = ?",
            (depot_id,),
        ).fetchone()
        if not prev:
            return

        def _txt(new_val: Any, old: Any) -> Any:
            if new_val is _MISSING:
                return old
            if new_val is None:
                return None
            s = str(new_val).strip()
            return s or None

        def _flt(new_val: Any, old: Any) -> Any:
            if new_val is _MISSING:
                return old
            return _coerce_opt_float(new_val)

        s_str = _txt(strasse, prev[0])
        s_hnr = _txt(hausnummer, prev[1])
        s_plz = _txt(postleitzahl, prev[2])
        s_stadt = _txt(stadt, prev[3])
        lat = _flt(latitude, prev[4])
        lon = _flt(longitude, prev[5])
        self.cur.execute(
            """
            UPDATE depots SET name=?, adresse=?, telefon=?, email=?, institution_id=?,
                strasse=?, hausnummer=?, postleitzahl=?, stadt=?, latitude=?, longitude=?
            WHERE id=?
            """,
            (
                name,
                adresse,
                telefon,
                email,
                institution_id,
                s_str,
                s_hnr,
                s_plz,
                s_stadt,
                lat,
                lon,
                depot_id,
            ),
        )
        self.conn.commit()
        self.enqueue_sync_change(
            entity_name="depots",
            operation="update",
            payload={
                "id": int(depot_id),
                "name": name,
                "adresse": adresse,
                "strasse": s_str,
                "hausnummer": s_hnr,
                "postleitzahl": s_plz,
                "stadt": s_stadt,
                "telefon": telefon,
                "email": email,
                "institution_id": institution_id,
                "latitude": lat,
                "longitude": lon,
            },
        )
        self._clear_lookup_caches()

    def list_institutions(self):
        return self.cur.execute(
            """
            SELECT id, name, adresse, strasse, hausnummer, postleitzahl, stadt, latitude, longitude
            FROM institutions ORDER BY name
            """
        ).fetchall()

    def upsert_user_depot_permission(self, username: str, depot_id: int, can_read: bool, can_write: bool):
        self.cur.execute(
            """
            INSERT INTO user_depot_permissions (username, depot_id, can_read, can_write)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(username, depot_id) DO UPDATE SET
                can_read = excluded.can_read,
                can_write = excluded.can_write
            """,
            (username, int(depot_id), int(bool(can_read)), int(bool(can_write))),
        )
        self.conn.commit()

    def list_user_depot_permissions(self, username: str):
        return self.cur.execute(
            """
            SELECT depot_id, can_read, can_write
            FROM user_depot_permissions
            WHERE username = ?
            ORDER BY depot_id
            """,
            (username,),
        ).fetchall()

    def delete_depot(self, depot_id):
        self.cur.execute("DELETE FROM depots WHERE id=?", (depot_id,))
        self.conn.commit()
        self.enqueue_sync_change(
            entity_name="depots",
            operation="delete",
            payload={"id": int(depot_id)},
        )
        self._clear_lookup_caches()

    @lru_cache(maxsize=128)
    def get_depot_name(self, depot_id):
        row = self.cur.execute("SELECT name FROM depots WHERE id=?", (depot_id,)).fetchone()
        return row[0] if row else None

    @lru_cache(maxsize=256)
    def get_praeparat_name(self, praeparat_id):
        row = self.cur.execute("SELECT name FROM praeparate WHERE id=?", (praeparat_id,)).fetchone()
        return row[0] if row else None
    
    # ----- Präparate -----
    @lru_cache(maxsize=64)
    def list_praeparate(self):
        return self.cur.execute("SELECT id, name FROM praeparate ORDER BY name").fetchall()

    @lru_cache(maxsize=64)
    def list_praeparate_extended(self):
        return self.cur.execute(
            """
            SELECT id, name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller
            FROM praeparate
            ORDER BY name
            """
        ).fetchall()

    def add_praeparat(self, name):
        return self.add_praeparat_extended(
            name=name,
            wirkstoff="",
            darreichungsform="",
            staerke="",
            einheit="",
            pzn="",
            hersteller="",
        )

    def add_praeparat_extended(
        self,
        name: str,
        wirkstoff: str = "",
        darreichungsform: str = "",
        staerke: str = "",
        einheit: str = "",
        pzn: str = "",
        hersteller: str = "",
    ):
        self.cur.execute(
            """
            INSERT INTO praeparate
                (name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                (wirkstoff or "").strip() or None,
                (darreichungsform or "").strip() or None,
                (staerke or "").strip() or None,
                (einheit or "").strip() or None,
                (pzn or "").strip() or None,
                (hersteller or "").strip() or None,
            ),
        )
        self.conn.commit()
        prae_id = self.cur.lastrowid
        self.enqueue_sync_change(
            entity_name="praeparate",
            operation="create",
            payload={
                "id": int(prae_id),
                "name": name,
                "wirkstoff": (wirkstoff or "").strip() or None,
                "darreichungsform": (darreichungsform or "").strip() or None,
                "staerke": (staerke or "").strip() or None,
                "einheit": (einheit or "").strip() or None,
                "pzn": (pzn or "").strip() or None,
                "hersteller": (hersteller or "").strip() or None,
            },
        )
        self._clear_lookup_caches()
        return prae_id

    def update_praeparat(self, prae_id, name):
        self.update_praeparat_extended(
            prae_id=prae_id,
            name=name,
            wirkstoff="",
            darreichungsform="",
            staerke="",
            einheit="",
            pzn="",
            hersteller="",
        )

    def update_praeparat_extended(
        self,
        prae_id: int,
        name: str,
        wirkstoff: str = "",
        darreichungsform: str = "",
        staerke: str = "",
        einheit: str = "",
        pzn: str = "",
        hersteller: str = "",
    ):
        self.cur.execute(
            """
            UPDATE praeparate
            SET name=?, wirkstoff=?, darreichungsform=?, staerke=?, einheit=?, pzn=?, hersteller=?
            WHERE id=?
            """,
            (
                name,
                (wirkstoff or "").strip() or None,
                (darreichungsform or "").strip() or None,
                (staerke or "").strip() or None,
                (einheit or "").strip() or None,
                (pzn or "").strip() or None,
                (hersteller or "").strip() or None,
                prae_id,
            ),
        )
        self.conn.commit()
        self.enqueue_sync_change(
            entity_name="praeparate",
            operation="update",
            payload={
                "id": int(prae_id),
                "name": name,
                "wirkstoff": (wirkstoff or "").strip() or None,
                "darreichungsform": (darreichungsform or "").strip() or None,
                "staerke": (staerke or "").strip() or None,
                "einheit": (einheit or "").strip() or None,
                "pzn": (pzn or "").strip() or None,
                "hersteller": (hersteller or "").strip() or None,
            },
        )
        self._clear_lookup_caches()

    def delete_praeparat(self, prae_id):
        self.cur.execute("DELETE FROM praeparate WHERE id=?", (prae_id,))
        self.conn.commit()
        self.enqueue_sync_change(
            entity_name="praeparate",
            operation="delete",
            payload={"id": int(prae_id)},
        )
        self._clear_lookup_caches()

    # ----- Zuordnung Depot ↔ Präparate mit Sollbestand -----
    def get_assigned_praeparate(self, depot_id):
        rows = self.cur.execute("SELECT praeparat_id FROM depot_praeparate WHERE depot_id=?", (depot_id,)).fetchall()
        return set(r[0] for r in rows)

    def get_depot_praeparat_assignments(self, depot_id):
        rows = self.cur.execute("""
            SELECT praeparat_id, sollbestand 
            FROM depot_praeparate 
            WHERE depot_id=?
        """, (depot_id,)).fetchall()
        return {r[0]: r[1] if r[1] is not None else 0 for r in rows}

    def set_assigned_praeparate_with_sollbestand(self, depot_id, praeparat_sollbestand_dict):
        before_rows = self.cur.execute(
            "SELECT praeparat_id FROM depot_praeparate WHERE depot_id=?",
            (depot_id,),
        ).fetchall()
        before_ids = {int(r[0]) for r in before_rows}
        self.cur.execute("DELETE FROM depot_praeparate WHERE depot_id=?", (depot_id,))
        for pid, sollbestand in praeparat_sollbestand_dict.items():
            self.cur.execute("""
                INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand) 
                VALUES (?, ?, ?)
            """, (depot_id, pid, sollbestand))
        self.conn.commit()
        after_ids = {int(pid) for pid in praeparat_sollbestand_dict.keys()}
        deleted_ids = before_ids - after_ids
        for praeparat_id in deleted_ids:
            self.enqueue_sync_change(
                entity_name="depot_praeparate",
                operation="delete",
                payload={"depot_id": int(depot_id), "praeparat_id": int(praeparat_id)},
            )
        for pid, sollbestand in praeparat_sollbestand_dict.items():
            self.enqueue_sync_change(
                entity_name="depot_praeparate",
                operation="update",
                payload={
                    "depot_id": int(depot_id),
                    "praeparat_id": int(pid),
                    "sollbestand": int(sollbestand or 0),
                },
            )
        self._clear_lookup_caches()

    # ----- Ansprechpartner -----
    def list_kontakte(self, depot_id):
        return self.cur.execute("SELECT id, name, rolle, telefon, email FROM kontakte WHERE depot_id=? ORDER BY name", (depot_id,)).fetchall()

    def add_kontakt(self, depot_id, name, rolle, telefon, email):
        self.cur.execute("INSERT INTO kontakte (depot_id, name, rolle, telefon, email) VALUES (?,?,?,?,?)", 
                        (depot_id, name, rolle, telefon, email))
        self.conn.commit()
        kontakt_id = self.cur.lastrowid
        self.enqueue_sync_change(
            entity_name="kontakte",
            operation="create",
            payload={
                "id": int(kontakt_id),
                "depot_id": int(depot_id),
                "name": name,
                "rolle": rolle,
                "telefon": telefon,
                "email": email,
            },
        )
        return kontakt_id

    def update_kontakt(self, kontakt_id, name, rolle, telefon, email):
        self.cur.execute("UPDATE kontakte SET name=?, rolle=?, telefon=?, email=? WHERE id=?", 
                        (name, rolle, telefon, email, kontakt_id))
        self.conn.commit()
        self.enqueue_sync_change(
            entity_name="kontakte",
            operation="update",
            payload={
                "id": int(kontakt_id),
                "name": name,
                "rolle": rolle,
                "telefon": telefon,
                "email": email,
            },
        )

    def delete_kontakt(self, kontakt_id):
        self.cur.execute("DELETE FROM kontakte WHERE id=?", (kontakt_id,))
        self.conn.commit()
        self.enqueue_sync_change(
            entity_name="kontakte",
            operation="delete",
            payload={"id": int(kontakt_id)},
        )

    # ----- E-Mail-Funktionen -----
    def get_kontakte_by_depot_ids(self, depot_ids):
        if not depot_ids:
            return []
        
        # Scanner-Schutz (False Positive Prävention): Typisierung erzwingen
        safe_depot_ids = tuple(int(d) for d in depot_ids)
        placeholders = ','.join('?' * len(safe_depot_ids))
        # Placeholders are exclusively '?' generated from the count of
        # already-validated integer IDs; no user input reaches the SQL.
        sql = f"""
            SELECT k.id, k.name, k.rolle, k.email, d.name as depot_name, d.id as depot_id
            FROM kontakte k
            JOIN depots d ON d.id = k.depot_id
            WHERE k.depot_id IN ({placeholders})
              AND k.email IS NOT NULL
              AND k.email != ''
            ORDER BY d.name, k.name
        """  # nosec B608
        return self.cur.execute(sql, safe_depot_ids).fetchall()

    def add_email_verlauf(
        self,
        betreff,
        nachricht,
        depot_names,
        emails,
        anzahl,
        send_now=False,
        delivery_status="draft",
        delivery_channel="outlook",
        delivery_error=None,
    ):
        datum = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cur.execute("""
            INSERT INTO email_verlauf (
                datum, betreff, nachricht, empfaenger_depots, empfaenger_emails, anzahl_empfaenger,
                send_now, delivery_status, delivery_channel, delivery_error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datum,
            betreff,
            nachricht,
            depot_names,
            emails,
            anzahl,
            int(bool(send_now)),
            str(delivery_status or "draft"),
            str(delivery_channel or "outlook"),
            str(delivery_error) if delivery_error else None,
        ))
        self.conn.commit()
        return self.cur.lastrowid

    def get_email_verlauf(self, limit=50):
        return self.cur.execute("""
            SELECT id, datum, betreff, empfaenger_depots, anzahl_empfaenger, delivery_status
            FROM email_verlauf
            ORDER BY datum DESC
            LIMIT ?
        """, (limit,)).fetchall()

    def get_email_details(self, email_id):
        return self.cur.execute("""
            SELECT
                datum, betreff, nachricht, empfaenger_depots, empfaenger_emails, anzahl_empfaenger,
                send_now, delivery_status, delivery_channel, delivery_error
            FROM email_verlauf
            WHERE id = ?
        """, (email_id,)).fetchone()

    def update_email_verlauf_delivery(self, email_id: int, delivery_status: str, delivery_channel: str, delivery_error: str | None):
        self.cur.execute(
            """
            UPDATE email_verlauf
            SET delivery_status = ?, delivery_channel = ?, delivery_error = ?
            WHERE id = ?
            """,
            (str(delivery_status or "draft"), str(delivery_channel or "outlook"), delivery_error, int(email_id)),
        )
        self.conn.commit()

    def get_app_setting(self, key: str, default: str = "") -> str:
        try:
            row = self.cur.execute(
                "SELECT wert FROM einstellungen WHERE schluessel = ?",
                (key,),
            ).fetchone()
            if row is None or row[0] is None:
                return default
            return str(row[0])
        except sqlite3.Error:
            return default

    def set_app_setting(self, key: str, value: str):
        self.cur.execute(
            "INSERT OR REPLACE INTO einstellungen (schluessel, wert) VALUES (?, ?)",
            (key, str(value) if value is not None else ""),
        )
        self.conn.commit()

    def count_praeparate(self) -> int:
        row = self.cur.execute("SELECT COUNT(*) FROM praeparate").fetchone()
        return int(row[0]) if row else 0

    def count_depots(self) -> int:
        row = self.cur.execute("SELECT COUNT(*) FROM depots").fetchone()
        return int(row[0]) if row else 0

    def is_setup_wizard_completed(self) -> bool:
        raw = self.get_app_setting(DB.SETTING_SETUP_WIZARD_COMPLETED, "0").strip().lower()
        return raw in {"1", "true", "yes", "on"}

    def set_setup_wizard_completed(self, completed: bool) -> None:
        self.set_app_setting(DB.SETTING_SETUP_WIZARD_COMPLETED, "1" if completed else "0")

    def needs_setup_wizard(self) -> bool:
        """True, wenn Ersteinrichtung noch sinnvoll ist (keine Stammdaten oder Wizard nicht abgeschlossen)."""
        if self.is_setup_wizard_completed():
            return False
        return self.count_praeparate() == 0 or self.count_depots() == 0

    def apply_setup_wizard_draft(self, draft: dict[str, Any]) -> None:
        """
        Schreibt Institution, Präparate, Depots, depot_praeparate und einen Depot-Kontakt
        (Tabelle kontakte) in einer Transaktion. Outbox-Einträge erfolgen erst nach COMMIT.

        Voraussetzung: Es dürfen noch keine Depots existieren (sonst RuntimeError).
        Präparate werden bei Bedarf ergänzt (Namensabgleich case-insensitive).
        """
        if self.count_depots() > 0:
            raise RuntimeError("Es existieren bereits Notfalldepots. Einrichtungswizard kann nicht angewendet werden.")

        inst = draft.get("institution") if isinstance(draft.get("institution"), dict) else {}
        prs = draft.get("praeparate") if isinstance(draft.get("praeparate"), list) else []
        deps = draft.get("depots") if isinstance(draft.get("depots"), list) else []

        inst_name = str(inst.get("name") or "").strip()
        if not inst_name:
            raise RuntimeError("Institutionsname fehlt.")

        new_praeparat_ids: list[int] = []
        new_depot_ids: list[int] = []
        new_kontakt_ids: list[int] = []
        new_dp_keys: list[tuple[int, int, int]] = []

        try:
            self.cur.execute("BEGIN")
            row = self.cur.execute("SELECT id FROM institutions ORDER BY id ASC LIMIT 1").fetchone()
            if not row:
                raise RuntimeError("Keine Institution in der Datenbank.")
            inst_id = int(row[0])
            i_str = str(inst.get("strasse") or "").strip() or None
            i_hnr = str(inst.get("hausnummer") or "").strip() or None
            i_plz = str(inst.get("postleitzahl") or "").strip() or None
            i_stadt = str(inst.get("stadt") or "").strip() or None
            self.cur.execute(
                """
                UPDATE institutions
                SET name = ?, adresse = ?, strasse = ?, hausnummer = ?, postleitzahl = ?, stadt = ?,
                    latitude = ?, longitude = ?
                WHERE id = ?
                """,
                (
                    inst_name,
                    (str(inst.get("adresse") or "").strip() or None),
                    i_str,
                    i_hnr,
                    i_plz,
                    i_stadt,
                    _coerce_opt_float(inst.get("latitude")),
                    _coerce_opt_float(inst.get("longitude")),
                    inst_id,
                ),
            )

            name_to_id: dict[str, int] = {}
            for p in prs:
                if not isinstance(p, dict):
                    continue
                pname = str(p.get("name") or "").strip()
                if not pname:
                    continue
                key = pname.lower()
                ex = self.cur.execute(
                    "SELECT id FROM praeparate WHERE lower(name) = lower(?)",
                    (pname,),
                ).fetchone()
                if ex:
                    name_to_id[key] = int(ex[0])
                else:
                    self.cur.execute(
                        """
                        INSERT INTO praeparate
                            (name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            pname,
                            str(p.get("wirkstoff") or "").strip() or None,
                            str(p.get("darreichungsform") or "").strip() or None,
                            str(p.get("staerke") or "").strip() or None,
                            str(p.get("einheit") or "").strip() or None,
                            str(p.get("pzn") or "").strip() or None,
                            str(p.get("hersteller") or "").strip() or None,
                        ),
                    )
                    pid = int(self.cur.lastrowid)
                    name_to_id[key] = pid
                    new_praeparat_ids.append(pid)

            for d in deps:
                if not isinstance(d, dict):
                    continue
                d_name = str(d.get("name") or "").strip()
                contacts = d.get("contacts") if isinstance(d.get("contacts"), list) else []
                first_contact_email = ""
                first_contact_phone = ""
                if contacts:
                    first = contacts[0] if isinstance(contacts[0], dict) else {}
                    first_contact_email = str(first.get("email") or "").strip()
                    first_contact_phone = str(first.get("telefon") or "").strip()
                d_email = str(d.get("email") or "").strip() or first_contact_email
                if not d_name or not d_email:
                    raise RuntimeError("Jedes Notfalldepot braucht Name und mindestens einen Kontakt mit E-Mail.")
                d_adr = str(d.get("adresse") or "").strip() or None
                d_tel = str(d.get("telefon") or "").strip() or first_contact_phone or None
                d_str = str(d.get("strasse") or "").strip() or None
                d_hnr = str(d.get("hausnummer") or "").strip() or None
                d_plz = str(d.get("postleitzahl") or "").strip() or None
                d_stadt = str(d.get("stadt") or "").strip() or None
                d_lat = _coerce_opt_float(d.get("latitude"))
                d_lon = _coerce_opt_float(d.get("longitude"))
                self.cur.execute(
                    """
                    INSERT INTO depots (
                        name, adresse, telefon, email, institution_id,
                        strasse, hausnummer, postleitzahl, stadt, latitude, longitude
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        d_name,
                        d_adr,
                        d_tel,
                        d_email,
                        inst_id,
                        d_str,
                        d_hnr,
                        d_plz,
                        d_stadt,
                        d_lat,
                        d_lon,
                    ),
                )
                depot_id = int(self.cur.lastrowid)
                new_depot_ids.append(depot_id)

                if contacts:
                    for c in contacts:
                        if not isinstance(c, dict):
                            continue
                        cname = str(c.get("name") or "").strip() or d_name
                        crole = str(c.get("rolle") or "").strip() or "Depot"
                        ctel = str(c.get("telefon") or "").strip() or None
                        cemail = str(c.get("email") or "").strip()
                        if not cemail:
                            continue
                        self.cur.execute(
                            """
                            INSERT INTO kontakte (depot_id, name, rolle, telefon, email)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (depot_id, cname, crole, ctel, cemail),
                        )
                        new_kontakt_ids.append(int(self.cur.lastrowid))
                else:
                    kontakt_display = str(d.get("kontakt_name") or "").strip() or d_name
                    self.cur.execute(
                        """
                        INSERT INTO kontakte (depot_id, name, rolle, telefon, email)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (depot_id, kontakt_display, "Depot", d_tel, d_email),
                    )
                    new_kontakt_ids.append(int(self.cur.lastrowid))

                assignments = d.get("praeparat_assignments")
                rows_to_insert: list[tuple[str, int]] = []
                if isinstance(assignments, list) and assignments:
                    seen_a: set[str] = set()
                    for item in assignments:
                        if not isinstance(item, dict):
                            continue
                        pn = str(item.get("name") or "").strip()
                        if not pn:
                            continue
                        lk = pn.lower()
                        if lk in seen_a:
                            continue
                        seen_a.add(lk)
                        try:
                            soll = int(item.get("sollbestand") or 0)
                        except (TypeError, ValueError):
                            soll = 0
                        rows_to_insert.append((pn, max(0, soll)))
                else:
                    pnames = d.get("praeparat_names") if isinstance(d.get("praeparat_names"), list) else []
                    for raw in pnames:
                        pn = str(raw or "").strip()
                        if pn:
                            rows_to_insert.append((pn, 0))
                if not rows_to_insert:
                    raise RuntimeError(f"Notfalldepot '{d_name}': Bitte mindestens ein Präparat zuordnen.")
                for pn, soll in rows_to_insert:
                    lk = pn.lower()
                    pid = name_to_id.get(lk)
                    if pid is None:
                        raise RuntimeError(
                            f"Notfalldepot '{d_name}': Präparat '{pn}' ist nicht in der Wizard-Liste."
                        )
                    self.cur.execute(
                        """
                        INSERT INTO depot_praeparate (depot_id, praeparat_id, sollbestand)
                        VALUES (?, ?, ?)
                        """,
                        (depot_id, pid, soll),
                    )
                    new_dp_keys.append((depot_id, pid, soll))

            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

        self._clear_lookup_caches()

        inst_row = self.cur.execute(
            """
            SELECT id, name, adresse, strasse, hausnummer, postleitzahl, stadt, latitude, longitude
            FROM institutions WHERE id = ?
            """,
            (inst_id,),
        ).fetchone()
        if inst_row:
            self.enqueue_sync_change(
                "institutions",
                "update",
                {
                    "id": int(inst_row[0]),
                    "name": inst_row[1],
                    "adresse": inst_row[2],
                    "strasse": inst_row[3],
                    "hausnummer": inst_row[4],
                    "postleitzahl": inst_row[5],
                    "stadt": inst_row[6],
                    "latitude": inst_row[7],
                    "longitude": inst_row[8],
                },
                dedupe_key=f"wizard:institutions:update:{inst_id}",
            )

        for pid in new_praeparat_ids:
            nm_row = self.cur.execute(
                """
                SELECT name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller
                FROM praeparate WHERE id = ?
                """,
                (pid,),
            ).fetchone()
            nm = str(nm_row[0]) if nm_row else ""
            self.enqueue_sync_change(
                "praeparate",
                "create",
                {
                    "id": int(pid),
                    "name": nm,
                    "wirkstoff": nm_row[1] if nm_row else None,
                    "darreichungsform": nm_row[2] if nm_row else None,
                    "staerke": nm_row[3] if nm_row else None,
                    "einheit": nm_row[4] if nm_row else None,
                    "pzn": nm_row[5] if nm_row else None,
                    "hersteller": nm_row[6] if nm_row else None,
                },
                dedupe_key=f"wizard:praeparate:create:{pid}",
            )
        for did in new_depot_ids:
            r = self.cur.execute(
                """
                SELECT name, adresse, telefon, email, institution_id, strasse, hausnummer, postleitzahl, stadt,
                       latitude, longitude
                FROM depots WHERE id = ?
                """,
                (did,),
            ).fetchone()
            if r:
                self.enqueue_sync_change(
                    "depots",
                    "create",
                    {
                        "id": int(did),
                        "name": r[0],
                        "adresse": r[1],
                        "telefon": r[2],
                        "email": r[3],
                        "institution_id": r[4],
                        "strasse": r[5],
                        "hausnummer": r[6],
                        "postleitzahl": r[7],
                        "stadt": r[8],
                        "latitude": r[9],
                        "longitude": r[10],
                    },
                    dedupe_key=f"wizard:depots:create:{did}",
                )
        for kid in new_kontakt_ids:
            r = self.cur.execute(
                "SELECT depot_id, name, rolle, telefon, email FROM kontakte WHERE id = ?",
                (kid,),
            ).fetchone()
            if r:
                self.enqueue_sync_change(
                    "kontakte",
                    "create",
                    {
                        "id": int(kid),
                        "depot_id": int(r[0]),
                        "name": r[1],
                        "rolle": r[2],
                        "telefon": r[3],
                        "email": r[4],
                    },
                    dedupe_key=f"wizard:kontakte:create:{kid}",
                )
        for depot_id, praeparat_id, sollbestand in new_dp_keys:
            self.enqueue_sync_change(
                "depot_praeparate",
                "create",
                {
                    "depot_id": int(depot_id),
                    "praeparat_id": int(praeparat_id),
                    "sollbestand": int(sollbestand),
                },
                dedupe_key=f"wizard:depot_praeparate:{depot_id}:{praeparat_id}",
            )

    def get_smtp_settings(self) -> dict:
        port_raw = self.get_app_setting(DB.SETTING_SMTP_PORT, "587").strip() or "587"
        try:
            port = max(1, min(65535, int(port_raw)))
        except ValueError:
            port = 587
        return {
            "host": self.get_app_setting(DB.SETTING_SMTP_HOST).strip(),
            "port": port,
            "username": self.get_app_setting(DB.SETTING_SMTP_USERNAME).strip(),
            "password": self.get_app_setting(DB.SETTING_SMTP_PASSWORD),
            "use_tls": self.get_app_setting(DB.SETTING_SMTP_USE_TLS, "1").strip().lower() in {"1", "true", "yes", "on"},
            "use_ssl": self.get_app_setting(DB.SETTING_SMTP_USE_SSL, "0").strip().lower() in {"1", "true", "yes", "on"},
            "from_address": self.get_app_setting(DB.SETTING_SMTP_FROM_ADDRESS).strip(),
            "from_name": self.get_app_setting(DB.SETTING_SMTP_FROM_NAME).strip(),
        }

    def save_smtp_settings(self, cfg: dict) -> None:
        self.set_app_setting(DB.SETTING_SMTP_HOST, str(cfg.get("host", "") or ""))
        self.set_app_setting(DB.SETTING_SMTP_PORT, str(int(cfg.get("port", 587) or 587)))
        self.set_app_setting(DB.SETTING_SMTP_USERNAME, str(cfg.get("username", "") or ""))
        self.set_app_setting(DB.SETTING_SMTP_PASSWORD, str(cfg.get("password", "") or ""))
        self.set_app_setting(DB.SETTING_SMTP_USE_TLS, "1" if cfg.get("use_tls") else "0")
        self.set_app_setting(DB.SETTING_SMTP_USE_SSL, "1" if cfg.get("use_ssl") else "0")
        self.set_app_setting(DB.SETTING_SMTP_FROM_ADDRESS, str(cfg.get("from_address", "") or ""))
        self.set_app_setting(DB.SETTING_SMTP_FROM_NAME, str(cfg.get("from_name", "") or ""))

    def smtp_settings_missing_for_send(self, cfg: dict | None = None) -> list[str]:
        c = cfg if cfg is not None else self.get_smtp_settings()
        missing: list[str] = []
        if not (c.get("host") or "").strip():
            missing.append("SMTP-Server (Host)")
        if not (c.get("from_address") or "").strip():
            missing.append("Absender-E-Mail")
        if c.get("use_ssl") and c.get("use_tls"):
            missing.append("Nur eine Option: TLS (STARTTLS) oder SSL (SMTPS)")
        return missing

    def send_smtp_email(self, subject: str, message: str, recipients: list[str], cfg: dict | None = None) -> None:
        settings = dict(cfg) if cfg is not None else self.get_smtp_settings()
        missing = self.smtp_settings_missing_for_send(settings)
        if missing:
            raise RuntimeError("SMTP unvollständig: " + ", ".join(missing))
        to_list = [r.strip() for r in recipients if r and str(r).strip()]
        if not to_list:
            raise RuntimeError("Keine Empfänger.")

        msg = EmailMessage()
        msg["Subject"] = (subject or "").strip() or "ND-Hub Nachricht"
        from_addr = (settings.get("from_address") or "").strip()
        from_name = (settings.get("from_name") or "").strip()
        msg["From"] = f"{from_name} <{from_addr}>" if from_name else from_addr
        msg["To"] = ", ".join(to_list)
        msg.set_content(message or "")

        host = (settings.get("host") or "").strip()
        port = int(settings.get("port") or 587)
        use_ssl = bool(settings.get("use_ssl"))
        use_tls = bool(settings.get("use_tls"))
        user = (settings.get("username") or "").strip()
        password = settings.get("password") or ""
        timeout = 15

        try:
            if use_ssl:
                client = smtplib.SMTP_SSL(host, port, timeout=timeout)
            else:
                client = smtplib.SMTP(host, port, timeout=timeout)
            with client as smtp:
                smtp.ehlo()
                if use_tls and not use_ssl:
                    smtp.starttls()
                    smtp.ehlo()
                if user:
                    smtp.login(user, password)
                rejected = smtp.send_message(msg) or {}
        except Exception as exc:
            raise RuntimeError(f"SMTP-Versand fehlgeschlagen: {exc}") from exc

        rejected_addrs = sorted(str(a) for a in rejected.keys())
        if len(to_list) - len(rejected_addrs) <= 0:
            raise RuntimeError("SMTP hat keine Empfänger akzeptiert.")

    def test_smtp_connection(self, cfg: dict | None = None) -> tuple[bool, str]:
        settings = dict(cfg) if cfg is not None else self.get_smtp_settings()
        missing = self.smtp_settings_missing_for_send(settings)
        if missing:
            return False, "Unvollständig: " + ", ".join(missing)
        host = (settings.get("host") or "").strip()
        port = int(settings.get("port") or 587)
        use_ssl = bool(settings.get("use_ssl"))
        use_tls = bool(settings.get("use_tls"))
        user = (settings.get("username") or "").strip()
        password = settings.get("password") or ""
        timeout = 12
        try:
            if use_ssl:
                client = smtplib.SMTP_SSL(host, port, timeout=timeout)
            else:
                client = smtplib.SMTP(host, port, timeout=timeout)
            with client as smtp:
                smtp.ehlo()
                if use_tls and not use_ssl:
                    smtp.starttls()
                    smtp.ehlo()
                if user:
                    smtp.login(user, password)
        except Exception as exc:
            return False, str(exc)
        return True, "Verbindung und Anmeldung erfolgreich."

    # ----- Bewegungen -----
    def insert_bewegung(self, depot_id, prae_id, charge, verfall, eingang, ausgang, empfaenger, anzahl, typ):
        self.cur.execute("""
            INSERT INTO bewegungen (depot_id, praeparat_id, charge, verfall, eingang_datum, ausgang_datum, empfaenger, anzahl, typ)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (depot_id, prae_id, charge, verfall, eingang, ausgang, empfaenger, anzahl, typ))
        self.conn.commit()
        
        # Clear caches that depend on movement data
        if hasattr(self.get_all_praeparate_names, 'cache_clear'):
            self.get_all_praeparate_names.cache_clear()
        if hasattr(self.get_all_depot_names, 'cache_clear'):
            self.get_all_depot_names.cache_clear()

        bewegung_id = self.cur.lastrowid
        datum = eingang or ausgang
        depot_name = self.get_depot_name(int(depot_id)) or ""
        praeparat_name = self.get_praeparat_name(int(prae_id)) or ""
        self.enqueue_sync_change(
            entity_name="bewegungen",
            operation="create",
            payload={
                "id": int(bewegung_id),
                "depot_id": int(depot_id),
                "depot_name": depot_name,
                "praeparat_id": int(prae_id),
                "praeparat_name": praeparat_name,
                "typ": typ,
                "charge": charge,
                "verfall": verfall,
                "datum": datum,
                "anzahl": int(anzahl),
                "empfaenger": empfaenger,
            },
        )
        return bewegung_id

    def bulk_insert_bewegungen(self, movements_data):
        """Bulk insert movements for better performance"""
        if not movements_data:
            return []
        
        # Use executemany for bulk insert
        self.cur.executemany("""
            INSERT INTO bewegungen (depot_id, praeparat_id, charge, verfall, eingang_datum, ausgang_datum, empfaenger, anzahl, typ)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, movements_data)
        self.conn.commit()
        
        # Clear caches
        if hasattr(self.get_all_praeparate_names, 'cache_clear'):
            self.get_all_praeparate_names.cache_clear()
        if hasattr(self.get_all_depot_names, 'cache_clear'):
            self.get_all_depot_names.cache_clear()
        
        return [self.cur.lastrowid]

    def list_bewegungen_with_attachments(self, depot_id=None, typ=None, search_text=None):
        sql = """
            SELECT 
                b.id, d.name AS depot, p.name AS praeparat, b.typ, b.charge, b.verfall,
                b.eingang_datum, b.ausgang_datum, b.empfaenger, b.anzahl, b.datei_pfad
            FROM bewegungen b
            JOIN depots d ON d.id = b.depot_id
            JOIN praeparate p ON p.id = b.praeparat_id
            WHERE 1=1
        """
        params = []
        if depot_id:
            sql += " AND b.depot_id = ?"
            params.append(depot_id)
        if typ and typ != "Alle":
            sql += " AND b.typ = ?"
            params.append(typ)
        if search_text:
            sql += """ AND (
                d.name LIKE ? OR 
                p.name LIKE ? OR 
                b.typ LIKE ? OR 
                b.charge LIKE ? OR 
                b.empfaenger LIKE ?
            )"""
            wildcard = f"%{search_text}%"
            params.extend([wildcard] * 5)
            
        sql += " ORDER BY b.id DESC"
        return self.cur.execute(sql, params).fetchall()

    # ----- Attachments -----
    def link_bewegung_with_attachment(self, bewegung_id: int, local_file_path: str, dest_folder: str, depot_name: str = None):
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"Datei nicht gefunden: {local_file_path}")
        
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        
        if depot_name:
            safe_depot_name = "".join(c for c in depot_name if c.isalnum() or c in (' ', '_', '-'))
            full_dest = os.path.join(dest_folder, safe_depot_name, year, month)
        else:
            full_dest = os.path.join(dest_folder, year, month)
        
        os.makedirs(full_dest, exist_ok=True)
        
        ext = os.path.splitext(local_file_path)[1]
        filename = f"bewegung_{bewegung_id}_{now.strftime('%Y%m%d_%H%M%S')}{ext}"
        dest_path = os.path.join(full_dest, filename)
        
        shutil.copy2(local_file_path, dest_path)
        self.cur.execute("UPDATE bewegungen SET datei_pfad=? WHERE id=?", (dest_path, bewegung_id))
        self.conn.commit()
        return dest_path

    def get_attachment_for_bewegung(self, bewegung_id: int):
        row = self.cur.execute("SELECT datei_pfad FROM bewegungen WHERE id=?", (bewegung_id,)).fetchone()
        return row[0] if row and row[0] else None

    # ----- Berichte mit Soll/Ist-Vergleich -----
    def query_stock(self, depot_name=None):
        base_sql = """
            WITH v_saldo AS (
                SELECT depot_id, praeparat_id,
                       SUM(CASE WHEN typ='Zugang' THEN anzahl
                           WHEN typ IN ('Abgang','Vernichtung') THEN -anzahl ELSE 0 END) AS saldo
                FROM bewegungen GROUP BY depot_id, praeparat_id
            )
            SELECT 
                d.name AS Depot, 
                p.name AS Präparat, 
                dp.sollbestand AS Soll,
                COALESCE(v.saldo, 0) AS Ist,
                (COALESCE(v.saldo, 0) - dp.sollbestand) AS Differenz
            FROM depot_praeparate dp
            JOIN depots d ON d.id = dp.depot_id
            JOIN praeparate p ON p.id = dp.praeparat_id
            LEFT JOIN v_saldo v ON v.depot_id = dp.depot_id AND v.praeparat_id = dp.praeparat_id
        """
        params = []
        if depot_name and depot_name != "Alle Depots":
            base_sql += " WHERE d.name = ?"
            params.append(depot_name)
        base_sql += " ORDER BY d.name, p.name"
        rows = self.cur.execute(base_sql, params).fetchall()
        return [("Depot", "Präparat", "Soll", "Ist", "Differenz")] + rows

    def query_outgoing(self, year, depot_name=None):
        start = f"{year}-01-01"
        end = f"{year}-12-31"
        sql = """
            SELECT d.name AS Depot, p.name AS Präparat, b.charge AS Charge,
                   b.verfall AS Verfall, b.ausgang_datum AS Ausgang, b.empfaenger AS Empfänger, b.anzahl AS Anzahl
            FROM bewegungen b
            JOIN depots d ON d.id=b.depot_id
            JOIN praeparate p ON p.id=b.praeparat_id
            WHERE b.typ='Abgang' AND b.ausgang_datum >= ? AND b.ausgang_datum <= ?
        """
        params = [start, end]
        if depot_name and depot_name != "Alle Depots":
            sql += " AND d.name = ?"
            params.append(depot_name)
        sql += " ORDER BY d.name, p.name, b.ausgang_datum"
        rows = self.cur.execute(sql, params).fetchall()
        return [("Depot", "Präparat", "Charge", "Verfall", "Ausgang", "Empfänger", "Anzahl")] + rows

    # ----- Statistik-Abfragen -----
    def get_abgaben_by_praeparat(self, praeparat_name, years):
        results = {}
        for year in years:
            start = f"{year}-01-01"
            end = f"{year}-12-31"
            sql = """
                SELECT d.name AS depot, SUM(b.anzahl) AS gesamt
                FROM bewegungen b
                JOIN depots d ON d.id = b.depot_id
                JOIN praeparate p ON p.id = b.praeparat_id
                WHERE b.typ = 'Abgang'
                  AND p.name = ?
                  AND b.ausgang_datum >= ?
                  AND b.ausgang_datum <= ?
                GROUP BY d.name
                ORDER BY gesamt DESC
            """
            results[year] = self.cur.execute(sql, (praeparat_name, start, end)).fetchall()
        return results

    def get_abgaben_by_depot(self, depot_name, years):
        results = {}
        for year in years:
            start = f"{year}-01-01"
            end = f"{year}-12-31"
            sql = """
                SELECT p.name AS praeparat, SUM(b.anzahl) AS gesamt
                FROM bewegungen b
                JOIN depots d ON d.id = b.depot_id
                JOIN praeparate p ON p.id = b.praeparat_id
                WHERE b.typ = 'Abgang'
                  AND d.name = ?
                  AND b.ausgang_datum >= ?
                  AND b.ausgang_datum <= ?
                GROUP BY p.name
                ORDER BY gesamt DESC
            """
            results[year] = self.cur.execute(sql, (depot_name, start, end)).fetchall()
        return results

    @lru_cache(maxsize=128)
    def get_all_praeparate_names(self):
        return [row[0] for row in self.cur.execute("SELECT name FROM praeparate ORDER BY name").fetchall()]

    @lru_cache(maxsize=128)
    def get_all_depot_names(self):
        return [row[0] for row in self.cur.execute("SELECT name FROM depots ORDER BY name").fetchall()]

    @lru_cache(maxsize=256)
    def get_depot_id_by_name(self, name):
        row = self.cur.execute("SELECT id FROM depots WHERE name=?", (name,)).fetchone()
        return row[0] if row else None

    @lru_cache(maxsize=256)
    def get_praeparat_id_by_name(self, name):
        row = self.cur.execute("SELECT id FROM praeparate WHERE name=?", (name,)).fetchone()
        return row[0] if row else None

# ===== AUSWERTUNGEN - Neue Methoden für Phase 1 =====

    def get_bewegungen_analyse(self, depot_ids=None, praeparat_ids=None, start_date=None, end_date=None):
        """Bewegungsanalyse für Diagramme"""
        sql = """
            SELECT 
                d.name as depot_name,
                p.name as praeparat_name,
                b.typ,
                strftime('%Y-%m', b.eingang_datum) as monat,
                SUM(b.anzahl) as gesamt
            FROM bewegungen b
            JOIN depots d ON d.id = b.depot_id
            JOIN praeparate p ON p.id = b.praeparat_id
            WHERE 1=1
        """
        params = []

        if depot_ids:
            placeholders = ','.join('?' * len(depot_ids))
            sql += f" AND b.depot_id IN ({placeholders})"
            params.extend(depot_ids)

        if praeparat_ids:
            placeholders = ','.join('?' * len(praeparat_ids))
            sql += f" AND b.praeparat_id IN ({placeholders})"
            params.extend(praeparat_ids)

        if start_date:
            sql += " AND (b.eingang_datum >= ? OR b.ausgang_datum >= ?)"
            params.extend([start_date, start_date])

        if end_date:
            sql += " AND (b.eingang_datum <= ? OR b.ausgang_datum <= ?)"
            params.extend([end_date, end_date])

        sql += " GROUP BY d.name, p.name, b.typ, monat ORDER BY monat"

        return self.cur.execute(sql, params).fetchall()

    def get_bestandsentwicklung(self, depot_ids=None, praeparat_ids=None):
        """Bestandsentwicklung mit Soll/Ist-Vergleich"""
        sql = """
            SELECT 
                d.name as depot_name,
                p.name as praeparat_name,
                dp.sollbestand,
                COALESCE(SUM(CASE 
                    WHEN b.typ = 'Zugang' THEN b.anzahl
                    WHEN b.typ IN ('Abgang', 'Vernichtung') THEN -b.anzahl
                    ELSE 0 
                END), 0) as ist_bestand,
                COALESCE(SUM(CASE 
                    WHEN b.typ = 'Zugang' THEN b.anzahl
                    WHEN b.typ IN ('Abgang', 'Vernichtung') THEN -b.anzahl
                    ELSE 0 
                END), 0) - dp.sollbestand as differenz
            FROM depot_praeparate dp
            JOIN depots d ON d.id = dp.depot_id
            JOIN praeparate p ON p.id = dp.praeparat_id
            LEFT JOIN bewegungen b ON b.depot_id = dp.depot_id AND b.praeparat_id = dp.praeparat_id
            WHERE 1=1
        """
        params = []

        if depot_ids:
            placeholders = ','.join('?' * len(depot_ids))
            sql += f" AND dp.depot_id IN ({placeholders})"
            params.extend(depot_ids)

        if praeparat_ids:
            placeholders = ','.join('?' * len(praeparat_ids))
            sql += f" AND dp.praeparat_id IN ({placeholders})"
            params.extend(praeparat_ids)

        sql += " GROUP BY d.name, p.name, dp.sollbestand ORDER BY d.name, p.name"

        return self.cur.execute(sql, params).fetchall()

    def get_depot_ranking(self, praeparat_ids=None, start_date=None, end_date=None, limit=10):
        """Top Depots nach Bewegungen"""
        sql = """
            SELECT 
                d.name as depot_name,
                p.name as praeparat_name,
                SUM(CASE WHEN b.typ = 'Abgang' THEN b.anzahl ELSE 0 END) as abgaben_gesamt
            FROM bewegungen b
            JOIN depots d ON d.id = b.depot_id
            JOIN praeparate p ON p.id = b.praeparat_id
            WHERE b.typ = 'Abgang'
        """
        params = []

        if praeparat_ids:
            placeholders = ','.join('?' * len(praeparat_ids))
            sql += f" AND b.praeparat_id IN ({placeholders})"
            params.extend(praeparat_ids)

        if start_date:
            sql += " AND b.ausgang_datum >= ?"
            params.append(start_date)

        if end_date:
            sql += " AND b.ausgang_datum <= ?"
            params.append(end_date)

        sql += " GROUP BY d.name, p.name ORDER BY abgaben_gesamt DESC LIMIT ?"
        params.append(limit)

        return self.cur.execute(sql, params).fetchall()

    def get_praeparat_ranking(self, depot_ids=None, start_date=None, end_date=None, limit=10):
        """Top Präparate nach Bewegungen"""
        sql = """
            SELECT 
                p.name as praeparat_name,
                d.name as depot_name,
                SUM(CASE WHEN b.typ = 'Abgang' THEN b.anzahl ELSE 0 END) as abgaben_gesamt
            FROM bewegungen b
            JOIN depots d ON d.id = b.depot_id
            JOIN praeparate p ON p.id = b.praeparat_id
            WHERE b.typ = 'Abgang'
        """
        params = []

        if depot_ids:
            placeholders = ','.join('?' * len(depot_ids))
            sql += f" AND b.depot_id IN ({placeholders})"
            params.extend(depot_ids)

        if start_date:
            sql += " AND b.ausgang_datum >= ?"
            params.append(start_date)

        if end_date:
            sql += " AND b.ausgang_datum <= ?"
            params.append(end_date)

        sql += " GROUP BY p.name, d.name ORDER BY abgaben_gesamt DESC LIMIT ?"
        params.append(limit)

        return self.cur.execute(sql, params).fetchall()

    def get_matrix_data(self):
        """Matrix-Daten für Heatmap (Depot × Präparat)"""
        sql = """
            SELECT 
                d.name as depot_name,
                p.name as praeparat_name,
                dp.sollbestand,
                COALESCE(SUM(CASE 
                    WHEN b.typ = 'Zugang' THEN b.anzahl
                    WHEN b.typ IN ('Abgang', 'Vernichtung') THEN -b.anzahl
                    ELSE 0 
                END), 0) as ist_bestand
            FROM depot_praeparate dp
            JOIN depots d ON d.id = dp.depot_id
            JOIN praeparate p ON p.id = dp.praeparat_id
            LEFT JOIN bewegungen b ON b.depot_id = dp.depot_id AND b.praeparat_id = dp.praeparat_id
            GROUP BY d.name, p.name, dp.sollbestand
            ORDER BY d.name, p.name
        """
        return self.cur.execute(sql).fetchall()
    
    # In der Database-Klasse:

    def reset_test_data(self) -> tuple[bool, str, dict]:
        """
        Setzt Test-Daten zurück (Bewegungen + E-Mail-Verlauf).
        Behält alle Stammdaten (Depots, Kontakte, Präparate, Zuordnungen).
        
        Returns:
            (success: bool, message: str, statistics: dict)
        """
        try:
            # Prüfen welche Tabellen existieren
            def table_exists(table_name: str) -> bool:
                result = self.cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table_name,)
                ).fetchone()
                return result is not None
            
            # Statistik VOR dem Löschen sammeln
            stats_before = {}
            
            # Bewegungen zählen
            if table_exists('bewegungen'):
                stats_before['bewegungen'] = self.cur.execute(
                    "SELECT COUNT(*) FROM bewegungen"
                ).fetchone()[0]
            else:
                stats_before['bewegungen'] = 0
            
            # E-Mail-Verlauf zählen (MIT UNTERSTRICH!)
            if table_exists('email_verlauf'):
                stats_before['email_verlauf'] = self.cur.execute(
                    "SELECT COUNT(*) FROM email_verlauf"
                ).fetchone()[0]
            else:
                stats_before['email_verlauf'] = 0
            
            # Prüfen ob überhaupt etwas zu löschen ist
            total_to_delete = stats_before['bewegungen'] + stats_before['email_verlauf']
            if total_to_delete == 0:
                return True, "Datenbank ist bereits leer - nichts zu tun!", stats_before
            
            # Transaktionsbasiertes Löschen
            self.cur.execute("BEGIN TRANSACTION")
            
            deleted = {}
            
            # 1. Bewegungen löschen
            if table_exists('bewegungen') and stats_before['bewegungen'] > 0:
                self.cur.execute("DELETE FROM bewegungen")
                deleted['bewegungen'] = self.cur.rowcount
            else:
                deleted['bewegungen'] = 0
            
            # 2. E-Mail-Verlauf löschen (MIT UNTERSTRICH!)
            if table_exists('email_verlauf') and stats_before['email_verlauf'] > 0:
                self.cur.execute("DELETE FROM email_verlauf")
                deleted['email_verlauf'] = self.cur.rowcount
            else:
                deleted['email_verlauf'] = 0
            
            # 3. Meldungstracking zurücksetzen (falls vorhanden)
            if table_exists('meldungs_tracking'):
                self.cur.execute(
                    "UPDATE meldungs_tracking SET bewegungen_erhalten = 0, bestand_erhalten = 0"
                )
            
            # Transaktion abschließen
            self.conn.commit()
            
            # Erfolgs-Nachricht zusammenstellen
            msg_parts = ["Test-Daten erfolgreich zurückgesetzt!\n"]
            if deleted['bewegungen'] > 0:
                msg_parts.append(f"  • {deleted['bewegungen']} Bewegungen gelöscht")
            if deleted.get('email_verlauf', 0) > 0:
                msg_parts.append(f"  • {deleted['email_verlauf']} E-Mail-Einträge gelöscht")
            
            msg_parts.append("\nStammdaten bleiben erhalten:")
            msg_parts.append("  • Depots, Kontakte, Präparate, Zuordnungen")
            
            return True, "\n".join(msg_parts), deleted
            
        except sqlite3.Error as e:
            self.conn.rollback()
            return False, f"❌ Datenbankfehler: {e}", {}
        except Exception as e:
            self.conn.rollback()
            return False, f"❌ Fehler: {e}", {}

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

