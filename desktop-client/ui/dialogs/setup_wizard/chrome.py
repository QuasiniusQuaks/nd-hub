"""Window chrome: backdrop, resize, show/close events."""
from __future__ import annotations

import logging

from PySide6 import QtCore, QtGui, QtWidgets

logger = logging.getLogger("ND-Hub")


class ChromeMixin:
    """Issue #67: dialog chrome extracted from setup_wizard_dialog monolith."""

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        try:
            self._persist_progress()
        except Exception:
            logger.exception("SetupWizard: persistieren beim Schließen fehlgeschlagen")
        if not (self.windowFlags() & QtCore.Qt.Widget):
            self._hide_backdrop()
        super().closeEvent(event)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self._resize_for_screen_ratio()
        if self.windowFlags() & QtCore.Qt.Widget:
            # Eingebettet im Overlay-Host: Verdunkelung übernimmt der Host.
            return
        self._show_backdrop()
        parent = self.parentWidget()
        if parent is not None:
            geo = parent.geometry()
            self.move(
                geo.x() + (geo.width() - self.width()) // 2,
                geo.y() + (geo.height() - self.height()) // 2,
            )

    def _resize_for_screen_ratio(self, ratio: float = 0.92) -> None:
        ratio = min(max(ratio, 0.1), 1.0)
        available_geo: QtCore.QRect | None = None
        parent = self.parentWidget()
        if parent is not None and parent.windowHandle() is not None and parent.windowHandle().screen() is not None:
            available_geo = parent.windowHandle().screen().availableGeometry()
        elif self.windowHandle() is not None and self.windowHandle().screen() is not None:
            available_geo = self.windowHandle().screen().availableGeometry()
        else:
            screen = QtGui.QGuiApplication.primaryScreen()
            if screen is not None:
                available_geo = screen.availableGeometry()
        if available_geo is None:
            return
        max_width = int(available_geo.width() * ratio)
        max_height = int(available_geo.height() * ratio)
        if max_width <= 0 or max_height <= 0:
            return

        # Erzwinge ein breites 16:9-Layout und nutze dabei so viel Platz wie moeglich.
        target_width = max_width
        target_height = int(target_width * 9 / 16)
        if target_height > max_height:
            target_height = max_height
            target_width = int(target_height * 16 / 9)

        target_width = max(self.minimumWidth(), target_width)
        target_height = max(self.minimumHeight(), target_height)
        target_width = min(target_width, available_geo.width())
        target_height = min(target_height, available_geo.height())
        self.resize(target_width, target_height)

    def _show_backdrop(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        if self._backdrop is None:
            self._backdrop = QtWidgets.QWidget(parent)
            self._backdrop.setStyleSheet("background-color: rgba(0, 0, 0, 70);")
            self._backdrop.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self._backdrop.setGeometry(parent.rect())
        self._backdrop.show()
        self._backdrop.raise_()
        self.raise_()

    def _hide_backdrop(self) -> None:
        if self._backdrop is not None:
            self._backdrop.hide()


