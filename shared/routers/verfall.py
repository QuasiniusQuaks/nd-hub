"""Shared Verfall overview router (Issues #60/#61)."""

from fastapi import APIRouter, Depends, HTTPException, status


def create_verfall_router(
    repository,
    require_permission,
    *,
    parse_id_list_csv,
    normalize_verfall_thresholds,
    enrich_verfall_rows,
    csv_response,
    enable_depot_scope: bool = False,
    allowed_depot_ids=None,
    scoped_requested_ids=None,
) -> APIRouter:
    router = APIRouter(prefix="/verfall", tags=["verfall"])

    def _resolve_depot_ids(session, safe_perspective: str, selected_ids: list[int]):
        if not enable_depot_scope:
            return selected_ids if safe_perspective == "depot" and selected_ids else None
        if safe_perspective == "depot":
            return scoped_requested_ids(session, selected_ids, require_write=False)
        return allowed_depot_ids(session, require_write=False)

    @router.get("/overview")
    def verfall_overview(
        perspective: str = "depot",
        ids: str = "",
        q: str = "",
        category: str = "alle",
        limit: int = 100,
        offset: int = 0,
        critical_days: int = 30,
        warning_days: int = 90,
        attention_days: int = 180,
        session=Depends(require_permission("movements_read")),
    ) -> dict:
        _ = session
        safe_perspective = (perspective or "").strip().lower()
        if safe_perspective not in {"depot", "praeparat"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungueltige Perspektive.")
        try:
            selected_ids = parse_id_list_csv(ids)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ungueltige IDs: {exc}") from exc
        safe_critical, safe_warning, safe_attention = normalize_verfall_thresholds(
            critical_days=critical_days,
            warning_days=warning_days,
            attention_days=attention_days,
        )
        depot_ids = _resolve_depot_ids(session, safe_perspective, selected_ids)
        if enable_depot_scope and session.role != "Admin" and not depot_ids:
            return {
                "rows": [],
                "total": 0,
                "stats_page": {"kritisch": 0, "warnung": 0, "achtung": 0, "gesamt_menge": 0},
            }
        praeparat_ids = selected_ids if safe_perspective == "praeparat" and selected_ids else None
        rows = repository.list_verfall_items(
            depot_ids=depot_ids or None,
            praeparat_ids=praeparat_ids,
            search_text=q,
            category=category,
            limit=limit,
            offset=offset,
            critical_days=safe_critical,
            warning_days=safe_warning,
            attention_days=safe_attention,
        )
        total = repository.count_verfall_items(
            depot_ids=depot_ids or None,
            praeparat_ids=praeparat_ids,
            search_text=q,
            category=category,
            critical_days=safe_critical,
            warning_days=safe_warning,
            attention_days=safe_attention,
        )
        enriched_rows = enrich_verfall_rows(rows, safe_critical, safe_warning, safe_attention)
        stats = {
            "kritisch": int(sum(1 for row in enriched_rows if row["kategorie"] == "kritisch")),
            "warnung": int(sum(1 for row in enriched_rows if row["kategorie"] == "warnung")),
            "achtung": int(sum(1 for row in enriched_rows if row["kategorie"] == "achtung")),
            "gesamt_menge": int(sum(int(row.get("anzahl") or 0) for row in enriched_rows)),
        }
        return {
            "rows": enriched_rows,
            "total": total,
            "stats_page": stats,
            "thresholds": {
                "kritisch_tage": safe_critical,
                "warnung_tage": safe_warning,
                "achtung_tage": safe_attention,
            },
        }

    @router.get("/overview/export.csv")
    def export_verfall_overview_csv(
        perspective: str = "depot",
        ids: str = "",
        q: str = "",
        category: str = "alle",
        critical_days: int = 30,
        warning_days: int = 90,
        attention_days: int = 180,
        session=Depends(require_permission("movements_read")),
    ):
        _ = session
        safe_perspective = (perspective or "").strip().lower()
        if safe_perspective not in {"depot", "praeparat"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ungueltige Perspektive.")
        try:
            selected_ids = parse_id_list_csv(ids)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ungueltige IDs: {exc}") from exc
        safe_critical, safe_warning, safe_attention = normalize_verfall_thresholds(
            critical_days=critical_days,
            warning_days=warning_days,
            attention_days=attention_days,
        )
        depot_ids = _resolve_depot_ids(session, safe_perspective, selected_ids)
        if enable_depot_scope and session.role != "Admin" and not depot_ids:
            return csv_response("verfall_manager.csv", ["ID"], [])
        praeparat_ids = selected_ids if safe_perspective == "praeparat" and selected_ids else None
        rows = repository.list_verfall_items(
            depot_ids=depot_ids or None,
            praeparat_ids=praeparat_ids,
            search_text=q,
            category=category,
            limit=5000,
            offset=0,
            critical_days=safe_critical,
            warning_days=safe_warning,
            attention_days=safe_attention,
        )
        enriched_rows = enrich_verfall_rows(rows, safe_critical, safe_warning, safe_attention)
        csv_rows = [
            [
                row.get("id"),
                row.get("depot"),
                row.get("praeparat"),
                row.get("charge"),
                row.get("verfall"),
                row.get("tage_bis_verfall"),
                row.get("kategorie"),
                row.get("anzahl"),
            ]
            for row in enriched_rows
        ]
        return csv_response(
            filename="verfall_manager.csv",
            headers=["ID", "Depot", "Praeparat", "Charge", "Verfall", "TageBisVerfall", "Kategorie", "Anzahl"],
            rows=csv_rows,
        )

    return router
