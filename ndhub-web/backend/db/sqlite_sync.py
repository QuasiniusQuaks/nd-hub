"""SQLite repository mixins (Issue #110)."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

ALLOWED_MOVEMENT_TYPES = {"Zugang", "Abgang", "Vernichtung"}


class SqliteSyncMixin:
    def log_audit(
        self,
        username: str,
        action: str,
        resource_type: str,
        resource_id: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> int:
        safe_username = (username or "").strip() or "unknown"
        safe_action = (action or "").strip()
        safe_resource = (resource_type or "").strip()
        if not safe_action:
            raise ValueError("Audit action darf nicht leer sein.")
        if not safe_resource:
            raise ValueError("Audit resource_type darf nicht leer sein.")
        details_json = json.dumps(details or {}, ensure_ascii=True)
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO api_audit_log (
                    timestamp, username, action, resource_type, resource_id, details
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    safe_username,
                    safe_action,
                    safe_resource,
                    int(resource_id) if resource_id is not None else None,
                    details_json,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def list_audit_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        q: str = "",
        action: str = "",
        resource_type: str = "",
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 500))
        safe_offset = max(0, int(offset))
        like = f"%{(q or '').strip()}%"
        safe_action = (action or "").strip()
        safe_resource = (resource_type or "").strip()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, timestamp, username, action, resource_type, resource_id, details
                FROM api_audit_log
                WHERE (? = '%%' OR
                      COALESCE(username, '') LIKE ? OR
                      COALESCE(details, '') LIKE ?)
                  AND (? = '' OR action = ?)
                  AND (? = '' OR resource_type = ?)
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (
                    like,
                    like,
                    like,
                    safe_action,
                    safe_action,
                    safe_resource,
                    safe_resource,
                    safe_limit,
                    safe_offset,
                ),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_sync_batch_result(self, batch_id: str) -> dict[str, Any] | None:
        safe_batch = (batch_id or "").strip()
        if not safe_batch:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT result_json FROM sync_push_batches WHERE batch_id = ?",
                (safe_batch,),
            ).fetchone()
        if not row:
            return None
        raw = row["result_json"] if isinstance(row, sqlite3.Row) else row[0]
        if not raw:
            return None
        try:
            payload = json.loads(str(raw))
            return payload if isinstance(payload, dict) else None
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    def save_sync_batch_result(self, batch_id: str, username: str, result: dict[str, Any]) -> None:
        safe_batch = (batch_id or "").strip()
        if not safe_batch:
            raise ValueError("batch_id darf nicht leer sein.")
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        result_json = json.dumps(result or {}, ensure_ascii=True)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sync_push_batches (batch_id, username, received_at, result_json)
                VALUES (?, ?, ?, ?)
                """,
                (safe_batch, (username or "").strip() or "unknown", timestamp, result_json),
            )
            conn.commit()

    def get_import_batch_result(self, batch_id: str) -> dict[str, Any] | None:
        safe_batch = (batch_id or "").strip()
        if not safe_batch:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT result_json FROM import_batches WHERE batch_id = ?",
                (safe_batch,),
            ).fetchone()
        if not row:
            return None
        raw = row["result_json"] if isinstance(row, sqlite3.Row) else row[0]
        if not raw:
            return None
        try:
            payload = json.loads(str(raw))
            return payload if isinstance(payload, dict) else None
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    def save_import_batch_result(self, batch_id: str, username: str, result: dict[str, Any]) -> None:
        safe_batch = (batch_id or "").strip()
        if not safe_batch:
            raise ValueError("batch_id darf nicht leer sein.")
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        result_json = json.dumps(result or {}, ensure_ascii=True)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO import_batches (batch_id, username, received_at, result_json)
                VALUES (?, ?, ?, ?)
                """,
                (safe_batch, (username or "").strip() or "unknown", timestamp, result_json),
            )
            conn.commit()

    def list_sync_audit_changes(
        self,
        cursor: int = 0,
        entities: list[str] | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        safe_cursor = max(0, int(cursor))
        safe_limit = max(1, min(int(limit), 1000))
        safe_entities = sorted({str(item).strip() for item in (entities or []) if str(item).strip()})
        with self._connect() as conn:
            if safe_entities:
                placeholders = ",".join("?" for _ in safe_entities)
                sql = "".join(
                    [
                        """
                        SELECT id, timestamp, username, action, resource_type, resource_id, details
                        FROM api_audit_log
                        WHERE id > ? AND resource_type IN (""",
                        placeholders,
                        """)
                        ORDER BY id ASC
                        LIMIT ?
                        """,
                    ]
                )
                rows = conn.execute(
                    sql,
                    (safe_cursor, *safe_entities, safe_limit + 1),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, timestamp, username, action, resource_type, resource_id, details
                    FROM api_audit_log
                    WHERE id > ?
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    (safe_cursor, safe_limit + 1),
                ).fetchall()

        has_more = len(rows) > safe_limit
        sliced = rows[:safe_limit]
        changes: list[dict[str, Any]] = []
        next_cursor = safe_cursor
        for row in sliced:
            row_dict = dict(row)
            next_cursor = int(row_dict["id"])
            details_text = row_dict.get("details")
            details: dict[str, Any] | None = None
            if isinstance(details_text, str) and details_text.strip():
                try:
                    parsed = json.loads(details_text)
                    if isinstance(parsed, dict):
                        details = parsed
                except (TypeError, ValueError, json.JSONDecodeError):
                    details = None
            changes.append(
                {
                    "change_id": int(row_dict["id"]),
                    "changed_at": str(row_dict.get("timestamp") or ""),
                    "actor": str(row_dict.get("username") or ""),
                    "operation": str(row_dict.get("action") or ""),
                    "entity": str(row_dict.get("resource_type") or ""),
                    "entity_id": row_dict.get("resource_id"),
                    "details": details,
                }
            )
        return {
            "changes": changes,
            "next_cursor": str(next_cursor),
            "has_more": has_more,
        }

    def get_latest_audit_cursor(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COALESCE(MAX(id), 0) AS max_id FROM api_audit_log").fetchone()
        if not row:
            return 0
        if isinstance(row, sqlite3.Row):
            return int(row["max_id"] or 0)
        return int(row[0] or 0)

    def get_sync_ops_stats(self) -> dict[str, Any]:
        with self._connect() as conn:
            batch_count_row = conn.execute("SELECT COUNT(*) AS c FROM sync_push_batches").fetchone()
            latest_batch_row = conn.execute(
                "SELECT batch_id, username, received_at FROM sync_push_batches ORDER BY received_at DESC LIMIT 1"
            ).fetchone()
            sync_change_row = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM api_audit_log
                WHERE COALESCE(details, '') LIKE '%"source": "sync_push"%'
                """
            ).fetchone()
            pending_outbox_row = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM sync_push_batches
                WHERE COALESCE(result_json, '') LIKE '%"deduplicated": false%'
                """
            ).fetchone()

        latest_batch = dict(latest_batch_row) if latest_batch_row else None
        return {
            "total_push_batches": int((batch_count_row["c"] if batch_count_row else 0) or 0),
            "total_audit_sync_changes": int((sync_change_row["c"] if sync_change_row else 0) or 0),
            "latest_push_batch": latest_batch,
            "non_deduplicated_batch_rows": int((pending_outbox_row["c"] if pending_outbox_row else 0) or 0),
            "latest_audit_cursor": self.get_latest_audit_cursor(),
        }
