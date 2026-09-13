"""MariaDB repository mixins (Issue #110)."""

from __future__ import annotations

import json
import logging
from typing import Any

ALLOWED_MOVEMENT_TYPES = {"Zugang", "Abgang", "Vernichtung"}
logger = logging.getLogger(__name__)


class MariadbSyncMixin:
    def log_audit(
        self,
        username: str,
        action: str,
        resource_type: str,
        resource_id: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO api_audit_log (timestamp, username, action, resource_type, resource_id, details)
                    VALUES (UTC_TIMESTAMP(), %s, %s, %s, %s, %s)
                    """,
                    (
                        (username or "").strip() or "system",
                        (action or "").strip(),
                        (resource_type or "").strip(),
                        resource_id,
                        self._to_json(details),
                    ),
                )
                conn.commit()
        self._mirror_write("log_audit", username, action, resource_type, resource_id, details)

    def list_audit_logs(
        self,
        q: str = "",
        action: str = "",
        resource_type: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 300))
        safe_offset = max(0, int(offset))
        like = f"%{(q or '').strip()}%"
        action_filter = (action or "").strip()
        resource_filter = (resource_type or "").strip()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, timestamp, username, action, resource_type, resource_id, details
                    FROM api_audit_log
                    WHERE
                        (%s = '' OR action = %s) AND
                        (%s = '' OR resource_type = %s) AND
                        (
                            %s = '%%' OR
                            username LIKE %s OR
                            action LIKE %s OR
                            resource_type LIKE %s OR
                            COALESCE(details, '') LIKE %s
                        )
                    ORDER BY id DESC
                    LIMIT %s OFFSET %s
                    """,
                    (
                        action_filter,
                        action_filter,
                        resource_filter,
                        resource_filter,
                        like,
                        like,
                        like,
                        like,
                        like,
                        safe_limit,
                        safe_offset,
                    ),
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_sync_batch_result(self, batch_id: str) -> dict[str, Any] | None:
        safe_batch = (batch_id or "").strip()
        if not safe_batch:
            return None
        self._ensure_sync_batch_table()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT result_json FROM sync_push_batches WHERE batch_id = %s", (safe_batch,))
                row = cur.fetchone()
        if not row:
            return None
        raw = row.get("result_json")
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
        self._ensure_sync_batch_table()
        result_json = json.dumps(result or {}, ensure_ascii=False)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sync_push_batches (batch_id, username, received_at, result_json)
                    VALUES (%s, %s, UTC_TIMESTAMP(), %s)
                    ON DUPLICATE KEY UPDATE
                        username = VALUES(username),
                        received_at = UTC_TIMESTAMP(),
                        result_json = VALUES(result_json)
                    """,
                    (safe_batch, (username or "").strip() or "unknown", result_json),
                )
                conn.commit()

    def get_import_batch_result(self, batch_id: str) -> dict[str, Any] | None:
        safe_batch = (batch_id or "").strip()
        if not safe_batch:
            return None
        self._ensure_import_batch_table()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT result_json FROM import_batches WHERE batch_id = %s", (safe_batch,))
                row = cur.fetchone()
        if not row:
            return None
        raw = row.get("result_json")
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
        self._ensure_import_batch_table()
        result_json = json.dumps(result or {}, ensure_ascii=False)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT IGNORE INTO import_batches (batch_id, username, received_at, result_json)
                    VALUES (%s, %s, UTC_TIMESTAMP(), %s)
                    """,
                    (safe_batch, (username or "").strip() or "unknown", result_json),
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
            with conn.cursor() as cur:
                if safe_entities:
                    placeholders = ", ".join(["%s"] * len(safe_entities))
                    sql = "".join(
                        [
                            """
                            SELECT id, timestamp, username, action, resource_type, resource_id, details
                            FROM api_audit_log
                            WHERE id > %s AND resource_type IN (""",
                            placeholders,
                            """)
                            ORDER BY id ASC
                            LIMIT %s
                            """,
                        ]
                    )
                    cur.execute(sql, (safe_cursor, *safe_entities, safe_limit + 1))
                else:
                    cur.execute(
                        """
                        SELECT id, timestamp, username, action, resource_type, resource_id, details
                        FROM api_audit_log
                        WHERE id > %s
                        ORDER BY id ASC
                        LIMIT %s
                        """,
                        (safe_cursor, safe_limit + 1),
                    )
                rows = cur.fetchall()
        has_more = len(rows) > safe_limit
        sliced = rows[:safe_limit]
        changes: list[dict[str, Any]] = []
        next_cursor = safe_cursor
        for row in sliced:
            next_cursor = int(row.get("id") or safe_cursor)
            details_text = row.get("details")
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
                    "change_id": int(row.get("id") or 0),
                    "changed_at": str(row.get("timestamp") or ""),
                    "actor": str(row.get("username") or ""),
                    "operation": str(row.get("action") or ""),
                    "entity": str(row.get("resource_type") or ""),
                    "entity_id": row.get("resource_id"),
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
            with conn.cursor() as cur:
                cur.execute("SELECT COALESCE(MAX(id), 0) AS max_id FROM api_audit_log")
                row = cur.fetchone()
        return int((row or {}).get("max_id") or 0)

    def get_sync_ops_stats(self) -> dict[str, Any]:
        self._ensure_sync_batch_table()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM sync_push_batches")
                batch_count_row = cur.fetchone() or {}
                cur.execute(
                    """
                    SELECT batch_id, username, received_at
                    FROM sync_push_batches
                    ORDER BY received_at DESC
                    LIMIT 1
                    """
                )
                latest_batch_row = cur.fetchone()
                cur.execute(
                    """
                    SELECT COUNT(*) AS c
                    FROM api_audit_log
                    WHERE COALESCE(details, '') LIKE %s
                    """,
                    ('%"source": "sync_push"%',),
                )
                sync_change_row = cur.fetchone() or {}
                cur.execute(
                    """
                    SELECT COUNT(*) AS c
                    FROM sync_push_batches
                    WHERE COALESCE(result_json, '') LIKE %s
                    """,
                    ('%"deduplicated": false%',),
                )
                pending_outbox_row = cur.fetchone() or {}
        return {
            "total_push_batches": int(batch_count_row.get("c") or 0),
            "total_audit_sync_changes": int(sync_change_row.get("c") or 0),
            "latest_push_batch": dict(latest_batch_row) if latest_batch_row else None,
            "non_deduplicated_batch_rows": int(pending_outbox_row.get("c") or 0),
            "latest_audit_cursor": self.get_latest_audit_cursor(),
        }
