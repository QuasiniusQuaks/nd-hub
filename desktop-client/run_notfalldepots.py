#!/usr/bin/env python3
"""
ND-Hub – Startskript für Linux
===============================
Startet die Hauptanwendung.

WICHTIG: Alle Daten (Datenbank, Anhänge, Backups, Logs) liegen NICHT
in diesem Quellcode-Verzeichnis, sondern werden automatisch nach
~/ND-Hub/ umgeleitet (siehe nd_hub.get_data_dir()).
"""

import sys
import os
import subprocess

# --- AUTO-VENV BOOTSTRAP ---
def _ensure_venv():
    """Stellt sicher, dass die Anwendung in der virtuellen Umgebung läuft."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(script_dir, ".venv", "bin", "python3")
    
    # Prüfen, ob wir bereits in einer VENV sind (sys.prefix != sys.base_prefix)
    # Oder ob die VENV-Python-Datei gar nicht existiert
    in_venv = sys.prefix != sys.base_prefix
    
    if os.path.exists(venv_python) and not in_venv:
        # Re-execute mit VENV-Python
        print(f"[*] Starte ND-Hub in virtueller Umgebung: {venv_python}")
        os.execv(venv_python, [venv_python] + sys.argv)

_ensure_venv()
# ---------------------------

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now run the main application
if __name__ == "__main__":
    from nd_hub import MainWindow, config
    from PySide6 import QtWidgets
    from ui.dialogs.embedded_dialog_host import install_embedded_dialog_patches
    
    # ---------------------------------------------------------------
    # Konfiguration wird automatisch über den ConfigManager geladen.
    # Siehe core/config_manager.py und nd_hub.py.
    # ---------------------------------------------------------------
    
    # Create application
    app = QtWidgets.QApplication(sys.argv)
    install_embedded_dialog_patches()
    
    # Apply Apple theme
    from apple_theme import AppleTheme
    app.setStyleSheet(AppleTheme.get_stylesheet())
    
    # Create and show main window
    win = MainWindow(config)
    win.showFullScreen()
    
    # Run application
    sys.exit(app.exec())