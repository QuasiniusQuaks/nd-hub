"""Shared Praeparate-Router (Issues #60/#61)."""

from fastapi import APIRouter, Depends, HTTPException, status


def create_praeparate_router(
    repository,
    require_permission,
    *,
    praeparat_upsert_model,
    include_extended_fields: bool = False,
) -> APIRouter:
    PraeparatUpsertRequest = praeparat_upsert_model
    router = APIRouter(prefix="/praeparate", tags=["praeparate"])

    def _kwargs(payload) -> dict:
        data = {"name": payload.name}
        if include_extended_fields:
            data.update(
                {
                    "wirkstoff": payload.wirkstoff,
                    "darreichungsform": payload.darreichungsform,
                    "staerke": payload.staerke,
                    "einheit": payload.einheit,
                    "pzn": payload.pzn,
                    "hersteller": payload.hersteller,
                }
            )
        return data

    def _details(payload) -> dict:
        if include_extended_fields:
            return {
                "name": payload.name,
                "wirkstoff": payload.wirkstoff,
                "darreichungsform": payload.darreichungsform,
                "staerke": payload.staerke,
                "einheit": payload.einheit,
                "pzn": payload.pzn,
                "hersteller": payload.hersteller,
            }
        return {"name": payload.name}

    @router.get("/")
    def list_praeparate(
        q: str = "",
        limit: int = 100,
        offset: int = 0,
        session=Depends(require_permission("masterdata_read")),
    ) -> list[dict]:
        _ = session
        return repository.list_praeparate(q=q, limit=limit, offset=offset)

    @router.post("/", status_code=status.HTTP_201_CREATED)
    def create_praeparat(
        payload: PraeparatUpsertRequest,
        session=Depends(require_permission("masterdata_write")),
    ) -> dict[str, int | str]:
        _ = session
        try:
            new_id = repository.create_praeparat(**_kwargs(payload))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        repository.log_audit(
            username=session.username,
            action="create",
            resource_type="praeparat",
            resource_id=new_id,
            details=_details(payload),
        )
        return {"id": new_id, "status": "created"}

    @router.put("/{praeparat_id}")
    def update_praeparat(
        praeparat_id: int,
        payload: PraeparatUpsertRequest,
        session=Depends(require_permission("masterdata_write")),
    ) -> dict[str, int | str]:
        _ = session
        try:
            changed = repository.update_praeparat(praeparat_id=praeparat_id, **_kwargs(payload))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if not changed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Praeparat nicht gefunden.")
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="praeparat",
            resource_id=praeparat_id,
            details=_details(payload),
        )
        return {"id": praeparat_id, "status": "updated"}

    @router.delete("/{praeparat_id}")
    def delete_praeparat(
        praeparat_id: int,
        session=Depends(require_permission("masterdata_write")),
    ) -> dict[str, int | str]:
        _ = session
        try:
            changed = repository.delete_praeparat(praeparat_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if not changed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Praeparat nicht gefunden.")
        repository.log_audit(
            username=session.username,
            action="delete",
            resource_type="praeparat",
            resource_id=praeparat_id,
        )
        return {"id": praeparat_id, "status": "deleted"}

    return router
