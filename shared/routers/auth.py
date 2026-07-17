"""Shared Auth-Router — common session/profile endpoints.

Issues #60/#61/#65 — Factory with DI for both backends.
Login and web-only desktop-sync tokens stay in the respective app.py.
"""

import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)


def create_auth_router(
    security,
    token_store,
    repository,
    get_current_session,
    bearer_scheme,
    *,
    password_change_model,
    get_user_flags,
    get_avatar_path_for_user,
    enrich_me=None,
) -> APIRouter:
    """Factory for shared auth routes.

    Args:
        enrich_me: optional callable(session) -> dict merged into /auth/me
                   (e.g. web depot_permissions).
        password_change_model: Pydantic model class for change-password body.
    """
    PasswordChangeRequest = password_change_model
    router = APIRouter(prefix="/auth", tags=["auth"])

    @router.post("/logout")
    def auth_logout(
        session=Depends(get_current_session),
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    ) -> dict[str, str]:
        _ = session
        if credentials and credentials.credentials:
            token_store.revoke(credentials.credentials)
        return {"status": "logged_out"}

    @router.post("/change-password")
    def auth_change_password(
        payload: PasswordChangeRequest,
        session=Depends(get_current_session),
    ) -> dict[str, str]:
        user_row = security.cur.execute(
            "SELECT id FROM users WHERE username = ?",
            (session.username,),
        ).fetchone()
        if not user_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benutzer nicht gefunden.")
        ok, message = security.change_password(int(user_row[0]), payload.old_password, payload.new_password)
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="user",
            resource_id=int(user_row[0]),
            details={"change": "password_self_service"},
        )
        return {"status": "password_changed"}

    @router.get("/me")
    def auth_me(session=Depends(get_current_session)) -> dict[str, object]:
        user_flags = get_user_flags(security, session.username)
        avatar_path = get_avatar_path_for_user(security, session.username)
        payload: dict[str, object] = {
            "username": session.username,
            "role": session.role,
            "expires_at": session.expires_at.isoformat(),
            "requires_password_change": user_flags["requires_password_change"],
            "permissions": user_flags["permissions"],
            "avatar_available": avatar_path is not None,
        }
        if enrich_me is not None:
            payload.update(enrich_me(session))
        return payload

    @router.get("/activity")
    def auth_activity(
        limit: int = 50,
        session=Depends(get_current_session),
    ) -> list[dict]:
        safe_limit = max(1, min(int(limit), 200))
        user_row = security.cur.execute(
            "SELECT id FROM users WHERE username = ?",
            (session.username,),
        ).fetchone()
        if not user_row:
            return []
        rows = security.get_activity_log(user_id=int(user_row[0]), limit=safe_limit)
        result: list[dict] = []
        for row in rows:
            result.append(
                {
                    "id": int(row[0]),
                    "username": str(row[1]),
                    "action": str(row[2]),
                    "details": str(row[3] or ""),
                    "timestamp": str(row[4]),
                }
            )
        return result

    @router.get("/avatar")
    def auth_avatar(session=Depends(get_current_session)) -> FileResponse:
        avatar_path = get_avatar_path_for_user(security, session.username)
        if avatar_path is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kein Profilbild vorhanden.")
        return FileResponse(path=avatar_path)

    @router.post("/avatar")
    def upload_auth_avatar(
        file: UploadFile = File(...),
        session=Depends(get_current_session),
    ) -> dict[str, str]:
        filename = (file.filename or "").strip()
        if not filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dateiname fehlt.")
        suffix = Path(filename).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nur PNG/JPG/JPEG/WEBP/BMP sind erlaubt.",
            )
        user_row = security.cur.execute(
            "SELECT id FROM users WHERE username = ?",
            (session.username,),
        ).fetchone()
        if not user_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benutzer nicht gefunden.")
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = Path(tmp.name)
            file.file.seek(0)
            shutil.copyfileobj(file.file, tmp)
        try:
            security.current_user = session.username
            security.current_role = session.role
            ok, message = security.set_user_avatar(int(user_row[0]), str(tmp_path))
        finally:
            tmp_path.unlink(missing_ok=True)
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="user",
            resource_id=int(user_row[0]),
            details={"change": "avatar_upload"},
        )
        return {"status": "avatar_saved"}

    @router.delete("/avatar")
    def clear_auth_avatar(session=Depends(get_current_session)) -> dict[str, str]:
        user_row = security.cur.execute(
            "SELECT id FROM users WHERE username = ?",
            (session.username,),
        ).fetchone()
        if not user_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benutzer nicht gefunden.")
        security.current_user = session.username
        security.current_role = session.role
        ok, message = security.clear_user_avatar(int(user_row[0]))
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
        repository.log_audit(
            username=session.username,
            action="update",
            resource_type="user",
            resource_id=int(user_row[0]),
            details={"change": "avatar_clear"},
        )
        return {"status": "avatar_cleared"}

    return router
