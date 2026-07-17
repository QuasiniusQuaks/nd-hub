"""Audit-Router — re-export shared/routers/audit.py (Issues #60/#61)."""
from shared.routers.audit import create_audit_router

__all__ = ["create_audit_router"]
