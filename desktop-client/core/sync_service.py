# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from core.config_manager import ConfigManager
from core.data_access_layer import DataAccessRouter, OperatingMode


logger = logging.getLogger("ND-Hub.Sync")


@dataclass
class SyncCycleResult:
    effective_mode: str
    reason: str
    pushed: int = 0
    rejected: int = 0
    conflicts: int = 0
    pulled: int = 0
    skipped: bool = False


class DesktopSyncService:
    """Fuehrt Push/Pull-Zyklen fuer Desktop-Hybrid-Sync aus."""

    def __init__(self, db, config: ConfigManager, router: DataAccessRouter):
        self.db = db
        self.config = config
        self.router = router

    def get_local_outbox_stats(self) -> dict[str, Any]:
        return self.db.get_sync_outbox_stats()

    def retry_conflicts(self, limit: int = 100) -> int:
        return int(self.db.requeue_sync_outbox_conflicts(limit=limit))

    def run_cycle(self, actor_username: str) -> SyncCycleResult:
        effective_mode, reason = self.router.resolve_effective_mode()
        result = SyncCycleResult(effective_mode=effective_mode.value, reason=reason)

        if effective_mode != OperatingMode.HYBRID_SYNC:
            result.skipped = True
            return result

        if self.router.api_client is None:
            result.skipped = True
            result.reason = "Kein API-Client verfügbar."
            return result
        if not (self.router.api_client.config.access_token or "").strip():
            result.skipped = True
            result.reason = "Kein Backend-Token konfiguriert."
            return result

        pending = self.db.list_pending_sync_outbox(limit=200)
        if pending:
            push_stats = self._push_pending_changes(actor_username=actor_username, pending_rows=pending)
            result.pushed = push_stats["accepted"]
            result.rejected = push_stats["rejected"]
            result.conflicts = push_stats["conflicts"]

        pull_stats = self._pull_server_changes()
        result.pulled = pull_stats["pulled"]
        return result

    def _push_pending_changes(self, actor_username: str, pending_rows: list[dict[str, Any]]) -> dict[str, int]:
        index_to_outbox_id: dict[int, int] = {}
        index_to_row: dict[int, dict[str, Any]] = {}
        changes_payload: list[dict[str, Any]] = []
        for idx, row in enumerate(pending_rows):
            index_to_outbox_id[idx] = int(row["id"])
            index_to_row[idx] = row
            changes_payload.append(
                {
                    "entity": row["entity_name"],
                    "operation": row["operation"],
                    "payload": row["payload"],
                    "client_change_id": str(row["id"]),
                }
            )

        batch_id = str(uuid.uuid4())
        try:
            response = self.router.api_client.push_changes(batch_id=batch_id, changes=changes_payload)
        except Exception as exc:
            message = f"Push fehlgeschlagen: {exc}"
            logger.warning(message)
            for row in pending_rows:
                self.db.mark_sync_outbox_retry(int(row["id"]), message)
            return {"accepted": 0, "rejected": len(pending_rows), "conflicts": 0}

        accepted = int(len(response.get("accepted") or []))
        rejected = response.get("rejected") or []
        conflicts = response.get("conflicts") or []

        for entry in response.get("accepted") or []:
            idx = int(entry.get("index", -1))
            outbox_id = index_to_outbox_id.get(idx)
            row = index_to_row.get(idx)
            if row is not None:
                operation = str(row.get("operation") or "").strip().lower()
                if operation == "create":
                    payload = dict(row.get("payload") or {})
                    old_id = int(payload.get("id") or 0)
                    new_id = int(entry.get("server_id") or 0)
                    entity = str(row.get("entity_name") or "")
                    if old_id > 0 and new_id > 0 and old_id != new_id:
                        try:
                            self.db.remap_local_entity_id(entity, old_id, new_id)
                        except Exception as exc:
                            logger.warning(
                                "Lokales ID-Remap fehlgeschlagen: entity=%s old=%s new=%s err=%s",
                                entity,
                                old_id,
                                new_id,
                                exc,
                            )
            if outbox_id is not None:
                self.db.mark_sync_outbox_done(outbox_id)

        for entry in rejected:
            idx = int(entry.get("index", -1))
            outbox_id = index_to_outbox_id.get(idx)
            if outbox_id is not None:
                reason = str(entry.get("reason") or "Sync rejected")
                self.db.mark_sync_outbox_conflict(outbox_id, reason)

        for entry in conflicts:
            idx = int(entry.get("index", -1))
            outbox_id = index_to_outbox_id.get(idx)
            if outbox_id is not None:
                reason = str(entry.get("reason") or "Sync conflict")
                self.db.mark_sync_outbox_conflict(outbox_id, reason)

        logger.info(
            "Sync-Push durchgefuehrt: actor=%s batch=%s accepted=%s rejected=%s conflicts=%s",
            actor_username,
            batch_id,
            accepted,
            len(rejected),
            len(conflicts),
        )
        return {"accepted": accepted, "rejected": len(rejected), "conflicts": len(conflicts)}

    def _pull_server_changes(self) -> dict[str, int]:
        cursor = self.config.get_sync_cursor()
        try:
            response = self.router.api_client.pull_changes(
                cursor=cursor,
                entities=["institutions", "depots", "praeparate", "kontakte", "depot_praeparate", "bewegungen"],
                limit=300,
            )
        except Exception as exc:
            logger.warning("Sync-Pull fehlgeschlagen: %s", exc)
            return {"pulled": 0}

        next_cursor = str(response.get("next_cursor") or cursor)
        changes = response.get("changes") or []
        applied = 0
        if isinstance(changes, list):
            for change in changes:
                if not isinstance(change, dict):
                    continue
                try:
                    changed = self.db.apply_remote_sync_change(
                        entity_name=str(change.get("entity") or ""),
                        operation=str(change.get("operation") or ""),
                        payload=dict(change.get("payload") or {}),
                    )
                    if changed:
                        applied += 1
                except Exception as exc:
                    logger.warning("Sync-Pull Change konnte nicht angewendet werden: %s", exc)
        self.config.set_sync_cursor(next_cursor)
        logger.info("Sync-Pull durchgefuehrt: applied=%s next_cursor=%s", applied, next_cursor)
        return {"pulled": applied}
