"""Web desktop-sync token management routes under /auth (Issue #60)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials


def create_desktop_sync_auth_router(token_store, get_current_session, DesktopSyncTokenResponse, DesktopSyncTokenCreateRequest, DesktopSyncTokenArchiveItem, DesktopSyncTokenRevokeRequest, _parse_iso_datetime, _mask_token, _resolve_archive_status) -> APIRouter:
    router = APIRouter()

    @router.post("/auth/desktop-sync-token", response_model=DesktopSyncTokenResponse)
    def create_desktop_sync_token(
        request: Request,
        payload: DesktopSyncTokenCreateRequest | None = None,
        session = Depends(get_current_session),
    ) -> DesktopSyncTokenResponse:
        base_url = str(request.base_url).rstrip("/")
        client_label = str((payload.client_label if payload else "") or "").strip() or None
        desktop_token = token_store.issue(
            username=session.username,
            role=session.role,
            ttl_hours=24 * 365 * 10,
            token_type="desktop_sync",  # nosec B106: token type label, not a password
            token_label=client_label,
        )
        token_info = token_store.get(desktop_token)
        if token_info is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Desktop-Token konnte nicht erzeugt werden.",
            )
        return DesktopSyncTokenResponse(
            backend_url=base_url,
            token=desktop_token,
            username=session.username,
            role=session.role,
            expires_at=token_info.expires_at.isoformat(),
            client_label=client_label,
        )

    @router.get("/auth/desktop-sync-tokens", response_model=list[DesktopSyncTokenArchiveItem])
    def list_desktop_sync_tokens(
        session = Depends(get_current_session),
    ) -> list[DesktopSyncTokenArchiveItem]:
        _ = session
        rows: list[DesktopSyncTokenArchiveItem] = []
        for entry in token_store.list_tokens(token_type="desktop_sync"):  # nosec B106: token type label, not a password
            issued_at = _parse_iso_datetime(entry.get("issued_at"))
            expires_at = _parse_iso_datetime(entry.get("expires_at"))
            revoked_at = _parse_iso_datetime(entry.get("revoked_at"))
            if not isinstance(issued_at, datetime) or not isinstance(expires_at, datetime):
                continue
            token_value = str(entry.get("token") or "")
            rows.append(
                DesktopSyncTokenArchiveItem(
                    token_fingerprint=str(entry.get("fingerprint") or ""),
                    token_masked=_mask_token(token_value),
                    client_label=entry.get("token_label"),
                    username=str(entry.get("username") or ""),
                    role=entry.get("role"),
                    created_at=issued_at.isoformat(),
                    expires_at=expires_at.isoformat(),
                    status=_resolve_archive_status(expires_at, revoked_at, token_value),
                )
            )
        return rows

    @router.post("/auth/desktop-sync-token/revoke")
    def revoke_desktop_sync_token(
        payload: DesktopSyncTokenRevokeRequest,
        session = Depends(get_current_session),
    ) -> dict[str, str]:
        _ = session
        revoked = token_store.revoke_by_fingerprint(
            payload.token_fingerprint,
            token_type="desktop_sync",  # nosec B106: token type label, not a password  # nosec B106: token type label, not a password
        )
        if not revoked:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Desktop-Token nicht gefunden oder bereits widerrufen.",
            )
        return {"status": "revoked"}


    return router
