"""BackupManager - Backup-Erstellung, Rotation und Wiederherstellung."""
import os
import sqlite3
from datetime import datetime
from pathlib import Path


class BackupManager:
    def __init__(self, db_path, backup_folder, max_backups=10):
        self.db_path = Path(db_path)
        self.backup_folder = Path(backup_folder)
        self.max_backups = max_backups
        self.backup_folder.mkdir(parents=True, exist_ok=True)

    def create_backup(self, db_connection, db_path):
        """Erstellt ein Backup der Datenbank - INKL. WAL!"""
        try:
            # 1. Zeitstempel
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.db"
            backup_path = self.backup_folder / backup_filename
            
            # 2. Natives SQLite-Backup durchführen
            # transaktionssicher, WAL-safe und blockiert nicht!
            with sqlite3.connect(backup_path) as bck_conn:
                db_connection.backup(bck_conn)
            
            # 3. Backup verifizieren
            if self._verify_backup(backup_path):
                print(f"Backup erstellt und verifiziert: {backup_path}")
                
                # 4. Alte Backups rotieren
                self._rotate_backups()
                
                filesize_kb = os.path.getsize(backup_path) / 1024
                return True, str(backup_path), filesize_kb
            else:
                backup_path.unlink()  # Fehlerhaftes Backup löschen
                return False, "Backup-Verifikation fehlgeschlagen", 0
            
        except Exception as e:
            print(f"✗ Backup-Fehler: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e), 0

    def _verify_backup(self, path):
        """Verifiziert die Integrität einer Backup-Datei"""
        try:
            conn = sqlite3.connect(str(path), timeout=10)
            result = conn.cursor().execute("PRAGMA integrity_check").fetchone()
            conn.close()
            return result[0] == "ok"
        except Exception as e:
            print(f"⚠ Verifikation fehlgeschlagen: {e}")
            return False

    def _rotate_backups(self):
        """Löscht alte Backups, behält nur max_backups neueste"""
        backups = sorted(self.backup_folder.glob("backup_*.db"), 
                        key=lambda p: p.stat().st_mtime, reverse=True)
        
        deleted_count = 0
        for old in backups[self.max_backups:]:
            try:
                old.unlink()
                deleted_count += 1
                print(f"   Altes Backup gelöscht: {old.name}")
            except Exception as e:
                print(f"   ⚠ Konnte {old.name} nicht löschen: {e}")
        
        if deleted_count > 0:
            print(f"   {deleted_count} alte(s) Backup(s) gelöscht")

    def list_backups(self):
        """Listet alle verfügbaren Backups auf"""
        backups = []
        for p in sorted(self.backup_folder.glob("backup_*.db"), 
                       key=lambda x: x.stat().st_mtime, reverse=True):
            backups.append({
                'path': p,
                'timestamp': datetime.fromtimestamp(p.stat().st_mtime),
                'size': p.stat().st_size,
                'name': p.name
            })
        return backups
    
    def get_backup_info(self, backup_path):
        """Gibt Informationen über eine Backup-Datei zurück"""
        try:
            stat = os.stat(backup_path)
            return {
                'size_kb': stat.st_size / 1024,
                'timestamp': datetime.fromtimestamp(stat.st_mtime),
                'exists': True,
                'verified': self._verify_backup(backup_path)
            }
        except Exception as e:
            return {
                'size_kb': 0,
                'timestamp': None,
                'exists': False,
                'verified': False,
                'error': str(e)
            }
