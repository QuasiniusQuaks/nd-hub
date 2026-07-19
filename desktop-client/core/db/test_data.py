"""Test-Daten zurücksetzen. Issue #66 Phase 4."""
from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)


class TestDataMixin:
    """reset_test_data. Erwartet: self.cur, self.conn, _clear_lookup_caches."""

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

