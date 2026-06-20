"""Simple token authentication for MVP backend."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


@dataclass
class SessionInfo:
    username: str
    role: str | None
    expires_at: datetime


class TokenStore:
    """In-memory token storage for MVP use."""

    def __init__(self, ttl_hours: int = 12):
        self.ttl = timedelta(hours=ttl_hours)
        self._tokens: dict[str, SessionInfo] = {}

    def issue(self, username: str, role: str | None) -> str:
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        self._tokens[token] = SessionInfo(
            username=username,
            role=role,
            expires_at=now + self.ttl,
        )
        return token

    def get(self, token: str) -> SessionInfo | None:
        info = self._tokens.get(token)
        if info is None:
            return None
        if info.expires_at <= datetime.now(timezone.utc):
            self._tokens.pop(token, None)
            return None
        return info

    def revoke(self, token: str) -> bool:
        return self._tokens.pop(token, None) is not None


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_session(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> SessionInfo:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )
    token_store: TokenStore = request.app.state.token_store
    info = token_store.get(credentials.credentials)
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )
    return info


def require_admin_session(
    session: SessionInfo = Depends(get_current_session),
) -> SessionInfo:
    if session.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin-Rechte erforderlich.",
        )
    return session

