"""Shared Audit-Logs-Router (Issues #60/#61)."""

from fastapi import APIRouter, Depends


def create_audit_router(
    repository,
    require_permission,
) -> APIRouter:
    router = APIRouter(tags=["audit"])

    @router.get("/audit-logs")
    def list_audit_logs(
        limit: int = 100,
        offset: int = 0,
        q: str = "",
        action: str = "",
        resource_type: str = "",
        session=Depends(require_permission("audit_view")),
    ) -> list[dict]:
        _ = session
        return repository.list_audit_logs(
            limit=limit,
            offset=offset,
            q=q,
            action=action,
            resource_type=resource_type,
        )

    return router
