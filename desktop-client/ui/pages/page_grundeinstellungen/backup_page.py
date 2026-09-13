"""Backup-UI-Tab und Backup-Hilfsmethoden (Issue #93)."""
import logging
import os
import shutil
import sqlite3
import sys
import time
from datetime import datetime

from apple_theme import AppleTheme
from icon_manager import IconManager
from PySide6 import QtWidgets

from ui.utils import create_card_widget

logger = logging.getLogger("ND-Hub")


def create_backup_tab(self):
    """Erstellt den Backup-Tab"""
    tab = QtWidgets.QWidget()
    outer_layout = QtWidgets.QVBoxLayout(tab)
    outer_layout.setContentsMargins(0, 0, 0, 0)
    outer_layout.setSpacing(0)

    scroll = QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
    outer_layout.addWidget(scroll)

    content = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(content)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(20)
    scroll.setWidget(content)

    # === Manuelles Backup ===
    backup_card = create_card_widget()
    backup_layout = QtWidgets.QVBoxLayout(backup_card)

    c = AppleTheme.current_colors()
    backup_title = QtWidgets.QLabel("Backup erstellen")
    backup_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {c['label']}; margin-bottom: 8px;")
    backup_layout.addWidget(backup_title)

    backup_info = QtWidgets.QLabel(
        "Erstellen Sie eine Sicherungskopie der gesamten Datenbank.\n"
        "Die Backup-Datei enthält alle Depots, Präparate, Bewegungen und Einstellungen."
    )
    backup_info.setWordWrap(True)
    backup_info.setStyleSheet(f"color: {c['secondary_label']}; font-size: 13px; margin-bottom: 12px;")
    backup_layout.addWidget(backup_info)

    backup_path_layout = QtWidgets.QHBoxLayout()
    backup_path_layout.addWidget(QtWidgets.QLabel("Backup-Ordner:"))
    self.backup_path_input = QtWidgets.QLineEdit()
    self.backup_path_input.setPlaceholderText("\\ND-Hub\\Backups")
    self.backup_path_input.setText(self.get_default_backup_path())
    backup_path_layout.addWidget(self.backup_path_input, 1)

    self.btn_browse_backup = QtWidgets.QPushButton(" Durchsuchen")
    self.btn_browse_backup.setIcon(IconManager.get_icon("folder"))
    self.btn_browse_backup.setObjectName("btn_secondary")
    backup_path_layout.addWidget(self.btn_browse_backup)
    backup_layout.addLayout(backup_path_layout)

    self.btn_create_backup = QtWidgets.QPushButton(" Backup jetzt erstellen")
    self.btn_create_backup.setIcon(IconManager.get_icon("refresh"))
    self.btn_create_backup.setObjectName("btn_save")
    self.btn_create_backup.setMinimumHeight(44)
    backup_layout.addWidget(self.btn_create_backup)

    layout.addWidget(backup_card)

    # === Auto-Backup ===
    auto_backup_card = create_card_widget()
    auto_backup_layout = QtWidgets.QVBoxLayout(auto_backup_card)

    c = AppleTheme.current_colors()
    auto_backup_title = QtWidgets.QLabel("Automatisches Backup")
    auto_backup_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {c['label']}; margin-bottom: 8px;")
    auto_backup_layout.addWidget(auto_backup_title)

    auto_backup_info = QtWidgets.QLabel(
        "Aktivieren Sie automatische Backups beim Programmstart.\n"
        "Es wird maximal ein Backup pro Tag erstellt."
    )
    auto_backup_info.setWordWrap(True)
    auto_backup_info.setStyleSheet(f"color: {c['secondary_label']}; font-size: 13px; margin-bottom: 12px;")
    auto_backup_layout.addWidget(auto_backup_info)

    self.check_auto_backup_enabled = QtWidgets.QCheckBox("Automatisches Backup beim Start aktivieren")
    self.check_auto_backup_enabled.setProperty("requires_write", True)
    auto_backup_setting = self.load_auto_backup_setting()
    self.check_auto_backup_enabled.setChecked(auto_backup_setting)
    self.check_auto_backup_enabled.toggled.connect(self.save_auto_backup_setting_from_bool)
    auto_backup_layout.addWidget(self.check_auto_backup_enabled)

    c = AppleTheme.current_colors()
    auto_backup_info2 = QtWidgets.QLabel("Backups werden im oben angegebenen Ordner gespeichert.")
    auto_backup_info2.setWordWrap(True)
    auto_backup_info2.setStyleSheet(f"color: {c['tertiary_label']}; font-size: 12px; font-style: italic; margin-top: 8px;")
    auto_backup_layout.addWidget(auto_backup_info2)

    layout.addWidget(auto_backup_card)

    # === NEU: Test-Daten zurücksetzen ===
    reset_card = create_card_widget()
    reset_layout = QtWidgets.QVBoxLayout(reset_card)

    c = AppleTheme.current_colors()
    reset_title = QtWidgets.QLabel("Test-Daten zurücksetzen")
    reset_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {c['label']}; margin-bottom: 8px;")
    reset_layout.addWidget(reset_title)

    reset_info = QtWidgets.QLabel(
        "Löscht alle Bewegungen und den E-Mail-Verlauf.\n"
        "Depots, Kontakte, Präparate und Sollbestände bleiben erhalten.\n"
        "Ideal zum Zurücksetzen nach Tests."
    )
    reset_info.setWordWrap(True)
    reset_info.setStyleSheet(f"color: {c['secondary_label']}; font-size: 13px; margin-bottom: 12px;")
    reset_layout.addWidget(reset_info)

    reset_warning = QtWidgets.QLabel(
        "ACHTUNG: Diese Aktion kann nicht rückgängig gemacht werden!\n"
        "Erstellen Sie vorher ein Backup."
    )
    reset_warning.setWordWrap(True)
    reset_warning.setStyleSheet(
        "background-color: #fff3cd; color: #856404; padding: 12px; "
        "border-radius: 6px; border: 1px solid #ffc107; font-weight: 500; margin-bottom: 12px;"
    )
    reset_layout.addWidget(reset_warning)

    self.btn_reset_data = QtWidgets.QPushButton("Test-Daten jetzt zurücksetzen")
    self.btn_reset_data.setIcon(IconManager.get_icon("delete"))
    self.btn_reset_data.setObjectName("btn_delete")
    self.btn_reset_data.setMinimumHeight(44)
    reset_layout.addWidget(self.btn_reset_data)

    layout.addWidget(reset_card)

    # === Wiederherstellung ===
    restore_card = create_card_widget()
    restore_layout = QtWidgets.QVBoxLayout(restore_card)

    c = AppleTheme.current_colors()
    restore_title = QtWidgets.QLabel("Backup wiederherstellen")
    restore_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {c['label']}; margin-bottom: 8px;")
    restore_layout.addWidget(restore_title)

    restore_warning = QtWidgets.QLabel(
        "ACHTUNG: Das Wiederherstellen eines Backups überschreibt ALLE aktuellen Daten!\n"
        "Erstellen Sie vorher unbedingt ein aktuelles Backup."
    )
    restore_warning.setWordWrap(True)
    restore_warning.setStyleSheet(
        f"background-color: {c['status_orange_bg']}; color: {c['status_orange']}; padding: 12px; "
        f"border-radius: 6px; border: 1px solid {c['status_orange']}; font-weight: 500; margin-bottom: 12px;"
    )
    restore_layout.addWidget(restore_warning)

    restore_path_layout = QtWidgets.QHBoxLayout()
    restore_path_layout.addWidget(QtWidgets.QLabel("Backup-Datei:"))
    self.restore_path_input = QtWidgets.QLineEdit()
    self.restore_path_input.setPlaceholderText("Backup-Datei auswählen...")
    self.restore_path_input.setReadOnly(True)
    restore_path_layout.addWidget(self.restore_path_input, 1)

    self.btn_browse_restore = QtWidgets.QPushButton(" Durchsuchen")
    self.btn_browse_restore.setIcon(IconManager.get_icon("folder"))
    self.btn_browse_restore.setObjectName("btn_secondary")
    restore_path_layout.addWidget(self.btn_browse_restore)
    restore_layout.addLayout(restore_path_layout)

    self.btn_restore_backup = QtWidgets.QPushButton(" Backup wiederherstellen")
    self.btn_restore_backup.setIcon(IconManager.get_icon("refresh_ccw"))
    self.btn_restore_backup.setObjectName("btn_delete")
    self.btn_restore_backup.setMinimumHeight(44)
    self.btn_restore_backup.setEnabled(False)
    restore_layout.addWidget(self.btn_restore_backup)

    layout.addWidget(restore_card)
    layout.addStretch()

    # Signals
    self.btn_browse_backup.clicked.connect(self.browse_backup_folder)
    self.btn_create_backup.clicked.connect(self.create_backup)
    self.btn_reset_data.clicked.connect(self.reset_test_data)  # NEU
    self.btn_browse_restore.clicked.connect(self.browse_restore_file)
    self.btn_restore_backup.clicked.connect(self.restore_backup)

    return tab


