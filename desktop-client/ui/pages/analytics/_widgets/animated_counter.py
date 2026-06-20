"""Animated-Counter-Widget — Zahl rollt von 0 auf Zielwert.

Verwendet QPropertyAnimation für eine smooth 600ms-Animation.
Apple-Health-Style Number-Counter.

Issue #42 Phase 1 — Wow-Details.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets


class AnimatedCounter(QtWidgets.QLabel):
    """QLabel, das seinen Zahlenwert von 0 auf target animiert.

    Animiert die Anzeige über eine QPropertyAnimation auf einer
    internen `displayValue`-Property. Bei jedem Frame wird der
    Wert als formatierter String gesetzt.
    """

    displayValueChanged = QtCore.Signal(float)

    def __init__(self, target: int | float = 0, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._target = float(target)
        self._display_value = 0.0
        self._animation: QtCore.QPropertyAnimation | None = None
        self._update_text()

    def _get_display_value(self) -> float:
        return self._display_value

    def _set_display_value(self, value: float) -> None:
        self._display_value = value
        self._update_text()
        self.displayValueChanged.emit(value)

    displayValue = QtCore.Property(float, _get_display_value, _set_display_value)

    def animate_to(self, target: int | float, duration_ms: int = 600) -> None:
        """Startet die Animation von aktuellem Wert zu `target`."""
        self._target = float(target)
        if self._animation is not None:
            self._animation.stop()

        self._animation = QtCore.QPropertyAnimation(self, b"displayValue")
        self._animation.setDuration(duration_ms)
        self._animation.setStartValue(self._display_value)
        self._animation.setEndValue(self._target)
        # Easing: OutCubic für degressive Abbremsung (natürliches Gefühl)
        self._animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self._animation.start()

    def set_target(self, target: int | float) -> None:
        """Setzt den Zielwert sofort (ohne Animation)."""
        self._target = float(target)
        self._display_value = float(target)
        self._update_text()

    def _update_text(self) -> None:
        """Formatiert den Display-Wert als String."""
        if self._target == int(self._target):
            self.setText(str(int(self._display_value)))
        else:
            self.setText(f"{self._display_value:.1f}")
