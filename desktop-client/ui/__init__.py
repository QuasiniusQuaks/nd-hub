"""UI Package - Setzt den sys.path, damit Imports aus dem Hauptverzeichnis funktionieren."""
import os
import sys

# Das Hauptverzeichnis (V35/) muss im sys.path sein, damit db_manager, icon_manager etc. 
# von den Untermodulen importiert werden können
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
