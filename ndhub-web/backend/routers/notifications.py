"""notifications router re-export from shared (Issues #60/#61)."""
from shared.routers.notifications import create_notifications_router

__all__ = ["create_notifications_router"]
