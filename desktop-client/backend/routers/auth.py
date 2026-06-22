"""Auth-Router — re-exportiert shared/routers/auth.py.

Issue #65 — Code-Duplikation eliminiert, beide Backends nutzen shared/.
"""
from shared.routers.auth import create_auth_router

__all__ = ["create_auth_router"]
