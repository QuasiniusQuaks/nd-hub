# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Protocol, Tuple
from urllib import error, request
from urllib.parse import urlencode, urlparse


logger = logging.getLogger("ND-Hub.DataAccess")


def _require_http_scheme(url: str) -> str:
    """Validiert dass die URL nur http/https verwendet (SSRF-Schutz)."""
    scheme = urlparse(url).scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError(f"URL scheme not allowed: {url}")
    return url


class OperatingMode(str, Enum):
    LOCAL_ONLY = "local_only"
    HYBRID_SYNC = "hybrid_sync"
    REMOTE_ONLY = "remote_only"

    @classmethod
    def from_raw(cls, value: str) -> "OperatingMode":
        normalized = (value or "").strip().lower()
        for candidate in cls:
            if candidate.value == normalized:
                return candidate
        return cls.LOCAL_ONLY


class LocalSyncOutbox(Protocol):
    def record_sync_outbox(
        self,
        entity_name: str,
        operation: str,
        payload: Dict[str, Any],
        dedupe_key: Optional[str] = None,
    ) -> int:
        ...


@dataclass(frozen=True)
class BackendSyncConfig:
    base_url: str
    connect_timeout_seconds: int = 3
    health_endpoint: str = "/health"
    access_token: str = ""

    @property
    def normalized_base_url(self) -> str:
        return self.base_url.rstrip("/")


class BackendApiClient:
    def __init__(self, config: BackendSyncConfig):
        self.config = config

    def is_configured(self) -> bool:
        return bool(self.config.normalized_base_url)

    def check_health(self) -> bool:
        if not self.is_configured():
            return False
        url = f"{self.config.normalized_base_url}{self.config.health_endpoint}"
        req = request.Request(_require_http_scheme(url), method="GET", headers=self._headers())
        try:
            with request.urlopen(req, timeout=self.config.connect_timeout_seconds) as response:  # nosec B310: URL scheme validated by _require_http_scheme
                return 200 <= response.status < 300
        except (error.URLError, TimeoutError, OSError) as exc:
            logger.info("Backend-Healthcheck nicht erreichbar: %s", exc)
            return False

    def pull_changes(self, cursor: Optional[str], entities: Optional[list], limit: int = 500) -> Dict[str, Any]:
        payload = {
            "cursor": cursor,
            "entities": entities or [],
            "limit": limit,
        }
        return self._post_json("/sync/pull", payload)

    def push_changes(self, batch_id: str, changes: list) -> Dict[str, Any]:
        payload = {
            "batch_id": batch_id,
            "changes": changes,
        }
        return self._post_json("/sync/push", payload)

    def get_sync_status(self) -> Dict[str, Any]:
        return self._get_json("/sync/status")

    def get_sync_ops_stats(self) -> Dict[str, Any]:
        return self._get_json("/sync/ops/stats")

    def list_sync_tokens(self) -> Dict[str, Any]:
        return self._get_json("/auth/desktop-sync-tokens")

    def create_sync_token(self, username: str, expires_in_hours: int = 72, note: str = "") -> Dict[str, Any]:
        payload = {
            "username": username,
            "expires_in_hours": max(1, int(expires_in_hours or 72)),
            "note": note or "",
        }
        return self._post_json("/auth/desktop-sync-token", payload)

    def revoke_sync_token(self, token_id: str) -> Dict[str, Any]:
        return self._post_json("/auth/desktop-sync-token/revoke", {"token_id": str(token_id)})

    def get_audit_logs(
        self,
        username: str = "",
        action: str = "",
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        params = {
            "page": max(1, int(page or 1)),
            "page_size": max(1, min(int(page_size or 50), 200)),
        }
        if username:
            params["username"] = username
        if action:
            params["action"] = action
        return self._get_json(f"/audit-logs?{urlencode(params)}")

    def get_permissions_catalog(self) -> Dict[str, Any]:
        return self._get_json("/permissions/catalog")

    def _post_json(self, route_path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("Backend-URL ist nicht konfiguriert")
        url = f"{self.config.normalized_base_url}{route_path}"
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            _require_http_scheme(url),
            data=body,
            method="POST",
            headers=self._headers(content_type="application/json"),
        )
        try:
            with request.urlopen(req, timeout=self.config.connect_timeout_seconds) as response:  # nosec B310: URL scheme validated by _require_http_scheme
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Sync-Aufruf fehlgeschlagen ({exc.code}): {detail}") from exc
        except (error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"Sync-Aufruf fehlgeschlagen: {exc}") from exc

    def _get_json(self, route_path: str) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("Backend-URL ist nicht konfiguriert")
        url = f"{self.config.normalized_base_url}{route_path}"
        req = request.Request(_require_http_scheme(url), method="GET", headers=self._headers())
        try:
            with request.urlopen(req, timeout=self.config.connect_timeout_seconds) as response:  # nosec B310: URL scheme validated by _require_http_scheme
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Sync-Aufruf fehlgeschlagen ({exc.code}): {detail}") from exc
        except (error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"Sync-Aufruf fehlgeschlagen: {exc}") from exc

    def _headers(self, content_type: str | None = None) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if content_type:
            headers["Content-Type"] = content_type
        token = (self.config.access_token or "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers


class DataAccessRouter:
    """
    Translational Layer fuer den Desktop-Client:
    - entscheidet pro Laufzeit zwischen lokalem SQLite und Backend-Zugriff
    - laesst lokale Schreibfaelle immer zu (offline/local-only)
    - puffert lokale Aenderungen fuer spaetere Synchronisation (Outbox)
    """

    def __init__(
        self,
        local_db: LocalSyncOutbox,
        operating_mode: OperatingMode,
        api_client: Optional[BackendApiClient] = None,
    ):
        self.local_db = local_db
        self.operating_mode = operating_mode
        self.api_client = api_client

    def resolve_effective_mode(self) -> Tuple[OperatingMode, str]:
        if self.operating_mode == OperatingMode.LOCAL_ONLY:
            return OperatingMode.LOCAL_ONLY, "local-only konfiguriert"

        if self.api_client is None or not self.api_client.is_configured():
            if self.operating_mode == OperatingMode.HYBRID_SYNC:
                return OperatingMode.LOCAL_ONLY, "kein Backend konfiguriert (hybrid fallback)"
            return OperatingMode.REMOTE_ONLY, "kein Backend konfiguriert"

        backend_ok = self.api_client.check_health()
        if backend_ok:
            return self.operating_mode, "Backend erreichbar"

        if self.operating_mode == OperatingMode.HYBRID_SYNC:
            return OperatingMode.LOCAL_ONLY, "Backend nicht erreichbar (hybrid fallback)"
        return OperatingMode.REMOTE_ONLY, "Backend nicht erreichbar"

    def route_local_write(
        self,
        entity_name: str,
        operation: str,
        payload: Dict[str, Any],
        dedupe_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Registriert lokale Schreiboperation fuer spaeteren Sync.
        Der eigentliche Fach-Write findet weiterhin im lokalen DB-Layer statt.
        """
        outbox_id = self.local_db.record_sync_outbox(
            entity_name=entity_name,
            operation=operation,
            payload=payload,
            dedupe_key=dedupe_key,
        )
        return {"queued": True, "outbox_id": outbox_id}
