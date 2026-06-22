"""Auth-Router — Login, Logout, Change-Password, Session-Info.

Proof-of-Concept für Issue #60: FastAPI APIRouter-Muster.
Die Endpoints werden aus app.py in Router-Module extrahiert.

Abhängigkeiten (via Factory-Pattern an create_auth_router übergeben):
- security: SecurityManager
- token_store: TokenStore
- repository: Repository
- get_current_session: Dependency
- bearer_scheme: HTTPBearer
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

if TYPE_CHECKING:
    from security_manager import SecurityManager

logger = logging.getLogger(__name__)


def create_auth_router(
    security: SecurityManager,
    token_store,
    repository,
    get_current_session,
    bearer_scheme,
    session_info_class,
) -> APIRouter:
    """Factory: erstellt den Auth-Router mit allen Dependencies.

    Args:
        security: SecurityManager-Instanz.
        token_store: TokenStore-Instanz.
        repository: Repository-Instanz.
        get_current_session: FastAPI-Dependency für Session-Extraktion.
        bearer_scheme: HTTPBearer-Scheme.
        session_info_class: SessionInfo-Klasse (für Type-Hints).

    Returns:
        Konfigurierter APIRouter mit /auth/* Endpoints.
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
        payload,  # PasswordChangeRequest — wird aus app.py importiert
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
