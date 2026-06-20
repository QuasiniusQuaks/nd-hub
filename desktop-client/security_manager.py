"""
SecurityManager - Benutzerverwaltung und Authentifizierung
Version: 2.0 (V32 - Kryptobereinigt)
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import shutil
import sqlite3
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Versuche bcrypt zu laden
try:
    import bcrypt
    HAS_BCRYPT = True
    logger.info("✓ bcrypt verfügbar")
except ImportError:
    HAS_BCRYPT = False
    logger.warning("bcrypt nicht verfügbar - verwende PBKDF2-SHA256")



class SecurityManager:
    """
    Verwaltet Benutzerauthentifizierung und Rollenverwaltung
    """

    # Rollen-Definitionen
    ROLE_ADMIN = "Admin"
    ROLE_USER = "User"
    ROLES = [ROLE_ADMIN, ROLE_USER]

    def __init__(self, db_path: str = "", *, database: Optional["Database"] = None):
        """
        Initialisiert den SecurityManager.

        Args:
            db_path: Pfad zur Datenbank (Legacy-Modus — eigene Connection).
            database: Optional, bestehende ``Database``-Instanz. Wenn
                      übergeben, wird deren Connection geteilt (kein
                      Lock-Contention). Issue #18: Architektur-Audit-Befund.
        """
        if database is not None:
            self._db = database
            self.db_path = database.path
            self.conn = database.conn
            self.cur = database.cur
            self._owns_connection = False
        else:
            if not db_path:
                raise TypeError(
                    "SecurityManager benötigt entweder 'db_path' (nicht-leer) oder 'database'"
                )
            self._db = None
            self.db_path = db_path
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.cur = self.conn.cursor()
            self._owns_connection = True
        self.current_user = None
        self.current_role = None

        # Erstelle Tabellen und Standard-Admin
        self._create_user_tables()
        self._create_default_admin()

        # Log Status
        logger.info("SecurityManager initialisiert (Mode: %s)",
                    "geteilt mit Database" if not self._owns_connection else "eigene Connection")
        logger.info("  Datenbank: %s", self.db_path)
        logger.info("  bcrypt: %s", '✓ Aktiv' if HAS_BCRYPT else '✗ Nicht verfügbar')

    def _create_user_tables(self):
        """Erstellt die Benutzertabellen falls nicht vorhanden"""
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
        except sqlite3.OperationalError:
            pass
        try:
            self.cur.execute("ALTER TABLE users ADD COLUMN avatar_path TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            self.cur.execute("ALTER TABLE users ADD COLUMN permissions TEXT")
        except sqlite3.OperationalError:
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
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS user_depot_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                depot_id INTEGER NOT NULL,
                can_read INTEGER NOT NULL DEFAULT 0,
                can_write INTEGER NOT NULL DEFAULT 0,
                UNIQUE(username, depot_id)
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
            if "no such column" in str(e):
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
        """Verifiziert ein Passwort gegen seinen Hash.

        Security-Hinweis: Der Vergleich nutzt ``hmac.compare_digest`` statt
        ``==``, um Timing-Attacken zu verhindern. Beide Iterationszählungen
        (modern 600k + legacy 100k) werden parallel berechnet, damit die
        Funktion *unabhängig* vom Hash-Format eine konstante Laufzeit hat —
        ein Angreifer kann nicht aus der Antwortzeit auf das Hash-Format
        oder Teile des Hashes schließen.
        """
        if not password_hash:
            return False
        try:
            if HAS_BCRYPT and password_hash.startswith('$2'):
                return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
            salt = bytes.fromhex(password_hash[:64])
            password_bytes = password.encode('utf-8')

            # Beide Varianten berechnen — konstante Zeit unabhängig vom Treffer
            modern = hashlib.pbkdf2_hmac('sha256', password_bytes, salt, 600000).hex()
            legacy = hashlib.pbkdf2_hmac('sha256', password_bytes, salt, 100000).hex()

            # Constant-time compare gegen BEIDE möglichen Hash-Suffixe
            modern_match = hmac.compare_digest(modern, password_hash[64:])
            legacy_match = hmac.compare_digest(legacy, password_hash[64:])
            return modern_match or legacy_match
        except Exception as e:
            logger.error(f"Passwort-Verifikation fehlgeschlagen: {e}")
            return False

    # ==================== USER AUTHENTICATION ====================

    def authenticate(self, username: str, password: str) -> tuple[bool, str]:
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

    def get_current_user(self) -> str | None:
        """Gibt den aktuellen Benutzernamen zurück"""
        return self.current_user

    def get_current_role(self) -> str | None:
        """Gibt die aktuelle Rolle zurück"""
        return self.current_role

    def get_current_permissions(self) -> set[str]:
        """Liefert effektive Berechtigungen des aktuellen Benutzers."""
        if self.current_role == self.ROLE_ADMIN:
            return {
                "masterdata_read",
                "masterdata_write",
                "movements_read",
                "movements_write",
                "settings_read",
                "settings_write",
                "reports_view",
                "users_manage",
            }
        if not self.current_user:
            return set()
        row = self.cur.execute("SELECT permissions FROM users WHERE username = ?", (self.current_user,)).fetchone()
        raw = row[0] if row else None
        if not raw:
            return set()
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = []
        else:
            parsed = raw
        if not isinstance(parsed, list):
            return set()
        return {str(item).strip() for item in parsed if str(item).strip()}

    def has_permission(self, permission_key: str) -> bool:
        if self.current_role == self.ROLE_ADMIN:
            return True
        return permission_key in self.get_current_permissions()

    PERMISSION_CROSS_INSTITUTION_READ = "cross_institution_read"
    PERMISSION_CROSS_INSTITUTION_WRITE = "cross_institution_write"

    def can_view_cross_institution_masterdata(self) -> bool:
        """True, wenn fremde Institutionen/Depots (Lesen) freigeschaltet sind."""
        return self.has_permission(self.PERMISSION_CROSS_INSTITUTION_READ)

    def can_edit_cross_institution_masterdata(self) -> bool:
        """True, wenn Stammdaten fremder Institutionen bearbeitet werden duerfen."""
        return self.has_permission(self.PERMISSION_CROSS_INSTITUTION_WRITE)

    def has_depot_access(self, depot_id: int, write: bool = False) -> bool:
        """Prüft depotgenauen Read/Write Zugriff."""
        if self.current_role == self.ROLE_ADMIN:
            return True
        if not self.current_user:
            return False
        row = self.cur.execute(
            "SELECT can_read, can_write FROM user_depot_permissions WHERE username = ? AND depot_id = ?",
            (self.current_user, int(depot_id)),
        ).fetchone()
        if not row:
            return False
        can_read = bool(int(row[0] or 0))
        can_write = bool(int(row[1] or 0))
        return can_write if write else can_read

    def set_query_only(self, enabled: bool):
        """Schaltet diese Security-Verbindung auf read-only/write."""
        try:
            self.cur.execute(f"PRAGMA query_only={'ON' if enabled else 'OFF'}")
            self.conn.commit()
        except sqlite3.Error as e:
            logger.warning("Konnte query_only in SecurityManager nicht setzen: %s", e)

    # ==================== USER MANAGEMENT ====================

    def create_user(self, username: str, password: str, role: str, email: str = "") -> tuple[bool, str]:
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
                   email: str = None, is_active: bool = None) -> tuple[bool, str]:
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
        # SET clauses are hardcoded "<column> = ?" strings from an explicit
        # allow-list; only the values are parameterized and user-controlled.
        sql = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"  # nosec B608

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

    def delete_user(self, user_id: int) -> tuple[bool, str]:
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

    def change_password(self, user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
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

    def reset_password(self, user_id: int, new_password: str) -> tuple[bool, str]:
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

    def unlock_user(self, user_id: int) -> tuple[bool, str]:
        """Entsperrt einen Benutzeraccount (setzt Lock/Fehlversuche zurueck)."""
        if not self.is_admin():
            return False, "Keine Berechtigung"
        try:
            row = self.cur.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
            if not row:
                return False, "Benutzer nicht gefunden"
            username = str(row[0])
            self.cur.execute(
                "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?",
                (int(user_id),),
            )
            self.conn.commit()
            self.log_activity(
                self.get_current_user_id(),
                self.current_user,
                "UNLOCK_USER",
                f"Benutzer entsperrt: '{username}'",
            )
            return True, "Benutzer entsperrt"
        except Exception as e:
            return False, str(e)

    def list_users(self) -> list[tuple]:
        """Listet alle Benutzer auf"""
        return self.cur.execute("""
            SELECT id, username, role, email, created_at, last_login, is_active, failed_attempts, locked_until, is_default_password, permissions
            FROM users
            ORDER BY username
        """).fetchall()

    def get_current_user_id(self) -> int | None:
        """Gibt die ID des aktuellen Benutzers zurück"""
        if not self.current_user:
            return None
        row = self.cur.execute("SELECT id FROM users WHERE username = ?", (self.current_user,)).fetchone()
        return row[0] if row else None

    def get_user_avatar_path(self, user_id: int) -> str | None:
        """Gibt den Avatar-Pfad eines Benutzers zurück."""
        row = self.cur.execute("SELECT avatar_path FROM users WHERE id = ?", (int(user_id),)).fetchone()
        if not row:
            return None
        return row[0] or None

    def get_current_user_avatar_path(self) -> str | None:
        """Gibt den Avatar-Pfad des aktuell angemeldeten Benutzers zurück."""
        user_id = self.get_current_user_id()
        if not user_id:
            return None
        return self.get_user_avatar_path(user_id)

    def set_user_avatar(self, user_id: int, image_path: str) -> tuple[bool, str]:
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

    def clear_user_avatar(self, user_id: int) -> tuple[bool, str]:
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

    def get_activity_log(self, user_id: int = None, limit: int = 100) -> list[tuple]:
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
                logger.debug("SecurityManager close fehlgeschlagen: %s", exc)
            logger.info("SecurityManager geschlossen")
