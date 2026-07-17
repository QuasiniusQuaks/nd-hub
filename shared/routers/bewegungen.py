"""Shared Bewegungen-Router (Issues #60/#61).

Desktop: simple list filters.
Web: advanced filters + CSV export + depot access checks via DI.
"""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse


def create_bewegungen_router(
    repository,
    require_permission,
    *,
    bewegung_create_model,
    ensure_depot_access=None,
    scoped_requested_ids=None,
    include_advanced_filters: bool = False,
    include_export: bool = False,
    csv_response=None,
    attachments_dir=None,
    build_attachment_target_path=None,
    persist_pdf_upload=None,
    pdf_mime_types=None,
) -> APIRouter:
    """Factory for /bewegungen routes.

    ensure_depot_access(session, depot_id, require_write) optional.
    scoped_requested_ids(session, depot_ids, require_write) optional (web scope).
    """
    BewegungCreateRequest = bewegung_create_model
    router = APIRouter(prefix="/bewegungen", tags=["bewegungen"])

    def _access(session, depot_id: int, require_write: bool) -> None:
        if ensure_depot_access is not None:
            ensure_depot_access(session, depot_id=depot_id, require_write=require_write)

    if include_advanced_filters:

        @router.get("/")
        def list_bewegungen(
            limit: int = 100,
            offset: int = 0,
            q: str = "",
            typ: str = "",
            depot_id: int = 0,
            praeparat_id: int = 0,
            has_attachment: int = 0,
            start_date: str = "",
            end_date: str = "",
            session=Depends(require_permission("movements_read")),
        ) -> list[dict]:
            if scoped_requested_ids is not None:
                scoped_ids = scoped_requested_ids(
                    session,
                    [int(depot_id)] if int(depot_id or 0) > 0 else [],
                    require_write=False,
                )
                if session.role != "Admin" and not scoped_ids:
                    return []
                requested_depot_id = int(depot_id) if int(depot_id or 0) > 0 else None
                depot_scope_ids = scoped_ids if session.role != "Admin" else []
                return repository.list_bewegungen(
                    limit=limit,
                    offset=offset,
                    q=q,
                    typ=typ or None,
                    depot_id=requested_depot_id,
                    depot_ids=depot_scope_ids or None,
                    praeparat_id=praeparat_id if int(praeparat_id or 0) > 0 else None,
                    has_attachment=bool(int(has_attachment or 0)),
                    start_date=start_date or None,
                    end_date=end_date or None,
                )
            _ = session
            return repository.list_bewegungen(limit=limit, offset=offset, q=q, typ=typ or None)

    else:

        @router.get("/")
        def list_bewegungen(
            limit: int = 100,
            offset: int = 0,
            q: str = "",
            typ: str = "",
            session=Depends(require_permission("movements_read")),
        ) -> list[dict]:
            _ = session
            return repository.list_bewegungen(limit=limit, offset=offset, q=q, typ=typ or None)

    @router.post("/", status_code=status.HTTP_201_CREATED)
    def create_bewegung(
        payload: BewegungCreateRequest,
        session=Depends(require_permission("movements_write")),
    ) -> dict[str, int | str]:
        _access(session, payload.depot_id, True)
        try:
            new_id = repository.insert_bewegung(
                depot_id=payload.depot_id,
                praeparat_id=payload.praeparat_id,
                typ=payload.typ,
                charge=payload.charge,
                verfall=payload.verfall.isoformat(),
                datum=payload.datum.isoformat(),
                anzahl=payload.anzahl,
                empfaenger=payload.empfaenger,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        repository.log_audit(
            username=session.username,
            action="create",
            resource_type="bewegung",
            resource_id=new_id,
            details={"typ": payload.typ, "depot_id": payload.depot_id, "praeparat_id": payload.praeparat_id},
        )
        return {"id": new_id, "status": "created"}

    @router.post("/{bewegung_id}/attachment", status_code=status.HTTP_201_CREATED)
    def upload_bewegung_attachment(
        bewegung_id: int,
        file: UploadFile = File(...),
        session=Depends(require_permission("movements_write")),
    ) -> dict[str, int | str]:
        if not all([attachments_dir, build_attachment_target_path, persist_pdf_upload]):
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Attachments not configured.")
        bewegung = repository.get_bewegung(bewegung_id)
        if bewegung is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bewegung nicht gefunden.")
        _access(session, int(bewegung.get("depot_id") or 0), True)
        filename = (file.filename or "").strip()
        if not filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dateiname fehlt.")
        content_type = (file.content_type or "").lower()
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nur PDF-Dateien sind erlaubt.")
        allowed = pdf_mime_types or set()
        if content_type and allowed and content_type not in allowed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nur PDF-Dateien sind erlaubt.")
        depot_name = repository.get_depot_name(int(bewegung["depot_id"]))
        target_path = build_attachment_target_path(
            attachments_dir,
            bewegung_id=bewegung_id,
            depot_name=depot_name,
            original_name=filename,
        )
        try:
            size = persist_pdf_upload(file, target_path)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Datei konnte nicht gespeichert werden.",
            ) from exc
        stored_name = Path(filename).name
        uploaded_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        repository.set_bewegung_attachment(
            bewegung_id=bewegung_id,
            datei_pfad=str(target_path),
            datei_name=stored_name,
            datei_groesse=size,
            uploaded_at=uploaded_at,
        )
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="bewegung",
            resource_id=bewegung_id,
            details={"attachment": stored_name, "size": size},
        )
        return {"id": bewegung_id, "status": "attachment_saved"}

    @router.get("/{bewegung_id}/attachment")
    def get_bewegung_attachment(
        bewegung_id: int,
        download: bool = False,
        session=Depends(require_permission("movements_read")),
    ) -> FileResponse:
        bewegung = repository.get_bewegung(bewegung_id)
        if bewegung is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bewegung nicht gefunden.")
        _access(session, int(bewegung.get("depot_id") or 0), False)
        datei_pfad = (bewegung.get("datei_pfad") or "").strip()
        if not datei_pfad:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kein PDF-Anhang vorhanden.")
        path = Path(datei_pfad)
        if not path.exists() or not path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF-Datei nicht gefunden.")
        filename = (bewegung.get("datei_name") or path.name).strip() or path.name
        if download:
            return FileResponse(path=path, media_type="application/pdf", filename=filename)
        return FileResponse(path=path, media_type="application/pdf")

    if include_export:

        @router.get("/export.csv")
        def export_bewegungen_csv(
            q: str = "",
            typ: str = "",
            depot_id: int = 0,
            praeparat_id: int = 0,
            has_attachment: int = 0,
            start_date: str = "",
            end_date: str = "",
            session=Depends(require_permission("movements_read")),
        ):
            if csv_response is None:
                raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="CSV export not configured.")
            requested_depot_id = depot_id if int(depot_id or 0) > 0 else None
            if requested_depot_id is not None and session.role != "Admin":
                _access(session, requested_depot_id, False)
            depot_ids = None
            if scoped_requested_ids is not None and session.role != "Admin":
                depot_ids = scoped_requested_ids(
                    session,
                    [int(depot_id)] if int(depot_id or 0) > 0 else [],
                    require_write=False,
                )
            rows = repository.list_bewegungen(
                limit=5000,
                offset=0,
                q=q,
                typ=typ or None,
                depot_id=requested_depot_id,
                depot_ids=depot_ids,
                praeparat_id=praeparat_id if int(praeparat_id or 0) > 0 else None,
                has_attachment=bool(int(has_attachment or 0)),
                start_date=start_date or None,
                end_date=end_date or None,
            )
            headers = [
                "ID",
                "Typ",
                "Charge",
                "Verfall",
                "Datum",
                "Anzahl",
                "Depot_ID",
                "Praeparat_ID",
                "Empfaenger",
                "Hat_PDF",
                "Datei",
            ]
            data_rows = []
            for row in rows:
                datum = row.get("eingang_datum") or row.get("ausgang_datum") or ""
                has_pdf = int(row.get("has_attachment") or 0)
                data_rows.append(
                    [
                        row.get("id", ""),
                        row.get("typ", ""),
                        row.get("charge", ""),
                        row.get("verfall", ""),
                        datum,
                        row.get("anzahl", ""),
                        row.get("depot_id", ""),
                        row.get("praeparat_id", ""),
                        row.get("empfaenger", "") or "",
                        has_pdf,
                        row.get("datei_name", "") or "",
                    ]
                )
            return csv_response("bewegungen_verlauf.csv", headers, data_rows)

    return router
