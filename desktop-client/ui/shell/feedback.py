"""MainWindow shell helpers (Issue #93)."""
from __future__ import annotations

import logging

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt

logger = logging.getLogger("ND-Hub")

def _setup_feedback_layers(self) -> None:
    """Initialisiert Busy-Overlay und Toast-Container."""
    self._active_toasts = []
    self._busy_operation_seq = 0
    self._busy_delay_timer = QtCore.QTimer(self)
    self._busy_delay_timer.setSingleShot(True)

    self.busy_overlay = QtWidgets.QWidget(self.right_container)
    self.busy_overlay.setObjectName("page_busy_overlay")
    busy_layout = QtWidgets.QVBoxLayout(self.busy_overlay)
    busy_layout.setContentsMargins(24, 24, 24, 24)
    busy_layout.addStretch()

    self._busy_card_frame = QtWidgets.QFrame()
    self._busy_card_frame.setObjectName("busy_card")
    self._busy_card_frame.setMaximumWidth(360)
    card_layout = QtWidgets.QVBoxLayout(self._busy_card_frame)
    card_layout.setSpacing(10)
    self.busy_label = QtWidgets.QLabel("Seite wird geladen ...")
    card_layout.addWidget(self.busy_label)

    self.busy_hint_label = QtWidgets.QLabel("Bitte einen Moment Geduld.")
    card_layout.addWidget(self.busy_hint_label)

    self.busy_progress = QtWidgets.QProgressBar()
    self.busy_progress.setRange(0, 0)
    self.busy_progress.setTextVisible(False)
    card_layout.addWidget(self.busy_progress)

    busy_layout.addWidget(self._busy_card_frame, alignment=Qt.AlignHCenter)
    busy_layout.addStretch()
    self.busy_overlay.hide()

    self.toast_container = QtWidgets.QWidget(self.right_container)
    self.toast_container.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
    self.toast_container.setStyleSheet("background: transparent;")
    self.toast_container.hide()
    self._update_feedback_layer_geometry()


def _update_feedback_layer_geometry(self) -> None:
    if hasattr(self, "right_container"):
        rect = self.right_container.rect()
        if hasattr(self, "busy_overlay"):
            self.busy_overlay.setGeometry(rect)
        if hasattr(self, "toast_container"):
            self.toast_container.setGeometry(rect)
            self._reflow_toasts()


def _show_page_busy(self, message: str) -> None:
    if hasattr(self, "busy_label"):
        self.busy_label.setText(message)
    if hasattr(self, "busy_overlay"):
        self._update_feedback_layer_geometry()
        self.busy_overlay.raise_()
        self.busy_overlay.show()
        self.busy_overlay.repaint()


def _hide_page_busy(self) -> None:
    if hasattr(self, "busy_overlay"):
        self.busy_overlay.hide()


def _begin_busy_operation(self, message: str, delay_ms: int = 120) -> int:
    """
    Startet einen verzögerten Busy-Indicator.
    Der Overlay wird nur angezeigt, wenn die Aktion länger als delay_ms dauert.
    """
    self._busy_operation_seq += 1
    op_id = self._busy_operation_seq
    if delay_ms <= 0:
        self._show_page_busy(message)
        return op_id
    if hasattr(self, "_busy_delay_timer"):
        self._busy_delay_timer.stop()
        try:
            self._busy_delay_timer.timeout.disconnect()
        except (RuntimeError, TypeError):
            logger.debug("Busy-Timer-Signal war bereits getrennt — kein Disconnect nötig.")

        def _show_if_still_running():
            if op_id == self._busy_operation_seq:
                self._show_page_busy(message)

        self._busy_delay_timer.timeout.connect(_show_if_still_running)
        self._busy_delay_timer.start(delay_ms)
    return op_id


def _end_busy_operation(self, op_id: int) -> None:
    """Beendet eine Busy-Operation sicher ohne visuelles Blinken."""
    if op_id != getattr(self, "_busy_operation_seq", -1):
        return
    if hasattr(self, "_busy_delay_timer"):
        self._busy_delay_timer.stop()
        try:
            self._busy_delay_timer.timeout.disconnect()
        except (RuntimeError, TypeError):
            logger.debug("Busy-Timer-Signal war bereits getrennt — kein Disconnect nötig.")
    self._hide_page_busy()


def show_toast(self, message: str, level: str = "info", duration_ms: int = 2600) -> None:
    """Zeigt unaufdringliches Toast-Feedback oben rechts."""
    if not hasattr(self, "toast_container"):
        return
    palette = {
        "success": ("#ecfdf3", "#166534", "#86efac"),
        "warning": ("#fffbeb", "#92400e", "#fcd34d"),
        "error": ("#fef2f2", "#991b1b", "#fca5a5"),
        "info": ("#eff6ff", "#1d4ed8", "#93c5fd"),
    }
    bg, fg, border = palette.get(level, palette["info"])

    # QWidget statt QFrame: globales QFrame-Theme + Stylesheet-Border wirkten wie doppelter Rahmen.
    toast = QtWidgets.QWidget(self.toast_container)
    toast.setObjectName("toast_bubble")
    toast.setStyleSheet(
        f"QWidget#toast_bubble {{"
        f"background-color: {bg};"
        f"color: {fg};"
        f"border: 1px solid {border};"
        "border-radius: 8px;"
        "}}"
    )
    toast_layout = QtWidgets.QHBoxLayout(toast)
    toast_layout.setContentsMargins(12, 8, 12, 8)
    toast_layout.setSpacing(8)
    label = QtWidgets.QLabel(message)
    label.setWordWrap(True)
    label.setStyleSheet(
        f"color: {fg}; font-size: 12px; font-weight: 600; background: transparent; border: none;"
    )
    toast_layout.addWidget(label)
    toast.setMaximumWidth(440)
    toast.adjustSize()

    self._active_toasts.append(toast)
    self.toast_container.show()
    toast.show()
    self._reflow_toasts()

    QtCore.QTimer.singleShot(duration_ms, lambda t=toast: self._remove_toast(t))


def _remove_toast(self, toast: QtWidgets.QWidget) -> None:
    if toast in getattr(self, "_active_toasts", []):
        self._active_toasts.remove(toast)
    toast.hide()
    toast.deleteLater()
    self._reflow_toasts()
    if hasattr(self, "toast_container") and not self._active_toasts:
        self.toast_container.hide()


def _reflow_toasts(self) -> None:
    if not hasattr(self, "toast_container"):
        return
    x_margin = 16
    y = 16
    max_width = min(440, max(260, self.toast_container.width() - 32))
    for toast in reversed(self._active_toasts):
        toast.setFixedWidth(max_width)
        toast.adjustSize()
        height = toast.sizeHint().height()
        x = max(8, self.toast_container.width() - toast.width() - x_margin)
        toast.setGeometry(x, y, toast.width(), height)
        y += height + 10

