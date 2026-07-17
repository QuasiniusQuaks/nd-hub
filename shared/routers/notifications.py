"""Shared Notifications router (Issues #60/#61)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends


def create_notifications_router(
    repository,
    require_permission,
    *,
    normalize_verfall_thresholds,
    enrich_verfall_rows,
    enable_depot_scope: bool = False,
    allowed_depot_ids=None,
) -> APIRouter:
    router = APIRouter(prefix="/notifications", tags=["notifications"])

    @router.get("/verfall")
    def notifications_verfall(
        since: str = "",
        limit: int = 25,
        critical_days: int = 30,
        warning_days: int = 90,
        attention_days: int = 180,
        session=Depends(require_permission("movements_read")),
    ) -> dict:
        now_iso = datetime.now(timezone.utc).isoformat()
        if enable_depot_scope:
            allowed_ids = set(allowed_depot_ids(session, require_write=False))
            if session.role != "Admin" and not allowed_ids:
                return {
                    "since": (since or "").strip() or None,
                    "next_since": now_iso,
                    "rows": [],
                    "counts": {"kritisch": 0, "warnung": 0, "achtung": 0, "gesamt": 0},
                }
        else:
            allowed_ids = None
            _ = session

        safe_critical, safe_warning, safe_attention = normalize_verfall_thresholds(
            critical_days=critical_days,
            warning_days=warning_days,
            attention_days=attention_days,
        )
        rows = repository.list_new_critical_expiry_events(
            since_iso=(since or "").strip() or None,
            limit=limit,
            critical_days=safe_critical,
        )
        if enable_depot_scope and session.role != "Admin":
            rows = [row for row in rows if int(row.get("depot_id") or 0) in allowed_ids]
        enriched_rows = enrich_verfall_rows(rows, safe_critical, safe_warning, safe_attention)
        return {
            "since": (since or "").strip() or None,
            "next_since": now_iso,
            "rows": enriched_rows,
            "counts": {
                "kritisch": int(sum(1 for row in enriched_rows if row["kategorie"] == "kritisch")),
                "warnung": int(sum(1 for row in enriched_rows if row["kategorie"] == "warnung")),
                "achtung": int(sum(1 for row in enriched_rows if row["kategorie"] == "achtung")),
                "gesamt": len(enriched_rows),
            },
        }

    return router
