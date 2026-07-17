"""Analytics Saved Views & Custom-SQL (Issue #66).

Extrahiert aus ``db_manager.Database`` — reine LOC-Trennung.
``Database`` mischt ``AnalyticsSavedMixin`` ein.
"""
from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)


class AnalyticsSavedMixin:
    """Saved Views und Custom-SQL CRUD/Run (Issue #66 Phase 1).

    Erwartet: ``self.cur``, ``self.conn`` (sqlite3).
    """


    # ─────────────────────────────────────────────────────────────────────
    # Saved Views CRUD (Issue #42 Phase 2)
    # ─────────────────────────────────────────────────────────────────────

    def save_analytics_view(self, name: str, filter_json: str) -> bool:
        """Speichert eine Analytics-View (Filter-Konfiguration als JSON).

        Args:
            name: Eindeutiger Name für die View.
            filter_json: JSON-String mit Filter-Konfiguration
                         (depot_ids, praeparat_ids, date_range_days, compare_mode).

        Returns:
            True bei Erfolg, False bei Fehler.
        """
        try:
            self.cur.execute(
                "INSERT INTO analytics_saved_views (name, filter_json) VALUES (?, ?)",
                (name, filter_json),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Name existiert bereits → upsert
            self.cur.execute(
                "UPDATE analytics_saved_views SET filter_json = ?, created_at = datetime('now', 'localtime') WHERE name = ?",
                (filter_json, name),
            )
            self.conn.commit()
            return True
        except Exception:
            logger.exception("save_analytics_view fehlgeschlagen")
            return False

    def get_analytics_views(self) -> list[sqlite3.Row]:
        """Lädt alle gespeicherten Analytics-Views.

        Returns:
            Liste von Rows mit id, name, filter_json, created_at (neueste zuerst).
        """
        sql = """
            SELECT id, name, filter_json, created_at
            FROM analytics_saved_views
            ORDER BY created_at DESC
        """
        return self.cur.execute(sql).fetchall()

    def get_analytics_view(self, name: str) -> sqlite3.Row | None:
        """Lädt eine spezifische Analytics-View nach Namen.

        Returns:
            Row oder None wenn nicht gefunden.
        """
        return self.cur.execute(
            "SELECT id, name, filter_json, created_at FROM analytics_saved_views WHERE name = ?",
            (name,),
        ).fetchone()

    def delete_analytics_view(self, name: str) -> bool:
        """Löscht eine gespeicherte Analytics-View.

        Returns:
            True bei Erfolg, False wenn nicht gefunden.
        """
        self.cur.execute(
            "DELETE FROM analytics_saved_views WHERE name = ?", (name,)
        )
        self.conn.commit()
        return self.cur.rowcount > 0

    # ─────────────────────────────────────────────────────────────────────
    # Saved Queries CRUD (Issue #42 Phase 4 — Custom SQL)
    # ─────────────────────────────────────────────────────────────────────

    def save_query(self, name: str, sql_text: str, description: str = "") -> bool:
        """Speichert eine Custom-SQL-Query (Upsert).

        Args:
            name: Eindeutiger Name.
            sql_text: SQL-Statement (nur SELECT erlaubt).
            description: Optionale Beschreibung.

        Returns:
            True bei Erfolg.
        """
        # Security: nur SELECT-Statements erlauben
        stripped = sql_text.strip().upper()
        if not stripped.startswith("SELECT") and not stripped.startswith("WITH"):
            logger.warning("save_query: nur SELECT/WITH erlaubt, abgelehnt: %s", name)
            return False

        try:
            self.cur.execute(
                "INSERT INTO analytics_saved_queries (name, sql_text, description) VALUES (?, ?, ?)",
                (name, sql_text, description),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            self.cur.execute(
                "UPDATE analytics_saved_queries SET sql_text = ?, description = ? WHERE name = ?",
                (sql_text, description, name),
            )
            self.conn.commit()
            return True
        except Exception:
            logger.exception("save_query fehlgeschlagen")
            return False

    def get_saved_queries(self) -> list[sqlite3.Row]:
        """Lädt alle gespeicherten Queries."""
        return self.cur.execute(
            "SELECT id, name, sql_text, description, created_at, last_run "
            "FROM analytics_saved_queries ORDER BY created_at DESC"
        ).fetchall()

    def get_saved_query(self, name: str) -> sqlite3.Row | None:
        """Lädt eine spezifische Query nach Namen."""
        return self.cur.execute(
            "SELECT id, name, sql_text, description, created_at, last_run "
            "FROM analytics_saved_queries WHERE name = ?",
            (name,),
        ).fetchone()

    def delete_saved_query(self, name: str) -> bool:
        """Löscht eine gespeicherte Query."""
        self.cur.execute(
            "DELETE FROM analytics_saved_queries WHERE name = ?", (name,)
        )
        self.conn.commit()
        return self.cur.rowcount > 0

    def run_saved_query(self, name: str) -> tuple[list, list[str]]:
        """Führt eine gespeicherte Query aus.

        Returns:
            Tuple (rows, column_names). Bei Fehler: ([], []).
        """
        row = self.get_saved_query(name)
        if row is None:
            return [], []

        sql_text = row["sql_text"]
        # Security-Check: nur SELECT
        if not sql_text.strip().upper().startswith(("SELECT", "WITH")):
            return [], []

        try:
            cursor = self.cur.execute(sql_text)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            # last_run aktualisieren
            self.cur.execute(
                "UPDATE analytics_saved_queries SET last_run = datetime('now', 'localtime') WHERE name = ?",
                (name,),
            )
            self.conn.commit()
            return rows, columns
        except Exception:
            logger.exception("run_saved_query fehlgeschlagen: %s", name)
            return [], []
