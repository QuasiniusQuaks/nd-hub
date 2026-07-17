"""FastAPI app entry for ND-Hub desktop backend.

Issue #60/#61: thin module — factory lives in app_factory.py.
Re-exports create_app + models/helpers for tests and monkeypatch.
"""

from backend.app_factory import create_app
from backend.helpers import *  # noqa: F403
from backend.models import *  # noqa: F403

__all__ = ["create_app"]
