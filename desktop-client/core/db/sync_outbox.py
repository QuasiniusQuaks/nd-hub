"""Sync-Outbox und Write-Lease (Issue #66 Phase 2).

LOC-Split aus ``db_manager.Database``. API bleibt ``db.*`` via Mixin-MRO.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class SyncOutboxMixin:
    """Outbox-CRUD, ID-Remap und Write-Lease. Issue #66.

    Erwartet: ``self.cur``, ``self.conn``, ``self.session_id``,
    ``self.write_lease_owner``, ``set_query_only``, ``_clear_lookup_caches``.
    """

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

