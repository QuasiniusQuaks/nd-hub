"""Web multi-institution routes: onboarding, institutions, map, geo (Issue #60)."""

from typing import Any
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

from fastapi import APIRouter, Depends, HTTPException, status


def create_institutions_router(app, repository, require_permission, get_current_session, OnboardingInstitutionSetupRequest, InstitutionUpsertRequest, _allowed_depot_ids, _require_http_scheme) -> APIRouter:
    router = APIRouter()

    @router.get("/onboarding/status")
    def onboarding_status(session = Depends(require_permission("masterdata_read"))) -> dict:
        _ = session
        if not app.state.feature_multi_institution:
            return {
                "requires_onboarding": False,
                "counts": {"institutions": 0, "depots": 0, "praeparate": 0},
            }
        if hasattr(repository, "get_onboarding_status"):
            status_payload = repository.get_onboarding_status()
            return {
                "requires_onboarding": bool(status_payload.get("requires_onboarding")),
                "counts": status_payload.get("counts") or {},
            }
        depots_rows = repository.list_depots(limit=1, offset=0, q="")
        praeparat_rows = repository.list_praeparate(limit=1, offset=0, q="")
        return {
            "requires_onboarding": len(depots_rows) == 0 or len(praeparat_rows) == 0,
            "counts": {
                "institutions": 0,
                "depots": len(depots_rows),
                "praeparate": len(praeparat_rows),
            },
        }

    @router.post("/onboarding/institution-setup", status_code=status.HTTP_201_CREATED)
    def onboarding_institution_setup(
        payload: OnboardingInstitutionSetupRequest,
        session = Depends(require_permission("masterdata_write")),
    ) -> dict:
        _ = session
        if not app.state.feature_multi_institution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature deaktiviert.")
        if not hasattr(repository, "create_onboarding_setup"):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Onboarding nicht verfgbar.")
        try:
            result = repository.create_onboarding_setup(
                institution=payload.institution.model_dump(),
                praeparate=[item.model_dump() for item in payload.praeparate],
                depots=[item.model_dump() for item in payload.depots],
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return {
            "status": "created",
            "institution_id": int(result.get("institution_id") or 0),
            "praeparate_count": int(result.get("praeparate_count") or 0),
            "depots": result.get("depots") or [],
        }

    @router.get("/institutions")
    def list_institutions(session = Depends(require_permission("masterdata_read"))) -> list[dict]:
        _ = session
        if not app.state.feature_multi_institution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature deaktiviert.")
        if not hasattr(repository, "list_institutions"):
            return []
        return repository.list_institutions()

    @router.post("/institutions", status_code=status.HTTP_201_CREATED)
    def create_institution(
        payload: InstitutionUpsertRequest,
        session = Depends(require_permission("masterdata_write")),
    ) -> dict[str, int | str]:
        if not app.state.feature_multi_institution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature deaktiviert.")
        if not hasattr(repository, "create_institution"):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Institutionen nicht verfgbar.")
        try:
            new_id = repository.create_institution(
                name=payload.name,
                adresse=payload.adresse,
                strasse=payload.strasse,
                hausnummer=payload.hausnummer,
                postleitzahl=payload.postleitzahl,
                stadt=payload.stadt,
                latitude=payload.latitude,
                longitude=payload.longitude,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        repository.log_audit(
            username=session.username,
            action="create",
            resource_type="institution",
            resource_id=new_id,
            details={"name": payload.name},
        )
        return {"id": new_id, "status": "created"}

    @router.put("/institutions/{institution_id}")
    def update_institution(
        institution_id: int,
        payload: InstitutionUpsertRequest,
        session = Depends(require_permission("masterdata_write")),
    ) -> dict[str, int | str]:
        if not app.state.feature_multi_institution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature deaktiviert.")
        if not hasattr(repository, "update_institution"):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Institutionen nicht verfgbar.")
        try:
            changed = repository.update_institution(
                institution_id=institution_id,
                name=payload.name,
                adresse=payload.adresse,
                strasse=payload.strasse,
                hausnummer=payload.hausnummer,
                postleitzahl=payload.postleitzahl,
                stadt=payload.stadt,
                latitude=payload.latitude,
                longitude=payload.longitude,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if not changed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution nicht gefunden.")
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="institution",
            resource_id=institution_id,
            details={"name": payload.name},
        )
        return {"id": institution_id, "status": "updated"}

    @router.delete("/institutions/{institution_id}")
    def delete_institution(
        institution_id: int,
        session = Depends(require_permission("masterdata_write")),
    ) -> dict[str, int | str]:
        if not app.state.feature_multi_institution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature deaktiviert.")
        if not hasattr(repository, "delete_institution"):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Institutionen nicht verfgbar.")
        try:
            changed = repository.delete_institution(institution_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if not changed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution nicht gefunden.")
        repository.log_audit(
            username=session.username,
            action="delete",
            resource_type="institution",
            resource_id=institution_id,
        )
        return {"id": institution_id, "status": "deleted"}

    @router.get("/map/institutions")
    def map_institutions(session = Depends(require_permission("movements_read"))) -> list[dict]:
        if not app.state.feature_multi_institution or not app.state.feature_institution_map:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature deaktiviert.")
        if not hasattr(repository, "list_map_institutions_with_depots"):
            return []
        rows = repository.list_map_institutions_with_depots()
        if session.role == "Admin":
            return rows
        allowed_ids = set(_allowed_depot_ids(session, require_write=False))
        scoped: list[dict] = []
        for item in rows:
            depots = [depot for depot in item.get("depots", []) if int(depot.get("id") or 0) in allowed_ids]
            if depots:
                copy_item = dict(item)
                copy_item["depots"] = depots
                scoped.append(copy_item)
        return scoped

    @router.get("/geo/geocode")
    def geocode_address(
        q: str,
        session = Depends(require_permission("masterdata_write")),
    ) -> dict[str, float | str]:
        _ = session
        query = (q or "").strip()
        if len(query) < 4:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Adresse zu kurz.")
        try:
            params = urlencode({"q": query, "format": "jsonv2", "limit": 1, "countrycodes": "de"})
            req = UrlRequest(
                _require_http_scheme(f"https://nominatim.openstreetmap.org/search?{params}"),
                headers={"User-Agent": "ndhub-web/geo-geocode"},
            )
            with urlopen(req, timeout=8) as resp:  # nosec B310: URL scheme validated by _require_http_scheme
                payload = json.loads(resp.read().decode("utf-8"))
            if not isinstance(payload, list) or not payload:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keine Koordinate gefunden.")
            top = payload[0] if isinstance(payload[0], dict) else {}
            lat = float(top.get("lat"))
            lon = float(top.get("lon"))
            return {"latitude": lat, "longitude": lon, "display_name": str(top.get("display_name") or "")}
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Geokodierung fehlgeschlagen: {exc}") from exc


    return router