def reset_test_data(self):
    """Setzt Test-Daten zurück mit Bestätigung"""
    if self._is_read_only_mode():
        QtWidgets.QMessageBox.warning(self, "Nur-Lesen Modus", "Zurücksetzen ist nur mit Schreibzugriff möglich.")
        return

    # Erste Bestätigung
    reply = QtWidgets.QMessageBox.warning(
        self,
        "Test-Daten zurücksetzen",
        "WARNUNG: Diese Aktion löscht unwiderruflich:\n\n"
        "  • Alle Bewegungen (Zugang/Abgang/Vernichtung)\n"
        "  • Den gesamten E-Mail-Verlauf\n\n"
        "Folgende Daten bleiben erhalten:\n\n"
        "  • Depots\n"
        "  • Kontakte\n"
        "  • Präparate\n"
        "  • Zuordnungen mit Sollbeständen\n\n"
        "Möchten Sie fortfahren?",
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        QtWidgets.QMessageBox.No
    )

    if reply != QtWidgets.QMessageBox.Yes:
        return

    # Zweite Sicherheitsabfrage mit Texteingabe
    text, ok = QtWidgets.QInputDialog.getText(
        self,
        "Bestätigung erforderlich",
        "Bitte geben Sie 'ZURÜCKSETZEN' ein, um fortzufahren:",
        QtWidgets.QLineEdit.Normal,
        ""
    )

    if not ok or text.upper() != "ZURÜCKSETZEN":
        QtWidgets.QMessageBox.information(
            self,
            "Abgebrochen",
            "Reset wurde abgebrochen."
        )
        return

    # Backup erstellen (optional, aber empfohlen)
    backup_path = None
    try:
        import shutil
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{self.db.path}.before_reset_{timestamp}"
        shutil.copy2(self.db.path, backup_path)
        backup_created = True
    except Exception as e:
        backup_created = False
        reply = QtWidgets.QMessageBox.warning(
            self,
            "Backup fehlgeschlagen",
            f"Backup konnte nicht erstellt werden:\n{e}\n\n"
            "Trotzdem fortfahren?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

    # Reset durchführen
    success, msg, stats = self.db.reset_test_data()

    if success:
        # Erfolgs-Nachricht mit Backup-Info
        full_msg = msg
        if backup_created and backup_path:
            full_msg += f"\n\n💾 Backup erstellt:\n{backup_path}"

        QtWidgets.QMessageBox.information(
            self,
            "Erfolgreich",
            full_msg
        )

    else:
        QtWidgets.QMessageBox.critical(
            self,
            "Fehler",
            msg
        )


def get_default_backup_path(self):
    """Ermittelt den Standard-Backup-Pfad"""
    db_dir = os.path.dirname(self.db.path)
    backup_dir = os.path.join(db_dir, "Backups")
    return backup_dir


def browse_backup_folder(self):
    """Backup-Ordner auswählen"""
    folder = QtWidgets.QFileDialog.getExistingDirectory(
        self, "Backup-Ordner auswählen", self.backup_path_input.text()
    )
    if folder:
        self.backup_path_input.setText(folder)


def create_backup(self):
    """Erstellt ein Backup der Datenbank - INKL. WAL!"""
    if self._is_read_only_mode():
        QtWidgets.QMessageBox.warning(self, "Nur-Lesen Modus", "Backup erstellen ist nur mit Schreibzugriff möglich.")
        return
    backup_dir = self.backup_path_input.text().strip()

    if not backup_dir:
        QtWidgets.QMessageBox.warning(self, "Fehler", "Bitte einen Backup-Ordner angeben.")
        return

    try:
        # ✅ 1. WAL-Checkpoint: Alle Änderungen in Hauptdatei schreiben
        try:
            self.db.cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self.db.conn.commit()
            print("WAL-Checkpoint durchgeführt")
        except Exception as e:
            print(f"⚠ WAL-Checkpoint Warnung: {e}")

        # ✅ 2. Ordner erstellen
        os.makedirs(backup_dir, exist_ok=True)

        # ✅ 3. Zeitstempel
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)

        # ✅ 4. Backup erstellen (nur .db, da WAL bereits gemergt ist)
        shutil.copy2(self.db.path, backup_path)

        # ✅ 5. Backup verifizieren
        if self._verify_backup(backup_path):
            print(f"Backup erstellt und verifiziert: {backup_path}")

            # ✅ 6. Alte Backups aufräumen (max. 10 behalten)
            self._rotate_backups(backup_dir)

            # ✅ 7. Erfolg!
            filesize_kb = os.path.getsize(backup_path) / 1024
            QtWidgets.QMessageBox.information(
                self,
                "✅ Backup erstellt",
                f"Backup erfolgreich erstellt:\n\n{backup_path}\n\n"
                f"Dateigröße: {filesize_kb:.1f} KB"
            )
            self._toast("Backup erfolgreich erstellt.", "success")
        else:
            # Fehlerhaftes Backup löschen
            os.remove(backup_path)
            QtWidgets.QMessageBox.warning(
                self, "Warnung",
                "Backup wurde erstellt, aber die Verifikation ist fehlgeschlagen.\n"
                "Das Backup wurde nicht gespeichert."
            )

    except Exception as e:
        QtWidgets.QMessageBox.critical(
            self, "Fehler", f"Backup konnte nicht erstellt werden:\n\n{str(e)}"
        )
        print(f"✗ Backup-Fehler: {e}")
        import traceback
        traceback.print_exc()


