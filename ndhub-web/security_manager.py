# -*- coding: utf-8 -*-
"""
SecurityManager - Benutzerverwaltung und Authentifizierung
Version: 2.0 (V32 - Kryptobereinigt)
"""

import sqlite3
import os
import logging
import hashlib
import secrets
import shutil
import threading
from typing import Optional, List, Tuple
from datetime import datetime
from contextlib import suppress

try:
    import pymysql
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False

logger = logging.getLogger(__name__)

# Versuche bcrypt zu laden
try:
    import bcrypt
    HAS_BCRYPT = True
    logger.info("✓ bcrypt verfügbar")
except ImportError:
    HAS_BCRYPT = False
    logger.warning("bcrypt nicht verfügbar - verwende PBKDF2-SHA256")



def _convert_qmark_to_percent_s(sql: str) -> str:
    """Convert DB-API qmark placeholders to pymysql format."""
    if "?" not in sql:
        return sql
    return sql.replace("?", "%s")


class _CursorAdapter:
    """Small adapter to normalize sqlite/pymysql cursor usage."""

    def __init__(self, db_kind: str, connection_adapter=None):
        self._cursor = None
        self._db_kind = db_kind
        self._connection_adapter = connection_adapter
        self._lock_depth = 0
        self._lastrowid = None

    def _acquire_lock(self):
        if self._connection_adapter is None:
            return
        self._connection_adapter.lock.acquire()
        self._lock_depth += 1

    def _release_lock(self):
        if self._connection_adapter is None or self._lock_depth <= 0:
            return
        self._connection_adapter.lock.release()
        self._lock_depth -= 1

    def _close_cursor(self):
        if self._cursor is None:
            return
        with suppress(Exception):
            self._cursor.close()
        self._cursor = None

    def execute(self, sql, params=None):
        if params is None:
            params = ()
        self._acquire_lock()
        try:
            self._close_cursor()
            if self._db_kind == "mariadb":
                sql = _convert_qmark_to_percent_s(sql)
            if self._db_kind == "mariadb" and self._connection_adapter is not None:
                self._connection_adapter.ensure_connection()
            self._cursor = self._connection_adapter._conn.cursor()
            try:
                self._cursor.execute(sql, params)
            except Exception:
                if self._db_kind != "mariadb" or self._connection_adapter is None:
                    raise
                # Retry once after reconnect for transient protocol/socket hiccups.
                self._close_cursor()
                self._connection_adapter.ensure_connection()
                self._cursor = self._connection_adapter._conn.cursor()
                self._cursor.execute(sql, params)
            self._lastrowid = getattr(self._cursor, "lastrowid", None)
            # For non-SELECT statements there is no result set to fetch;
            # release immediately to avoid blocking other requests.
            if self._cursor.description is None:
                self._close_cursor()
                self._release_lock()
        except Exception:
            self._close_cursor()
            self._release_lock()
            raise
        return self

    def fetchone(self):
        try:
            if self._cursor is None:
                return None
            return self._cursor.fetchone()
        finally:
            self._close_cursor()
            self._release_lock()

    def fetchall(self):
        try:
            if self._cursor is None:
                return []
            return self._cursor.fetchall()
        finally:
            self._close_cursor()
            self._release_lock()

    @property
    def lastrowid(self):
        return self._lastrowid


class _ConnectionAdapter:
    """Connection wrapper exposing unified cursor/commit/rollback/close."""

    def __init__(self, conn, db_kind: str, mariadb_connector=None):
        self._conn = conn
        self._db_kind = db_kind
        self._mariadb_connector = mariadb_connector
        self.lock = threading.RLock()

    def cursor(self):
        if self._db_kind == "mariadb" and self._conn is None and self._mariadb_connector is not None:
            self._conn = self._mariadb_connector()
        return _CursorAdapter(self._db_kind, self)

    def ensure_connection(self):
        if self._db_kind != "mariadb":
            return
        if self._conn is None:
            return
        ping = getattr(self._conn, "ping", None)
        if callable(ping):
            ping(reconnect=True)

    def commit(self):
        if self._db_kind == "mariadb":
            return None
        with self.lock:
            if self._db_kind == "mariadb":
                self.ensure_connection()
            return self._conn.commit()

    def rollback(self):
        if self._db_kind == "mariadb":
            return None
        with self.lock:
            with suppress(Exception):
                if self._db_kind == "mariadb":
                    self.ensure_connection()
                return self._conn.rollback()

    def close(self):
        if self._conn is None:
            return None
        return self._conn.close()


