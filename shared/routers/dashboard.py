"""Shared Dashboard overview router (Issues #60/#61)."""

from fastapi import APIRouter, Depends


def create_dashboard_router(
    repository,
    require_permission,
    *,
    normalize_verfall_thresholds,
    enrich_verfall_rows,
    enable_depot_scope: bool = False,
    allowed_depot_ids=None,
) -> APIRouter:
    router = APIRouter(prefix="/dashboard", tags=["dashboard"])

    @router.get("/overview")
    def dashboard_overview(
        critical_days: int = 30,
        warning_days: int = 90,
        attention_days: int = 180,
        session=Depends(require_permission("movements_read")),
    ) -> dict:
        if enable_depot_scope:
            scoped_ids = allowed_depot_ids(session, require_write=False)
            if session.role != "Admin" and not scoped_ids:
                return {
                    "kpis": {"depots": 0, "praeparate": 0, "bewegungen": 0, "kritisch_verfallend": 0},
                    "recent_activity": [],
                    "expiry_preview": [],
                }
        else:
            scoped_ids = None
            _ = session

        safe_critical, safe_warning, safe_attention = normalize_verfall_thresholds(
            critical_days=critical_days,
            warning_days=warning_days,
            attention_days=attention_days,
        )
        payload = repository.get_dashboard_overview(
            limit_activity=8, limit_expiry=8, critical_days=safe_critical
        )
        if enable_depot_scope and session.role != "Admin":
            scoped_set = set(scoped_ids or [])
            payload["recent_activity"] = [
                row for row in payload.get("recent_activity", []) if int(row.get("depot_id") or 0) in scoped_set
            ]
            payload["expiry_preview"] = [
                row for row in payload.get("expiry_preview", []) if int(row.get("depot_id") or 0) in scoped_set
            ]
            payload["kpis"]["depots"] = len(scoped_set)
        payload["expiry_preview"] = enrich_verfall_rows(
            payload.get("expiry_preview", []),
            critical_days=safe_critical,
            warning_days=safe_warning,
            attention_days=safe_attention,
        )
        payload["thresholds"] = {
            "kritisch_tage": safe_critical,
            "warnung_tage": safe_warning,
            "achtung_tage": safe_attention,
        }
        return payload

    return router
