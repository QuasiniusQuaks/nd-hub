"""
ND-Hub – Die ND-Hub-Verwaltung – Modern UI Edition 2025

Thin entry module (Issue #93). Shell implementation: ``ui.shell``.
Public API for ``run_notfalldepots.py``: ``MainWindow``, ``config``.
"""
from __future__ import annotations

import faulthandler
import os
import sys

from apple_theme import AppleTheme
from core.config_manager import ConfigManager
from core.error_handler import setup_global_error_handler
from PySide6 import QtWidgets
from ui.dialogs.embedded_dialog_host import install_embedded_dialog_patches
from ui.shell import UI, VERSION, Cache, MainWindow, PageIndex
from ui.shell.logging_setup import configure_app_logging

faulthandler.enable()

# Initialisiere Konfiguration (vor dem Logging)
config = ConfigManager()
DATA_DIR = config.data_dir

# NumExpr-Hinweis unterdrücken und Thread-Anzahl explizit setzen
os.environ.setdefault("NUMEXPR_MAX_THREADS", "8")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "8")

logger, perf_logger = configure_app_logging(config)

# Re-exports for existing imports
__all__ = [
    "MainWindow",
    "VERSION",
    "UI",
    "Cache",
    "PageIndex",
    "config",
    "DATA_DIR",
    "logger",
    "perf_logger",
]


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    install_embedded_dialog_patches()
    app.setApplicationName("ND-Hub")
    app.setOrganizationName("ND-Hub Enterprise")

    error_handler = setup_global_error_handler(app)

    db_path = config.get_db_path()
    db_dir = os.path.dirname(db_path)
    if not db_dir:
        db_dir = "."

    if not os.path.exists(db_dir):
        QtWidgets.QMessageBox.critical(
            None,
            "Fehler",
            (
                f"Der Speicherort der Datenbank ist nicht erreichbar!\n\nPfad: {db_path}\n\n"
                "Bitte stellen Sie sicher, dass:\n"
                "1. Das Laufwerk oder das Netzwerk verbunden ist\n"
                "2. Sie Zugriff auf den Ordner haben"
            ),
        )
        sys.exit(1)

    app.setStyleSheet(AppleTheme.get_stylesheet())

    win = MainWindow(config)
    win.showMaximized()

    sys.exit(app.exec())