class SecurityManager:
    """
    Verwaltet Benutzerauthentifizierung und Rollenverwaltung
    """

    # Rollen-Definitionen
    ROLE_ADMIN = "Admin"
    ROLE_USER = "User"
    ROLES = [ROLE_ADMIN, ROLE_USER]

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db_kind = os.environ.get("ND_HUB_DB_ENGINE", "sqlite").strip().lower()
        if self.db_kind == "mariadb":
            if not HAS_PYMYSQL:
                raise RuntimeError("PyMySQL ist erforderlich fuer ND_HUB_DB_ENGINE=mariadb.")
            host = os.environ.get("ND_HUB_MARIADB_HOST", "mariadb").strip() or "mariadb"
            port = int((os.environ.get("ND_HUB_MARIADB_PORT", "3306") or "3306").strip() or "3306")
            database = os.environ.get("ND_HUB_MARIADB_DATABASE", "ndhub").strip() or "ndhub"
            user = os.environ.get("ND_HUB_MARIADB_USER", "ndhub").strip() or "ndhub"
            password = os.environ.get("ND_HUB_MARIADB_PASSWORD", "")
            raw_conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                charset="utf8mb4",
                autocommit=True,
            )
            self.conn = _ConnectionAdapter(raw_conn, "mariadb")
            self.cur = self.conn.cursor()
        else:
            raw_conn = sqlite3.connect(db_path, check_same_thread=False)
            self.conn = _ConnectionAdapter(raw_conn, "sqlite")
            self.cur = self.conn.cursor()
        self.current_user = None
        self.current_role = None

        # Erstelle Tabellen und Standard-Admin
        self._create_user_tables()
        self._create_default_admin()

        # Log Status
        logger.info(f"SecurityManager initialisiert")
        logger.info(f"  Datenbank: {db_path} (engine={self.db_kind})")
        logger.info(f"  bcrypt: {'✓ Aktiv' if HAS_BCRYPT else '✗ Nicht verfügbar'}")

    def _create_user_tables(self):
        """Erstellt die Benutzertabellen falls nicht vorhanden"""
        if self.db_kind == "mariadb":
            self.cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role VARCHAR(32) NOT NULL,
                    email VARCHAR(255),
                    created_at DATETIME NOT NULL,
                    last_login DATETIME NULL,
                    is_active TINYINT(1) DEFAULT 1,
                    failed_attempts INT DEFAULT 0,
                    locked_until DATETIME NULL,
                    is_default_password TINYINT(1) DEFAULT 0,
                    avatar_path TEXT,
                    permissions TEXT
                )
                """
            )
            # MariaDB supports IF NOT EXISTS in ADD COLUMN.
            self.cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_default_password TINYINT(1) DEFAULT 0")
            self.cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_path TEXT")
            self.cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS permissions TEXT")
            self.cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_activity_log (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_id BIGINT,
                    username VARCHAR(255),
                    action VARCHAR(255),
                    details TEXT,
                    timestamp DATETIME NOT NULL,
                    ip_address VARCHAR(64),
                    INDEX idx_user_activity_user_id (user_id),
                    CONSTRAINT fk_user_activity_user
                        FOREIGN KEY (user_id) REFERENCES users(id)
                        ON DELETE SET NULL
                )
                """
            )
        else:
            # Benutzertabelle
            self.cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('Admin', 'User')),
                    email TEXT,
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    is_active INTEGER DEFAULT 1,
                    failed_attempts INTEGER DEFAULT 0,
                    locked_until TEXT,
                    is_default_password INTEGER DEFAULT 0,
                    avatar_path TEXT,
                    permissions TEXT
                )
            """)

            # Für abwärtskompatibilität, füge Spalte is_default_password hinzu falls nicht existent
            try:
                self.cur.execute("ALTER TABLE users ADD COLUMN is_default_password INTEGER DEFAULT 0")
            except Exception:
                pass
            try:
                self.cur.execute("ALTER TABLE users ADD COLUMN avatar_path TEXT")
            except Exception:
                pass
            try:
                self.cur.execute("ALTER TABLE users ADD COLUMN permissions TEXT")
            except Exception:
                pass

            # Aktivitäts-Log
            self.cur.execute("""
                CREATE TABLE IF NOT EXISTS user_activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    action TEXT,
                    details TEXT,
                    timestamp TEXT NOT NULL,
                    ip_address TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)

        self.conn.commit()
        logger.info("Benutzertabellen erstellt/geprüft")

    def _create_default_admin(self):
        """Erstellt den Standard-Admin-Benutzer falls nicht vorhanden"""
        existing = self.cur.execute(
            "SELECT COUNT(*) FROM users WHERE username = ?", 
            ("admin",)
        ).fetchone()[0]

        if existing == 0:
            initial_password = os.environ.get("ND_HUB_INITIAL_ADMIN_PASSWORD", "").strip()
            generated_password = False
            if not initial_password:
                initial_password = secrets.token_urlsafe(18)
                generated_password = True

            password_hash = self.hash_password(initial_password)
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.cur.execute("""
                INSERT INTO users (username, password_hash, role, created_at, is_active, is_default_password)
                VALUES (?, ?, ?, ?, 1, 1)
            """, ("admin", password_hash, self.ROLE_ADMIN, now))
            self.conn.commit()
            if generated_password:
                logger.warning(
                    "Initialer Admin erstellt (Username: admin). "
                    "Kein ND_HUB_INITIAL_ADMIN_PASSWORD gesetzt; generiertes Initial-Passwort: %s",
                    initial_password
                )
            else:
                logger.info(
                    "Initialer Admin erstellt (Username: admin). Passwort aus ND_HUB_INITIAL_ADMIN_PASSWORD verwendet."
                )
        else:
            # Selbstheilung: Sicherstellen, dass 'admin' auch wirklich Admin-Rechte hat
            # Dies löst das Problem "Role is None" bei inkonsistenten Datenbanken
            self.cur.execute("""
                UPDATE users 
                SET role = ?, is_active = 1 
                WHERE username = ? AND (role IS NULL OR role = '' OR role != ?)
            """, (self.ROLE_ADMIN, "admin", self.ROLE_ADMIN))
            initial_password = os.environ.get("ND_HUB_INITIAL_ADMIN_PASSWORD", "").strip()
            force_sync = (os.environ.get("ND_HUB_FORCE_ADMIN_PASSWORD_SYNC", "0") or "0").strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
            if initial_password:
                row = self.cur.execute(
                    "SELECT id, is_default_password FROM users WHERE username = ?",
                    ("admin",),
                ).fetchone()
                if row:
                    admin_id = int(row[0])
                    is_default_password = int(row[1] or 0)
                    if is_default_password == 1 or force_sync:
                        # Keep deterministic bootstrap login in migrated environments
                        # while admin still uses default-password mode.
                        # Optional force mode allows one-time admin recovery after migration.
                        password_hash = self.hash_password(initial_password)
                        self.cur.execute(
                            """
                            UPDATE users
                            SET password_hash = ?, failed_attempts = 0, locked_until = NULL
                            WHERE id = ?
                            """,
                            (password_hash, admin_id),
                        )
            self.conn.commit()
  
    def is_using_default_password(self) -> bool:
        """
        Prüft, ob der aktuelle Benutzer das Standard-Passwort verwendet.
        
        Returns:
            True wenn Default-Passwort aktiv, sonst False
        """
        # Prüfe ob User eingeloggt ist
        if not hasattr(self, 'current_user') or not self.current_user:
            logger.warning("is_using_default_password aufgerufen ohne Login")
            return False
        
        try:
            cursor = self.conn.cursor()
            
            # User-ID aus Username holen
            cursor.execute("""
                SELECT id, is_default_password 
                FROM users 
                WHERE username = ?
            """, (self.current_user,))
            
            result = cursor.fetchone()
            
            if not result:
                logger.warning(f"User '{self.current_user}' nicht in DB gefunden")
                return False
            
            # Prüfe ob Spalte 'is_default_password' existiert
            user_id, is_default = result
            return is_default == 1
            
        except sqlite3.OperationalError as e:
            # Spalte existiert nicht -> immer False zurückgeben
            if "no such column" in str(e).lower() or "unknown column" in str(e).lower():
                logger.debug("Spalte 'is_default_password' existiert noch nicht")
                return False
            logger.error(f"DB-Fehler bei is_using_default_password: {e}")
            return False
        except Exception as e:
            logger.error(f"Unerwarteter Fehler: {e}", exc_info=True)
            return False

    # ==================== PASSWORD HASHING ====================

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash ein Passwort sicher"""
        if HAS_BCRYPT:
            return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        else:
            salt = os.urandom(32)
            pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 600000)
            return salt.hex() + pwdhash.hex()

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verifiziert ein Passwort gegen seinen Hash"""
        if not password_hash:
            return False
        try:
            if HAS_BCRYPT and password_hash.startswith('$2'):
                return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
            else:
                salt = bytes.fromhex(password_hash[:64])
                
                # Check for modern 600k iterations
                if hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 600000).hex() == password_hash[64:]:
                    return True
                # Check legacy 100k iterations fallback
                return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000).hex() == password_hash[64:]
        except Exception as e:
            logger.error(f"Passwort-Verifikation fehlgeschlagen: {e}")
            return False

    # ==================== USER AUTHENTICATION ====================

    def authenticate(self, username: str, password: str) -> Tuple[bool, str]:
        """
        Authentifiziert einen Benutzer

        Returns:
            (success: bool, message: str)
        """
        # Prüfe ob Benutzer existiert
        user = self.cur.execute("""
            SELECT id, username, password_hash, role, is_active, failed_attempts, locked_until
            FROM users WHERE username = ?
        """, (username,)).fetchone()

        if not user:
            return False, "Benutzername oder Passwort falsch"

        user_id, username, password_hash, role, is_active, failed_attempts, locked_until = user

        # Prüfe ob Account aktiv ist
        if not is_active:
            return False, "Dieser Account ist deaktiviert"

        # Prüfe ob Account gesperrt ist
        if locked_until:
            lock_time = datetime.strptime(locked_until, '%Y-%m-%d %H:%M:%S')
            if datetime.now() < lock_time:
                return False, f"Account ist gesperrt bis {locked_until}"
            else:
                # Entsperre Account
                self.cur.execute("""
                    UPDATE users SET locked_until = NULL, failed_attempts = 0 
                    WHERE id = ?
                """, (user_id,))
                self.conn.commit()

        # Verifiziere Passwort
        if self.verify_password(password, password_hash):
            # Erfolgreicher Login
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.cur.execute("""
                UPDATE users 
                SET last_login = ?, failed_attempts = 0, locked_until = NULL
                WHERE id = ?
            """, (now, user_id))
            self.conn.commit()

            self.current_user = username
            self.current_role = role

            # Log Activity
            self.log_activity(user_id, username, "LOGIN", "Erfolgreicher Login")

            logger.info(f"✓ Login: '{username}' ({role})")
            return True, f"Willkommen {username}!"
        else:
            # Fehlgeschlagener Login
            failed_attempts += 1
            locked_until = None

            # Sperre Account nach 5 fehlgeschlagenen Versuchen
            if failed_attempts >= 5:
                from datetime import timedelta
                lock_time = datetime.now() + timedelta(minutes=15)
                locked_until = lock_time.strftime('%Y-%m-%d %H:%M:%S')
                self.cur.execute("""
                    UPDATE users 
                    SET failed_attempts = ?, locked_until = ?
                    WHERE id = ?
                """, (failed_attempts, locked_until, user_id))
                self.conn.commit()
                return False, "Account wurde nach 5 Fehlversuchen für 15 Minuten gesperrt"
            else:
                self.cur.execute("""
                    UPDATE users SET failed_attempts = ? WHERE id = ?
                """, (failed_attempts, user_id))
                self.conn.commit()
                return False, f"Falsches Passwort ({5 - failed_attempts} Versuche übrig)"

    def logout(self):
        """Loggt den aktuellen Benutzer aus"""
        if self.current_user:
            logger.info(f"✓ Logout: '{self.current_user}'")
            self.current_user = None
            self.current_role = None

    def is_logged_in(self) -> bool:
        """Prüft ob ein Benutzer eingeloggt ist"""
        return self.current_user is not None

    def is_admin(self) -> bool:
        """Prüft ob der aktuelle Benutzer Admin ist"""
        return self.current_role == self.ROLE_ADMIN

    def get_current_user(self) -> Optional[str]:
        """Gibt den aktuellen Benutzernamen zurück"""
        return self.current_user

    def get_current_role(self) -> Optional[str]:
        """Gibt die aktuelle Rolle zurück"""
        return self.current_role

    def set_query_only(self, enabled: bool):
        """Schaltet diese Security-Verbindung auf read-only/write."""
        if self.db_kind != "sqlite":
            return
        try:
            self.cur.execute(f"PRAGMA query_only={'ON' if enabled else 'OFF'}")
            self.conn.commit()
        except Exception as e:
            logger.warning("Konnte query_only in SecurityManager nicht setzen: %s", e)

    # ==================== USER MANAGEMENT ====================

    def create_user(self, username: str, password: str, role: str, email: str = "") -> Tuple[bool, str]:
        """Erstellt einen neuen Benutzer (nur für Admins)"""
        if not self.is_admin():
            return False, "Keine Berechtigung"

        if role not in self.ROLES:
            return False, f"Ungültige Rolle. Erlaubt: {', '.join(self.ROLES)}"

        # Prüfe ob Username bereits existiert
        exists = self.cur.execute(
            "SELECT COUNT(*) FROM users WHERE username = ?", (username,)
        ).fetchone()[0]

        if exists:
            return False, "Benutzername existiert bereits"

        # Validiere Passwort
        if len(password) < 8:
            return False, "Passwort muss mindestens 8 Buchstaben, Ziffern oder Sonderzeichen lang sein"

        # Erstelle Benutzer
        password_hash = self.hash_password(password)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            self.cur.execute("""
                INSERT INTO users (username, password_hash, role, email, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (username, password_hash, role, email, now))
            self.conn.commit()

            user_id = self.cur.lastrowid
            self.log_activity(
                self.get_current_user_id(), 
                self.current_user, 
                "CREATE_USER", 
                f"Benutzer '{username}' erstellt (Rolle: {role})"
            )

            logger.info(f"✓ Benutzer '{username}' erstellt")
            return True, "Benutzer erfolgreich erstellt"
        except Exception as e:
            logger.error(f"✗ Fehler beim Erstellen: {e}")
            return False, f"Fehler: {str(e)}"

    def update_user(self, user_id: int, username: str = None, role: str = None, 
                   email: str = None, is_active: bool = None) -> Tuple[bool, str]:
        """Aktualisiert einen Benutzer (nur für Admins)"""
        if not self.is_admin():
            return False, "Keine Berechtigung"

        updates = []
        params = []

        if username:
            updates.append("username = ?")
            params.append(username)
        if role and role in self.ROLES:
            updates.append("role = ?")
            params.append(role)
        if email is not None:
            updates.append("email = ?")
            params.append(email)
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if is_active else 0)

        if not updates:
            return False, "Keine Änderungen"

        # Scanner-Schutz: Typisierung erzwingen
        safe_user_id = int(user_id)
        params.append(safe_user_id)
        sql = "".join(["UPDATE users SET ", ", ".join(updates), " WHERE id = ?"])

        try:
            self.cur.execute(sql, params)
            self.conn.commit()

            self.log_activity(
                self.get_current_user_id(), 
                self.current_user, 
                "UPDATE_USER", 
                f"Benutzer ID {safe_user_id} aktualisiert"
            )

            return True, "Benutzer aktualisiert"
        except Exception as e:
            logger.error(f"✗ Fehler beim Aktualisieren: {e}")
            return False, str(e)

    def delete_user(self, user_id: int) -> Tuple[bool, str]:
        """Löscht einen Benutzer (nur für Admins, nicht sich selbst)"""
        if not self.is_admin():
            return False, "Keine Berechtigung"

        # Verhindere Selbstlöschung
        current_user_id = self.get_current_user_id()
        if current_user_id == user_id:
            return False, "Sie können sich nicht selbst löschen"

        # Verhindere Löschung des letzten Admins
        user = self.cur.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
        if user and user[0] == self.ROLE_ADMIN:
            admin_count = self.cur.execute(
                "SELECT COUNT(*) FROM users WHERE role = ? AND is_active = 1", 
                (self.ROLE_ADMIN,)
            ).fetchone()[0]
            if admin_count <= 1:
                return False, "Der letzte Admin kann nicht gelöscht werden"

        try:
            username = self.cur.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()[0]
            self.cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
            self.conn.commit()

            self.log_activity(
                current_user_id, 
                self.current_user, 
                "DELETE_USER", 
                f"Benutzer '{username}' gelöscht"
            )

            return True, "Benutzer gelöscht"
        except Exception as e:
            logger.error(f"✗ Fehler beim Löschen: {e}")
            return False, str(e)

    def change_password(self, user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Ändert das Passwort eines Benutzers"""
        # Hole aktuellen Hash
        user = self.cur.execute(
            "SELECT password_hash, username FROM users WHERE id = ?", (user_id,)
        ).fetchone()

        if not user:
            return False, "Benutzer nicht gefunden"

        password_hash, username = user

        # Verifiziere altes Passwort
        if not self.verify_password(old_password, password_hash):
            return False, "Altes Passwort ist falsch"

        # Validiere neues Passwort
        if len(new_password) < 8:
            return False, "Neues Passwort muss mindestens 8 Buchstaben, Ziffern oder Sonderzeichen lang sein"

        # Setze neues Passwort und markiere, dass es kein Standard-Passwort mehr ist
        new_hash = self.hash_password(new_password)
        try:
            self.cur.execute("UPDATE users SET password_hash = ?, is_default_password = 0 WHERE id = ?", (new_hash, user_id))
            self.conn.commit()
            
            # Überprüfe ob Update erfolgreich war
            updated = self.cur.execute("SELECT is_default_password FROM users WHERE id = ?", (user_id,)).fetchone()
            if updated and updated[0] == 0:
                self.log_activity(user_id, username, "CHANGE_PASSWORD", "Passwort erfolgreich geändert")
                logger.info(f"✓ Passwort geändert und Flag zurückgesetzt: '{username}'")
                return True, "Passwort erfolgreich geändert"
            else:
                raise Exception("Datenbank-Flag 'is_default_password' konnte nicht auf 0 gesetzt werden.")
                
        except Exception as e:
            self.conn.rollback()
            logger.error(f"✗ Fehler beim Passwortändern: {e}")
            return False, f"Fehler beim Speichern: {str(e)}"

    def reset_password(self, user_id: int, new_password: str) -> Tuple[bool, str]:
        """Setzt das Passwort eines Benutzers zurück (nur für Admins)"""
        if not self.is_admin():
            return False, "Keine Berechtigung"

        if len(new_password) < 8:
            return False, "Passwort muss mindestens 8 Buchstaben, Ziffern oder Sonderzeichen lang sein"

        try:
            username = self.cur.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()[0]
            new_hash = self.hash_password(new_password)
            self.cur.execute("UPDATE users SET password_hash = ?, failed_attempts = 0, locked_until = NULL, is_default_password = ? WHERE id = ?", 
                           (new_hash, 1, user_id))
            self.conn.commit()

            self.log_activity(
                self.get_current_user_id(), 
                self.current_user, 
                "RESET_PASSWORD", 
                f"Passwort zurückgesetzt: '{username}'"
            )

            return True, "Passwort zurückgesetzt"
        except Exception as e:
            return False, str(e)

    def list_users(self) -> List[Tuple]:
        """Listet alle Benutzer auf"""
        return self.cur.execute("""
            SELECT id, username, role, email, created_at, last_login, is_active, failed_attempts, locked_until, is_default_password, permissions
            FROM users
            ORDER BY username
        """).fetchall()

    def get_current_user_id(self) -> Optional[int]:
        """Gibt die ID des aktuellen Benutzers zurück"""
        if not self.current_user:
            return None
        row = self.cur.execute("SELECT id FROM users WHERE username = ?", (self.current_user,)).fetchone()
        return row[0] if row else None

    def get_user_avatar_path(self, user_id: int) -> Optional[str]:
        """Gibt den Avatar-Pfad eines Benutzers zurück."""
        row = self.cur.execute("SELECT avatar_path FROM users WHERE id = ?", (int(user_id),)).fetchone()
        if not row:
            return None
        return row[0] or None

    def get_current_user_avatar_path(self) -> Optional[str]:
        """Gibt den Avatar-Pfad des aktuell angemeldeten Benutzers zurück."""
        user_id = self.get_current_user_id()
        if not user_id:
            return None
        return self.get_user_avatar_path(user_id)

    def set_user_avatar(self, user_id: int, image_path: str) -> Tuple[bool, str]:
        """Setzt/aktualisiert Avatar für einen Benutzer."""
        safe_user_id = int(user_id)
        current_user_id = self.get_current_user_id()
        if not self.is_admin() and current_user_id != safe_user_id:
            return False, "Keine Berechtigung zum Ändern dieses Profilbilds."
        if not image_path or not os.path.exists(image_path):
            return False, "Bilddatei wurde nicht gefunden."

        ext = os.path.splitext(image_path)[1].lower()
        if ext not in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
            return False, "Nur PNG/JPG/JPEG/WEBP/BMP sind erlaubt."

        avatar_dir = os.path.join(os.path.dirname(self.db_path), "Avatars")
        os.makedirs(avatar_dir, exist_ok=True)
        target_path = os.path.join(avatar_dir, f"user_{safe_user_id}{ext}")

        try:
            shutil.copy2(image_path, target_path)
            self.cur.execute("UPDATE users SET avatar_path = ? WHERE id = ?", (target_path, safe_user_id))
            self.conn.commit()
            return True, "Profilbild gespeichert."
        except Exception as e:
            logger.error("Fehler beim Speichern des Profilbilds: %s", e)
            return False, f"Fehler beim Speichern: {e}"

    def clear_user_avatar(self, user_id: int) -> Tuple[bool, str]:
        """Entfernt Avatar-Eintrag eines Benutzers."""
        safe_user_id = int(user_id)
        current_user_id = self.get_current_user_id()
        if not self.is_admin() and current_user_id != safe_user_id:
            return False, "Keine Berechtigung zum Entfernen dieses Profilbilds."

        try:
            old_path = self.get_user_avatar_path(safe_user_id)
            self.cur.execute("UPDATE users SET avatar_path = NULL WHERE id = ?", (safe_user_id,))
            self.conn.commit()
            if old_path and os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass
            return True, "Profilbild entfernt."
        except Exception as e:
            logger.error("Fehler beim Entfernen des Profilbilds: %s", e)
            return False, f"Fehler beim Entfernen: {e}"

    # ==================== ACTIVITY LOGGING ====================

    def log_activity(self, user_id: int, username: str, action: str, details: str = "", ip: str = ""):
        """Loggt eine Benutzeraktion"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            self.cur.execute("""
                INSERT INTO user_activity_log (user_id, username, action, details, timestamp, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, username, action, details, now, ip))
            self.conn.commit()
        except Exception as e:
            logger.error(f"✗ Logging-Fehler: {e}")

    def get_activity_log(self, user_id: int = None, limit: int = 100) -> List[Tuple]:
        """Holt das Aktivitätslog"""
        if user_id:
            return self.cur.execute("""
                SELECT id, username, action, details, timestamp
                FROM user_activity_log
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit)).fetchall()
        else:
            return self.cur.execute("""
                SELECT id, username, action, details, timestamp
                FROM user_activity_log
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()


    def close(self):
        """Schließt die Datenbankverbindung"""
        if self.conn:
            self.conn.close()
            logger.info("SecurityManager geschlossen")
