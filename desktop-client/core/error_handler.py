# -*- coding: utf-8 -*-
import sys
import traceback
import logging
from PySide6 import QtWidgets, QtCore
from ui.dialogs.embedded_dialog_host import exec_embedded_dialog

logger = logging.getLogger("ND-Hub.ErrorHandler")

class GlobalErrorHandler(QtCore.QObject):
    """Globaler Error-Handling Mechanismus für PySide6 Anwendungen."""
    
    error_occurred = QtCore.Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Hook sys.excepthook
        sys.excepthook = self.handle_exception
        self.error_occurred.connect(self.show_error_dialog)

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """Wird bei unbehandelten Python-Exceptions aufgerufen."""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # Stacktrace formatieren
        err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.critical(f"Unbehandelte Exception:\n{err_msg}")

        # Signal an UI-Thread senden (falls der Fehler in einem Worker-Thread auftrat)
        short_msg = f"{exc_type.__name__}: {exc_value}"
        self.error_occurred.emit(short_msg, err_msg)

    @QtCore.Slot(str, str)
    def show_error_dialog(self, short_msg, full_traceback):
        """Zeigt einen benutzerfreundlichen Fehlerdialog an."""
        msg_box = QtWidgets.QMessageBox()
        msg_box.setIcon(QtWidgets.QMessageBox.Critical)
        msg_box.setWindowTitle("Unerwarteter Fehler")
        msg_box.setText("Es ist ein kritischer Fehler aufgetreten.")
        msg_box.setInformativeText(short_msg)
        msg_box.setDetailedText(full_traceback)
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        
        # Sicherstellen, dass Dialog immer im Vordergrund ist
        msg_box.setWindowFlags(msg_box.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        exec_embedded_dialog(self.parent(), msg_box)

def setup_global_error_handler(app):
    """Initialisiert den globalen Error Handler."""
    return GlobalErrorHandler(app)
