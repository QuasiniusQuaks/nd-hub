"""Auth-Router für Desktop-Backend — Logout + Change-Password.

Proof-of-Concept für Issue #61: FastAPI APIRouter-Muster (analog #60).
Factory-Pattern mit Dependency-Injection.
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
    """Factory: erstellt den Auth-Router mit allen Dependencies."""
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
