"""Users-Router — re-export shared/routers/users.py (Issues #60/#61/#65)."""
from shared.routers.users import create_users_router

__all__ = ["create_users_router"]
