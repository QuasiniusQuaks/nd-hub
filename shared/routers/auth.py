"""Shared Auth-Router — Login-Logout, Change-Password.

Issue #65 — gemeinsame Router-Factory für beide Backends.
Identische Logik für Desktop- und Web-Backend.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)


def create_auth_router(
    security,
    token_store,
    repository,
    get_current_session,
    bearer_scheme,
) -> APIRouter:
    """Factory: erstellt den Auth-Router mit allen Dependencies.

    Wird von beiden Backends verwendet (Desktop + Web).
    Dependencies werden als Parameter übergeben (Dependency-Injection).

    Args:
        security: SecurityManager-Instanz.
        token_store: TokenStore-Instanz.
        repository: Repository-Instanz.
        get_current_session: FastAPI-Dependency für Session-Extraktion.
        bearer_scheme: HTTPBearer-Scheme.

    Returns:
        Konfigurierter APIRouter mit /auth/logout + /auth/change-password.
    """
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
        payload,
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

    return router
