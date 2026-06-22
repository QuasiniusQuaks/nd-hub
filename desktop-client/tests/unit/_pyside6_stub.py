"""PySide6-Stub für Test-Umgebungen ohne Qt-Installation.

Desktop-Client-Module importieren PySide6 am Top-Level, aber für
reine DB-/Logic-Tests brauchen wir Qt nicht. Dieser Stub liefert
MagicMock-Objekte für alles, sodass die Imports durchlaufen.
"""
import sys
import unittest.mock


def install_pyside6_stub() -> None:
    """Installiert einen PySide6-Stub im sys.modules."""
    if "PySide6" in sys.modules:
        return
    pyside6 = unittest.mock.MagicMock()
    pyside6.QtCore = unittest.mock.MagicMock()
    pyside6.QtWidgets = unittest.mock.MagicMock()
    pyside6.QtGui = unittest.mock.MagicMock()
    pyside6.QtNetwork = unittest.mock.MagicMock()
    pyside6.QtSvg = unittest.mock.MagicMock()
    sys.modules["PySide6"] = pyside6
    sys.modules["PySide6.QtCore"] = pyside6.QtCore
    sys.modules["PySide6.QtWidgets"] = pyside6.QtWidgets
    sys.modules["PySide6.QtGui"] = pyside6.QtGui
    sys.modules["PySide6.QtNetwork"] = pyside6.QtNetwork
    sys.modules["PySide6.QtSvg"] = pyside6.QtSvg


# Auto-install beim Import
install_pyside6_stub()
