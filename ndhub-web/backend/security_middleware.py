"""HTTP security middleware wiring for ND-Hub web backend (Issue #96 / #31)."""

from __future__ import annotations

import os
from typing import Any

from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware


def apply_security_middleware(app: Any) -> None:
    """TrustedHost + CORS + baseline security response headers."""
    allowed_hosts_raw = os.environ.get("ND_HUB_ALLOWED_HOSTS", "*").strip()
    if allowed_hosts_raw == "*":
        allowed_hosts = ["*"]
    else:
        allowed_hosts = [h.strip() for h in allowed_hosts_raw.split(",") if h.strip()]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    cors_raw = os.environ.get("ND_HUB_CORS_ORIGINS", "").strip()
    cors_origins = [o.strip() for o in cors_raw.split(",") if o.strip()] if cors_raw else []
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    @app.middleware("http")
    async def _security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains",
            )
        return response
