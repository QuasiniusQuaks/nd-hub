"""Dashboard package (Issue #93)."""
from .page import AppleDashboard
from .widgets import (
    CollapsibleSection,
    CompletionRing,
    StatusBadge,
    TrackingCard,
    create_card_widget,
)

__all__ = [
    "AppleDashboard",
    "StatusBadge",
    "CompletionRing",
    "TrackingCard",
    "CollapsibleSection",
    "create_card_widget",
]
