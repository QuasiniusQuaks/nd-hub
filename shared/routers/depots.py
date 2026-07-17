"""Shared Depots-Router — masterdata + assignments + kontakte under /depots.

Issues #60/#61/#65. Optional access control and geo/institution fields via DI.
"""

from fastapi import APIRouter, Depends, HTTPException, status


def create_depots_router(
    repository,
    require_permission,
    *,
    depot_upsert_model,
    depot_assignments_update_model,
    kontakt_upsert_model,
    ensure_depot_access=None,
    resolve_list_allowed_ids=None,
    include_geo_fields: bool = False,
) -> APIRouter:
    """ensure_depot_access(session, depot_id, require_write) optional.
    resolve_list_allowed_ids(session) -> list[int]|None (None = no filter / admin).
    """
    DepotUpsertRequest = depot_upsert_model
    DepotAssignmentsUpdateRequest = depot_assignments_update_model
    KontaktUpsertRequest = kontakt_upsert_model
    router = APIRouter(prefix="/depots", tags=["depots"])

    def _access(session, depot_id: int, require_write: bool) -> None:
        if ensure_depot_access is not None:
            ensure_depot_access(session, depot_id=depot_id, require_write=require_write)

    def _depot_kwargs(payload) -> dict:
        data = {
            "name": payload.name,
            "adresse": payload.adresse,
            "telefon": payload.telefon,
            "email": payload.email,
        }
        if include_geo_fields:
            data.update(
                {
                    "strasse": payload.strasse,
                    "hausnummer": payload.hausnummer,
                    "postleitzahl": payload.postleitzahl,
                    "stadt": payload.stadt,
                    "institution_id": payload.institution_id,
                    "latitude": payload.latitude,
                    "longitude": payload.longitude,
                }
            )
        return data

    @router.get("/")
    def list_depots(
        q: str = "",
        limit: int = 100,
        offset: int = 0,
        session=Depends(require_permission("masterdata_read")),
    ) -> list[dict]:
        if resolve_list_allowed_ids is not None:
            allowed_ids = resolve_list_allowed_ids(session)
            if session.role != "Admin" and not allowed_ids:
                return []
            return repository.list_depots(q=q, limit=limit, offset=offset, allowed_ids=allowed_ids)
        _ = session
        return repository.list_depots(q=q, limit=limit, offset=offset)

    @router.post("/", status_code=status.HTTP_201_CREATED)
    def create_depot(
        payload: DepotUpsertRequest,
        session=Depends(require_permission("masterdata_write")),
    ) -> dict[str, int | str]:
        _ = session
        try:
            new_id = repository.create_depot(**_depot_kwargs(payload))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        repository.log_audit(
            username=session.username,
            action="create",
            resource_type="depot",
            resource_id=new_id,
            details={"name": payload.name},
        )
        return {"id": new_id, "status": "created"}

    @router.put("/{depot_id}")
    def update_depot(
        depot_id: int,
        payload: DepotUpsertRequest,
        session=Depends(require_permission("masterdata_write")),
    ) -> dict[str, int | str]:
        _access(session, depot_id, True)
        try:
            changed = repository.update_depot(depot_id=depot_id, **_depot_kwargs(payload))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if not changed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Depot nicht gefunden.")
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="depot",
            resource_id=depot_id,
            details={"name": payload.name},
        )
        return {"id": depot_id, "status": "updated"}

    @router.delete("/{depot_id}")
    def delete_depot(
        depot_id: int,
        session=Depends(require_permission("masterdata_write")),
    ) -> dict[str, int | str]:
        _access(session, depot_id, True)
        try:
            changed = repository.delete_depot(depot_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if not changed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Depot nicht gefunden.")
        repository.log_audit(
            username=session.username,
            action="delete",
            resource_type="depot",
            resource_id=depot_id,
        )
        return {"id": depot_id, "status": "deleted"}

    @router.get("/{depot_id}/praeparate")
    def list_praeparate_for_depot(
        depot_id: int,
        session=Depends(require_permission("masterdata_read")),
    ) -> list[dict]:
        _access(session, depot_id, False)
        return repository.list_praeparate_for_depot(depot_id)

    @router.get("/{depot_id}/zuordnungen")
    def list_depot_assignments(
        depot_id: int,
        session=Depends(require_permission("settings_read")),
    ) -> list[dict]:
        _access(session, depot_id, False)
        return repository.list_depot_assignments(depot_id)

    @router.put("/{depot_id}/zuordnungen")
    def update_depot_assignments(
        depot_id: int,
        payload: DepotAssignmentsUpdateRequest,
        session=Depends(require_permission("settings_write")),
    ) -> dict[str, int | str]:
        _access(session, depot_id, True)
        try:
            repository.set_depot_assignments(
                depot_id=depot_id,
                assignments=[item.model_dump() for item in payload.assignments],
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="depot",
            resource_id=depot_id,
            details={"assignments_count": len(payload.assignments)},
        )
        return {"id": depot_id, "status": "assignments_updated"}

    @router.get("/{depot_id}/kontakte")
    def list_kontakte_for_depot(
        depot_id: int,
        session=Depends(require_permission("settings_read")),
    ) -> list[dict]:
        _access(session, depot_id, False)
        return repository.list_kontakte(depot_id)

    @router.post("/{depot_id}/kontakte", status_code=status.HTTP_201_CREATED)
    def create_kontakt_for_depot(
        depot_id: int,
        payload: KontaktUpsertRequest,
        session=Depends(require_permission("settings_write")),
    ) -> dict[str, int | str]:
        _access(session, depot_id, True)
        try:
            kontakt_id = repository.create_kontakt(
                depot_id=depot_id,
                name=payload.name,
                rolle=payload.rolle,
                telefon=payload.telefon,
                email=payload.email,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        repository.log_audit(
            username=session.username,
            action="create",
            resource_type="kontakt",
            resource_id=kontakt_id,
            details={"depot_id": depot_id, "name": payload.name},
        )
        return {"id": kontakt_id, "status": "created"}

    return router