def browse_restore_file(self):
    """Backup-Datei zum Wiederherstellen auswählen"""
    file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
        self,
        "Backup-Datei auswählen",
        self.backup_path_input.text(),
        "Datenbank-Dateien (*.db);;Alle Dateien (*)"
    )

    if file_path:
        self.restore_path_input.setText(file_path)
        self.btn_restore_backup.setEnabled(True)


def restore_backup(self):
    """Backup zurückspielen - OHNE Dateien zu löschen (überschreiben stattdessen)

    Issue #7: Die schwere Arbeit (WAL-Checkpoint, File-Copy, Verifikation)
    läuft im UI-Thread, aber ``time.sleep`` wurde durch ``QApplication.
    processEvents()``-Polling ersetzt, damit die UI responsive bleibt.
    Für eine vollständige Auslagerung in einen Worker-Thread siehe
    ``BackupRestoreRunner`` (core/backup_worker.py) — das ist der
    Migrationspfad, falls der Restore jemals >5 Sekunden braucht.
    """
    if self._is_read_only_mode():
        QtWidgets.QMessageBox.warning(self, "Nur-Lesen Modus", "Backup-Wiederherstellung ist nur mit Schreibzugriff möglich.")
        return
    restore_file = self.restore_path_input.text().strip()

    if not restore_file or not os.path.exists(restore_file):
        QtWidgets.QMessageBox.warning(self, "Fehler", "Bitte eine gültige Backup-Datei auswählen.")
        return

    # Backup-Info anzeigen
    backup_size = os.path.getsize(restore_file) / 1024
    backup_time = datetime.fromtimestamp(os.path.getmtime(restore_file))
    current_size = os.path.getsize(self.db.path) / 1024

    # Backup verifizieren
    backup_verified = self._verify_backup(restore_file)
    verify_text = "Verifiziert" if backup_verified else "⚠ Nicht verifiziert (möglicherweise beschädigt)"

    if not backup_verified:
        reply = QtWidgets.QMessageBox.warning(
            self,
            "Warnung",
            "Die Backup-Datei konnte nicht verifiziert werden.\n"
            "Möglicherweise ist sie beschädigt.\n\n"
            "Trotzdem fortfahren?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

    # Bestätigung anfordern
    info_msg = (
        f"ACHTUNG: Alle aktuellen Daten werden überschrieben!\n\n"
        f"Backup-Datei: {os.path.basename(restore_file)}\n"
        f"Backup-Datum: {backup_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Backup-Größe: {backup_size:.1f} KB\n"
        f"Status: {verify_text}\n\n"
        f"Aktuelle DB-Größe: {current_size:.1f} KB\n\n"
        f"Ein Notfall-Backup wird vor dem Restore erstellt.\n\n"
        f"Möchten Sie fortfahren?"
    )

    reply = QtWidgets.QMessageBox.question(
        self,
        "Backup wiederherstellen",
        info_msg,
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        QtWidgets.QMessageBox.No
    )

    if reply != QtWidgets.QMessageBox.Yes:
        return

    emergency_backup = None

    try:
        logger.info("=" * 50)
        logger.info("BACKUP-WIEDERHERSTELLUNG GESTARTET")
        logger.info("=" * 50)

        # 1. WAL-Checkpoint
        logger.info("1. WAL-Checkpoint wird durchgeführt...")
        try:
            result = self.db.cur.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            logger.info("   WAL-Checkpoint: %s", result)
            self.db.conn.commit()
        except Exception as e:
            logger.warning("   WAL-Checkpoint Fehler: %s", e)

        # 2. Cursor und Connection explizit schließen
        logger.info("2. Datenbank wird geschlossen...")
        try:
            if hasattr(self.db, 'cur') and self.db.cur:
                self.db.cur.close()
                self.db.cur = None
                logger.info("   Cursor geschlossen")
        except Exception as e:
            logger.warning("   Cursor-Fehler: %s", e)

        try:
            if hasattr(self.db, 'conn') and self.db.conn:
                self.db.conn.close()
                self.db.conn = None
                logger.info("   Connection geschlossen")
        except Exception as e:
            logger.warning("   Connection-Fehler: %s", e)

        # 3. Garbage Collection erzwingen
        import gc
        gc.collect()
        logger.info("   Garbage Collection durchgeführt")

        # 4. Pause für Windows File-System — ABER UI-responsive via processEvents
        logger.info("3. Warte auf File-System-Freigabe...")
        self._busy_sleep(2.0)  # 2 Sek warten, aber UI verarbeitet Events

        # 5. Notfall-Backup der aktuellen DB erstellen
        logger.info("4. Notfall-Backup wird erstellt...")
        emergency_backup = self.db.path + ".before_restore"
        if os.path.exists(self.db.path):
            # Altes Notfall-Backup löschen falls vorhanden
            if os.path.exists(emergency_backup):
                try:
                    os.remove(emergency_backup)
                except Exception as exc:
                    logger.warning("   Konnte altes Notfall-Backup nicht löschen: %s", exc)
            shutil.copy2(self.db.path, emergency_backup)
            logger.info("   Gesichert nach: %s", emergency_backup)

        # 6. WAL/SHM-Dateien löschen (diese MÜSSEN weg)
        logger.info("5. WAL/SHM-Dateien werden gelöscht...")
        wal_file = self.db.path + "-wal"
        shm_file = self.db.path + "-shm"
        journal_file = self.db.path + "-journal"

        for db_file in [wal_file, shm_file, journal_file]:
            if os.path.exists(db_file):
                _deleted = False
                for attempt in range(5):
                    try:
                        os.remove(db_file)
                        logger.info("   Gelöscht: %s", os.path.basename(db_file))
                        _deleted = True
                        break
                    except PermissionError:
                        if attempt < 4:
                            logger.warning("   Versuch %d/5: Warte...", attempt + 1)
                            self._busy_sleep(1.0)
                        else:
                            logger.warning(
                                "   Konnte nicht gelöscht werden (wird beim Restore überschrieben): %s",
                                os.path.basename(db_file),
                            )
                    except Exception as e:
                        logger.warning("   Fehler: %s", e)
                        break

        # 7. Hauptdatenbank ÜBERSCHREIBEN (nicht löschen!)
        logger.info("6. Backup wird wiederhergestellt (überschreibt alte Datei)...")

        # Mehrere Versuche zum Überschreiben
        restored = False
        restored_size = 0.0
        for attempt in range(10):
            try:
                shutil.copy2(restore_file, self.db.path)
                restored_size = os.path.getsize(self.db.path) / 1024
                logger.info("   Wiederhergestellt: %.1f KB", restored_size)
                restored = True
                break
            except PermissionError:
                if attempt < 9:
                    logger.warning("   Versuch %d/10: Datei noch gesperrt, warte...", attempt + 1)
                    self._busy_sleep(1.0)
                else:
                    raise Exception("Datei konnte nach 10 Versuchen nicht überschrieben werden!")
            except Exception as e:
                raise Exception(f"Fehler beim Überschreiben: {e}")

        if not restored:
            raise Exception("Restore fehlgeschlagen!")

        # 8. Verifizieren
        logger.info("7. Überprüfung...")
        if os.path.exists(self.db.path):
            logger.info("   Datei existiert: %s", self.db.path)
            if self._verify_backup(self.db.path):
                logger.info("   Datenbank-Integrität OK")
            else:
                logger.warning("   Integritäts-Check fehlgeschlagen")
        else:
            raise Exception("Wiederhergestellte Datei existiert nicht!")

        logger.info("=" * 50)
        logger.info("BACKUP-WIEDERHERSTELLUNG ABGESCHLOSSEN")
        logger.info("=" * 50)

        QtWidgets.QMessageBox.information(
            self,
            "✅ Wiederherstellung erfolgreich",
            f"Das Backup wurde erfolgreich wiederhergestellt.\n\n"
            f"Wiederhergestellt: {restored_size:.1f} KB\n"
            f"Original Backup: {backup_size:.1f} KB\n\n"
            f"Notfall-Backup: {emergency_backup}\n\n"
            f"Die Anwendung wird jetzt neu gestartet."
        )
        self._toast("Backup erfolgreich wiederhergestellt.", "success")

        # 9. Anwendung neu starten (im UI-Thread — Worker kann den Prozess nicht ersetzen)
        self.close()
        QtWidgets.QApplication.quit()
        os.execl(sys.executable, sys.executable, *sys.argv)  # nosec B606: self-restart without shell

    except Exception as e:
        logger.exception("FEHLER beim Restore: %s", e)

        # Bei Fehler: Datenbank wieder öffnen versuchen
        try:
            self.db.conn = sqlite3.connect(self.db.path, check_same_thread=False)
            self.db.cur = self.db.conn.cursor()
            logger.info("   Datenbankverbindung wiederhergestellt")
        except Exception as reconn_err:
            logger.error("   Verbindung konnte nicht wiederhergestellt werden: %s", reconn_err)

        error_msg = f"Backup-Wiederherstellung fehlgeschlagen:\n\n{str(e)}"
        if emergency_backup:
            error_msg += f"\n\nDie ursprüngliche Datenbank wurde gesichert unter:\n{emergency_backup}"
        error_msg += "\n\nPrüfen Sie die Konsole für Details!"

        QtWidgets.QMessageBox.critical(self, "❌ Fehler", error_msg)


def _busy_sleep(self, seconds: float) -> None:
    """Wait without pumping the event loop (Issue #114).

    Backup IO belongs in ``core/backup_worker.py``. A nested
    ``processEvents`` loop here allowed re-entrant Restore clicks.
    """
    time.sleep(seconds)


def _verify_backup(self, backup_path):
    """Verifiziert die Integrität einer Backup-Datei"""
    try:
        import sqlite3
        conn = sqlite3.connect(backup_path, timeout=10)
        result = conn.cursor().execute("PRAGMA integrity_check").fetchone()
        conn.close()
        return result[0] == "ok"
    except Exception as e:
        print(f"⚠ Backup-Verifikation fehlgeschlagen: {e}")
        return False


def _rotate_backups(self, backup_dir, max_backups=10):
    """Löscht alte Backups, behält nur die neuesten"""
    try:
        # Alle backup_*.db Dateien finden
        import glob
        backups = glob.glob(os.path.join(backup_dir, "backup_*.db"))

        # Nach Änderungsdatum sortieren (neueste zuerst)
        backups.sort(key=lambda x: os.path.getmtime(x), reverse=True)

        # Alte Backups löschen
        deleted_count = 0
        for old_backup in backups[max_backups:]:
            try:
                os.remove(old_backup)
                deleted_count += 1
                print(f"   Altes Backup gelöscht: {os.path.basename(old_backup)}")
            except Exception as e:
                print(f"   ⚠ Konnte {os.path.basename(old_backup)} nicht löschen: {e}")

        if deleted_count > 0:
            print(f"   {deleted_count} alte(s) Backup(s) gelöscht")

    except Exception as e:
        print(f"⚠ Backup-Rotation fehlgeschlagen: {e}")


def check_auto_backup(self):
    """Prüft und erstellt automatisches Backup beim Start"""
    if self._is_read_only_mode():
        return
    if not self.load_auto_backup_setting():
        print("Auto-Backup ist deaktiviert")
        return

    try:
        # Prüfen, ob heute bereits ein Backup erstellt wurde
        result = self.db.cur.execute(
            "SELECT wert FROM einstellungen WHERE schluessel = 'letztes_backup'"
        ).fetchone()

        heute = datetime.now().strftime("%Y-%m-%d")

        if result and result[0] == heute:
            print(f"Heute bereits ein Backup erstellt: {heute}")
            return

        # Auto-Backup erstellen
        backup_dir = self.get_default_backup_path()
        os.makedirs(backup_dir, exist_ok=True)

        # WAL-Checkpoint
        try:
            self.db.cur.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self.db.conn.commit()
        except Exception as exc:
            print(f"WAL-Checkpoint fehlgeschlagen (ignoriert): {exc}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"auto_backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)

        shutil.copy2(self.db.path, backup_path)

        # Datum speichern
        self.db.cur.execute("""
            INSERT OR REPLACE INTO einstellungen (schluessel, wert)
            VALUES ('letztes_backup', ?)
        """, (heute,))
        self.db.conn.commit()

        print(f"✅ Auto-Backup erstellt: {backup_path}")

        # Alte Auto-Backups aufräumen
        self._rotate_backups(backup_dir, max_backups=10)

    except Exception as e:
        print(f"Auto-Backup fehlgeschlagen: {e}")


def load_auto_backup_setting(self):
    """Lädt die Auto-Backup-Einstellung"""
    try:
        result = self.db.cur.execute(
            "SELECT wert FROM einstellungen WHERE schluessel = 'auto_backup'"
        ).fetchone()

        if result:
            return result[0] == '1'
        return False
    except Exception as e:
        print(f"Fehler beim Laden der Auto-Backup-Einstellung: {e}")
        return False


def save_auto_backup_setting_from_bool(self, checked):
    """Speichert die Auto-Backup-Einstellung (über toggled-Signal)"""
    if self._is_read_only_mode():
        return
    try:
        self.db.cur.execute("""
            INSERT OR REPLACE INTO einstellungen (schluessel, wert)
            VALUES ('auto_backup', ?)
        """, ('1' if checked else '0',))
        self.db.conn.commit()

        print(f"✅ Auto-Backup gespeichert: {'aktiviert' if checked else 'deaktiviert'}")
    except Exception as e:
        print(f"❌ Fehler beim Speichern: {e}")

