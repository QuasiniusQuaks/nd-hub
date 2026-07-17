"""Backward-compatible import path for the setup wizard.

Issue #67: implementation lives in ``ui.dialogs.setup_wizard``.
"""
from ui.dialogs.setup_wizard import SetupWizardDialog

__all__ = ["SetupWizardDialog"]
