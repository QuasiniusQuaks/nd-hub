"""Shared Admin Backup router (Issues #60/#61)."""

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse


def create_admin_backup_router(
    repository,
    require_permission,
    *,
    backups_dir,
    source_db_path,
    database_path,
    list_backup_files,
    create_backup_snapshot,
    auto_backup_hours,
    close_security,
    reopen_security,
    enable_web_features: bool = False,
    db_engine: str = "sqlite",
    max_restore_size_mb=None,
    max_backup_restore_bytes=None,
    create_mariadb_backup_snapshot=None,
    validate_restore_upload_size=None,
    restore_mariadb_backup_payload=None,
    is_valid_sqlite_file=None,
) -> APIRouter:
    router = APIRouter(prefix="/admin", tags=["admin"])

    def _create_snapshot(prefix: str) -> Path:
        if enable_web_features and db_engine == "mariadb" and create_mariadb_backup_snapshot is not None:
            return create_mariadb_backup_snapshot(backups_dir, prefix)
        return create_backup_snapshot(source_db_path, backups_dir, prefix)

    @router.get("/backup/list")
    def list_backups(
        limit: int = 200,
        session=Depends(require_permission("backup_manage")),
    ) -> dict:
        _ = session
        rows = list_backup_files(backups_dir, limit=limit)
        payload = {"rows": rows, "auto_backup_hours": auto_backup_hours}
        if enable_web_features:
            payload["max_restore_size_mb"] = max_restore_size_mb
            payload["db_engine"] = db_engine
        return payload

    @router.post("/backup/create")
    def create_backup(
        session=Depends(require_permission("backup_manage")),
    ) -> dict:
        _ = session
        backup_path = _create_snapshot("manual")
        repository.log_audit(
            username=session.username,
            action="create",
            resource_type="backup",
            details={"operation": "manual", "filename": backup_path.name},
        )
        stat = backup_path.stat()
        return {
            "filename": backup_path.name,
            "size_bytes": int(stat.st_size),
            "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        }

    @router.get("/backup/download")
    def download_backup(
        session=Depends(require_permission("backup_manage")),
    ) -> FileResponse:
        _ = session
        backup_path = _create_snapshot("manual")
        repository.log_audit(
            username=session.username,
            action="create",
            resource_type="backup",
            details={"operation": "manual_download", "filename": backup_path.name},
        )
        return FileResponse(
            path=backup_path,
            filename=backup_path.name,
            media_type="application/octet-stream",
        )

    @router.get("/backup/download/{filename}")
    def download_backup_file(
        filename: str,
        session=Depends(require_permission("backup_manage")),
    ) -> FileResponse:
        _ = session
        safe_name = Path(filename).name
        backup_path = Path(backups_dir) / safe_name
        if not backup_path.exists() or not backup_path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup-Datei nicht gefunden.")
        return FileResponse(
            path=backup_path,
            filename=safe_name,
            media_type="application/octet-stream",
        )

    @router.post("/backup/restore")
    def restore_backup(
        file: UploadFile = File(...),
        session=Depends(require_permission("backup_manage")),
    ) -> dict[str, str]:
        _ = session
        filename = (file.filename or "").strip().lower()
        if enable_web_features:
            if not filename:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dateiname fehlt.")
            uploaded_size_bytes = (
                validate_restore_upload_size(file, max_backup_restore_bytes)
                if validate_restore_upload_size and max_backup_restore_bytes
                else 0
            )
            if db_engine == "mariadb":
                if not filename.endswith((".mariadb.json", ".json")):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Nur MariaDB-Backup-Dateien mit Endung .mariadb.json/.json sind erlaubt.",
                    )
                try:
                    file.file.seek(0)
                    raw = file.file.read()
                    payload = json.loads(raw.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Backup-Datei konnte nicht gelesen werden: {exc}",
                    ) from exc
                pre_restore_path = create_mariadb_backup_snapshot(backups_dir, "pre_restore")
                try:
                    restore_mariadb_backup_payload(payload)
                    close_security()
                    reopen_security()
                except (OSError, sqlite3.Error, ValueError, TypeError, KeyError) as exc:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"MariaDB-Restore fehlgeschlagen: {exc}",
                    ) from exc
            else:
                if not filename.endswith((".db", ".sqlite", ".sqlite3")):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Nur Backup-Dateien mit Endung .db/.sqlite/.sqlite3 sind erlaubt.",
                    )
                db_target_path = Path(database_path).resolve()
                temp_restore_path = db_target_path.with_name(
                    f"{db_target_path.stem}.restore_tmp{db_target_path.suffix}"
                )
                file.file.seek(0)
                with temp_restore_path.open("wb") as temp_out:
                    shutil.copyfileobj(file.file, temp_out)
                if is_valid_sqlite_file is not None and not is_valid_sqlite_file(temp_restore_path):
                    temp_restore_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Backup-Datei ist keine gueltige SQLite-Datei.",
                    )
                try:
                    with sqlite3.connect(str(temp_restore_path)) as conn:
                        required = {"users", "depots", "praeparate", "bewegungen"}
                        rows = conn.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'",
                        ).fetchall()
                        present = {str(row[0]) for row in rows}
                        if not required.issubset(present):
                            missing = ", ".join(sorted(required - present))
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Backup ungueltig, fehlende Tabellen: {missing}",
                            )
                except HTTPException:
                    temp_restore_path.unlink(missing_ok=True)
                    raise
                except (OSError, sqlite3.Error) as exc:
                    temp_restore_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Backup-Datei konnte nicht validiert werden: {exc}",
                    ) from exc

                pre_restore_path = create_backup_snapshot(source_db_path, backups_dir, "pre_restore")
                try:
                    close_security()
                    shutil.move(str(temp_restore_path), str(db_target_path))
                    reopen_security()
                except (OSError, sqlite3.Error) as exc:
                    temp_restore_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Restore fehlgeschlagen: {exc}",
                    ) from exc

            repository.log_audit(
                username=session.username,
                action="update",
                resource_type="backup",
                details={
                    "operation": "restore",
                    "source_file": filename,
                    "source_size_bytes": uploaded_size_bytes,
                    "pre_restore_file": pre_restore_path.name,
                },
            )
            return {
                "status": "restored",
                "pre_restore_backup": pre_restore_path.name,
                "message": "Backup erfolgreich wiederhergestellt. Bitte neu anmelden.",
            }

        # Desktop / simple SQLite path
        if not filename.endswith((".db", ".sqlite", ".sqlite3")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nur Backup-Dateien mit Endung .db/.sqlite/.sqlite3 sind erlaubt.",
            )
        db_target_path = Path(database_path).resolve()
        temp_restore_path = db_target_path.with_name(f"{db_target_path.stem}.restore_tmp{db_target_path.suffix}")
        file.file.seek(0)
        with temp_restore_path.open("wb") as temp_out:
            shutil.copyfileobj(file.file, temp_out)
        try:
            with sqlite3.connect(str(temp_restore_path)) as conn:
                required = {"users", "depots", "praeparate", "bewegungen"}
                rows = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'",
                ).fetchall()
                present = {str(row[0]) for row in rows}
                if not required.issubset(present):
                    missing = ", ".join(sorted(required - present))
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Backup ungueltig, fehlende Tabellen: {missing}",
                    )
        except HTTPException:
            temp_restore_path.unlink(missing_ok=True)
            raise
        except (OSError, sqlite3.Error) as exc:
            temp_restore_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Backup-Datei konnte nicht validiert werden: {exc}",
            ) from exc

        pre_restore_path = create_backup_snapshot(source_db_path, backups_dir, "pre_restore")
        try:
            close_security()
            shutil.move(str(temp_restore_path), str(db_target_path))
            reopen_security()
        except (OSError, sqlite3.Error) as exc:
            temp_restore_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Restore fehlgeschlagen: {exc}",
            ) from exc

        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="backup",
            details={
                "operation": "restore",
                "source_file": filename,
                "pre_restore_file": pre_restore_path.name,
            },
        )
        return {
            "status": "restored",
            "pre_restore_backup": pre_restore_path.name,
            "message": "Backup erfolgreich wiederhergestellt. Bitte neu anmelden.",
        }

    return router
