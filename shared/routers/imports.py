"""Shared Imports-Router for bewegungen XLSX import (Issues #60/#61).

Web enables dry_run, fingerprint/dedup, error_summary, depot write-scoping.
Desktop uses the simple path.
"""

from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse


def create_imports_router(
    repository,
    require_permission,
    *,
    build_import_template,
    load_import_dataframe,
    map_import_columns,
    analyze_import_dataframe,
    enable_web_features: bool = False,
    summarize_import_errors=None,
    build_import_execution_fingerprint=None,
    allowed_depot_ids=None,
) -> APIRouter:
    router = APIRouter(prefix="/imports", tags=["imports"])

    @router.get("/bewegungen/template")
    def download_bewegungen_template(
        session=Depends(require_permission("import_use")),
    ) -> StreamingResponse:
        _ = session
        content = build_import_template(repository)
        return StreamingResponse(
            BytesIO(content),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="bewegungen_vorlage.xlsx"'},
        )

    @router.post("/bewegungen/preview")
    def preview_import_bewegungen(
        file: UploadFile = File(...),
        session=Depends(require_permission("import_use")),
    ) -> dict:
        _ = session
        filename = (file.filename or "").strip()
        if not filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dateiname fehlt.")
        try:
            raw_df, row_offset = load_import_dataframe(file)
            mapped_df = map_import_columns(raw_df)
            parsed_rows, preview_rows, errors = analyze_import_dataframe(repository, mapped_df, row_offset)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Datei konnte nicht gelesen werden: {exc}",
            ) from exc
        payload = {
            "filename": filename,
            "total_rows": int(len(mapped_df.dropna(how="all"))),
            "valid_rows": len(parsed_rows),
            "error_count": len(errors),
            "preview_rows": preview_rows,
            "errors": errors[:100],
        }
        if enable_web_features and summarize_import_errors is not None:
            payload["error_summary"] = summarize_import_errors(errors)
        return payload

    if enable_web_features:

        @router.post("/bewegungen/execute")
        def execute_import_bewegungen(
            file: UploadFile = File(...),
            dry_run: bool = Form(False),
            session=Depends(require_permission("import_use")),
        ) -> dict:
            filename = (file.filename or "").strip()
            if not filename:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dateiname fehlt.")
            try:
                raw_df, row_offset = load_import_dataframe(file)
                mapped_df = map_import_columns(raw_df)
                parsed_rows, _preview_rows, errors = analyze_import_dataframe(repository, mapped_df, row_offset)
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Datei konnte nicht gelesen werden: {exc}",
                ) from exc

            import_fingerprint = build_import_execution_fingerprint(filename, parsed_rows)
            if not dry_run:
                existing_batch = repository.get_import_batch_result(import_fingerprint)
                if existing_batch is not None:
                    deduplicated_result = dict(existing_batch)
                    deduplicated_result["filename"] = filename
                    deduplicated_result["deduplicated"] = True
                    deduplicated_result["import_fingerprint"] = import_fingerprint
                    deduplicated_result["dry_run"] = False
                    repository.log_audit(
                        username=session.username,
                        action="create",
                        resource_type="bewegung_import",
                        details={
                            "filename": filename,
                            "imported": deduplicated_result.get("imported"),
                            "errors": deduplicated_result.get("error_count"),
                            "import_fingerprint": import_fingerprint,
                            "deduplicated": True,
                            "dry_run": False,
                        },
                    )
                    return deduplicated_result

            allowed_write_ids = set(allowed_depot_ids(session, require_write=True)) if allowed_depot_ids else set()
            if dry_run:
                would_imported = len(parsed_rows)
                if session.role != "Admin" and allowed_depot_ids is not None:
                    would_imported = sum(
                        1 for row in parsed_rows if int(row.get("depot_id") or 0) in allowed_write_ids
                    )
                dry_result = {
                    "filename": filename,
                    "imported": 0,
                    "would_imported": would_imported,
                    "errors": errors[:200],
                    "error_count": len(errors),
                    "error_summary": summarize_import_errors(errors) if summarize_import_errors else {},
                    "deduplicated": False,
                    "import_fingerprint": import_fingerprint,
                    "dry_run": True,
                }
                repository.log_audit(
                    username=session.username,
                    action="create",
                    resource_type="bewegung_import",
                    details={
                        "filename": filename,
                        "would_imported": len(parsed_rows),
                        "errors": len(errors),
                        "import_fingerprint": import_fingerprint,
                        "deduplicated": False,
                        "dry_run": True,
                    },
                )
                return dry_result

            imported = 0
            for row in parsed_rows:
                if session.role != "Admin" and allowed_depot_ids is not None:
                    if int(row.get("depot_id") or 0) not in allowed_write_ids:
                        errors.append(f"Zeile {row['display_row']}: Keine Schreibberechtigung auf Depot.")
                        continue
                try:
                    repository.insert_bewegung(
                        depot_id=row["depot_id"],
                        praeparat_id=row["praeparat_id"],
                        typ=row["typ"],
                        charge=row["charge"],
                        verfall=row["verfall"],
                        datum=row["datum"],
                        anzahl=row["anzahl"],
                        empfaenger=row["empfaenger"],
                    )
                    imported += 1
                except ValueError as exc:
                    errors.append(f"Zeile {row['display_row']}: {exc}")

            result_payload = {
                "filename": filename,
                "imported": imported,
                "errors": errors[:200],
                "error_count": len(errors),
                "error_summary": summarize_import_errors(errors) if summarize_import_errors else {},
                "deduplicated": False,
                "import_fingerprint": import_fingerprint,
                "dry_run": False,
            }
            repository.save_import_batch_result(
                batch_id=import_fingerprint,
                username=session.username,
                result=result_payload,
            )
            repository.log_audit(
                username=session.username,
                action="create",
                resource_type="bewegung_import",
                details={
                    "filename": filename,
                    "imported": imported,
                    "errors": len(errors),
                    "import_fingerprint": import_fingerprint,
                    "deduplicated": False,
                    "dry_run": False,
                },
            )
            return result_payload

    else:

        @router.post("/bewegungen/execute")
        def execute_import_bewegungen(
            file: UploadFile = File(...),
            session=Depends(require_permission("import_use")),
        ) -> dict:
            _ = session
            filename = (file.filename or "").strip()
            if not filename:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dateiname fehlt.")
            try:
                raw_df, row_offset = load_import_dataframe(file)
                mapped_df = map_import_columns(raw_df)
                parsed_rows, _preview_rows, errors = analyze_import_dataframe(repository, mapped_df, row_offset)
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Datei konnte nicht gelesen werden: {exc}",
                ) from exc

            imported = 0
            for row in parsed_rows:
                try:
                    repository.insert_bewegung(
                        depot_id=row["depot_id"],
                        praeparat_id=row["praeparat_id"],
                        typ=row["typ"],
                        charge=row["charge"],
                        verfall=row["verfall"],
                        datum=row["datum"],
                        anzahl=row["anzahl"],
                        empfaenger=row["empfaenger"],
                    )
                    imported += 1
                except ValueError as exc:
                    errors.append(f"Zeile {row['display_row']}: {exc}")

            repository.log_audit(
                username=session.username,
                action="create",
                resource_type="bewegung_import",
                details={"filename": filename, "imported": imported, "errors": len(errors)},
            )
            return {
                "filename": filename,
                "imported": imported,
                "errors": errors[:200],
                "error_count": len(errors),
            }

    return router
