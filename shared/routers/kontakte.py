"""Shared Kontakte-Router (Issues #60/#61) — global update/delete by id."""

from fastapi import APIRouter, Depends, HTTPException, status


def create_kontakte_router(
    repository,
    require_permission,
    *,
    kontakt_upsert_model,
) -> APIRouter:
    KontaktUpsertRequest = kontakt_upsert_model
    router = APIRouter(prefix="/kontakte", tags=["kontakte"])

    @router.put("/{kontakt_id}")
    def update_kontakt(
        kontakt_id: int,
        payload: KontaktUpsertRequest,
        session=Depends(require_permission("settings_write")),
    ) -> dict[str, int | str]:
        _ = session
        try:
            changed = repository.update_kontakt(
                kontakt_id=kontakt_id,
                name=payload.name,
                rolle=payload.rolle,
                telefon=payload.telefon,
                email=payload.email,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if not changed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kontakt nicht gefunden.")
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="kontakt",
            resource_id=kontakt_id,
            details={"name": payload.name},
        )
        return {"id": kontakt_id, "status": "updated"}

    @router.delete("/{kontakt_id}")
    def delete_kontakt(
        kontakt_id: int,
        session=Depends(require_permission("settings_write")),
    ) -> dict[str, int | str]:
        _ = session
        changed = repository.delete_kontakt(kontakt_id)
        if not changed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kontakt nicht gefunden.")
        repository.log_audit(
            username=session.username,
            action="delete",
            resource_type="kontakt",
            resource_id=kontakt_id,
        )
        return {"id": kontakt_id, "status": "deleted"}

    return router
