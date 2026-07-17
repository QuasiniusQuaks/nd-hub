"""Shared Permissions catalog router (Issues #60/#61)."""

from fastapi import APIRouter, Depends


def create_permissions_router(
    get_current_session,
    *,
    permission_definitions,
    default_user_permissions,
    permission_templates,
) -> APIRouter:
    router = APIRouter(prefix="/permissions", tags=["permissions"])

    @router.get("/catalog")
    def permissions_catalog(session=Depends(get_current_session)) -> dict:
        _ = session
        return {
            "rows": permission_definitions,
            "default_user_permissions": sorted(default_user_permissions),
            "templates": permission_templates,
        }

    return router
