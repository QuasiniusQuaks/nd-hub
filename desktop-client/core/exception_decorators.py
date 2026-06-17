# -*- coding: utf-8 -*-
"""Decorator für defensive Exception-Behandlung im Desktop-Client.

Dieses Modul bietet wiederverwendbare Decorators, die das in der ND-Hub
Codebase häufige Anti-Pattern ``except Exception as e: logger.error(...);
pass`` durch eine deklarative Form ersetzen.

Hintergrund (Issue #16, Audit 2026-06):
    Im Desktop-Client existieren ~107 Vorkommen von
    ``except Exception as e: logger.error(...)``. Das ist defensiv oft
    nötig (UI darf nicht abstürzen), aber es führt zu:

    - Unklarer Logging-Konvention (manchmal logger.error, manchmal logger.warning)
    - Verlorenem Traceback in vielen Fällen (``logger.error(str(e))`` statt
      ``logger.exception(...)``)
    - Keine zentrale Telemetrie — Fehler werden stillschweigend geschluckt

    Die ``swallow_exceptions``-Decorator-Familie bietet eine deklarative
    Alternative: Logging-Level, Log-Message, Default-Returnwert und ob der
    Traceback mitgeloggt werden soll, werden am Decorator-Aufruf klar
    dokumentiert statt im try/except-Block versteckt.

Migration:
    Alt::

        def refresh_widget(self) -> None:
            try:
                self._do_refresh()
            except Exception as e:
                logger.error(f"Refresh fehlgeschlagen: {e}")

    Neu::

        @swallow_exceptions(default=None, message="Refresh fehlgeschlagen")
        def refresh_widget(self) -> Optional[Widget]:
            return self._do_refresh()

Wichtig:
    Diese Decorators sind für **defensive** UI-Pfade gedacht, wo ein
    Crash teurer wäre als ein verschluckter Fehler. Für kritische Pfade
    (Auth, Backup, DB-Migration) bitte weiterhin explizite try/except
    mit spezifischen Exception-Typen verwenden.
"""
from __future__ import annotations

import functools
import inspect
import logging
from typing import Any, Callable, Optional, Type, TypeVar, Union

logger = logging.getLogger("ND-Hub.ExceptionDecorators")

F = TypeVar("F", bound=Callable[..., Any])


def swallow_exceptions(
    *exception_types: Type[BaseException],
    default: Any = None,
    message: str = "Fehler in {}",
    level: int = logging.ERROR,
    log_traceback: bool = True,
    reraise: bool = False,
) -> Callable[[F], F]:
    """Decorator: Fängt die angegebenen Exceptions ab und loggt sie.

    Args:
        exception_types: Exception-Klassen, die abgefangen werden sollen.
            Default: ``Exception`` (alle nicht-sytemischen Exceptions).
        default: Rückgabewert der dekorierten Funktion bei Exception.
        message: Log-Message. ``{}`` wird durch den Funktionsnamen ersetzt.
        level: Logging-Level (default: ERROR).
        log_traceback: Wenn True, wird der Traceback mitgeloggt
            (``logger.exception`` statt ``logger.error``).
        reraise: Wenn True, wird die Exception nach dem Logging erneut
            geworfen. Nützlich für Telemetrie-Hooks.

    Returns:
        Decorator, der die Funktion wrappt.

    Beispiel::

        @swallow_exceptions(default=False, message="Health-Check fehlgeschlagen")
        def is_healthy(self) -> bool:
            return self._ping_server()

        @swallow_exceptions(KeyError, default="unbekannt")
        def get_user_name(self, user_id: int) -> str:
            return self._users[user_id]
    """
    # Wenn keine Typen angegeben sind: alle nicht-systemischen Exceptions fangen
    if not exception_types:
        exception_types = (Exception,)

    def decorator(func: F) -> F:
        qualname = getattr(func, "__qualname__", func.__name__)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except exception_types as exc:
                log_msg = message.format(qualname)
                if log_traceback:
                    logger.log(level, "%s: %s", log_msg, exc, exc_info=True)
                else:
                    logger.log(level, "%s: %s", log_msg, exc)
                if reraise:
                    raise
                return default

        return wrapper  # type: ignore[return-value]

    return decorator


def swallow_ui_errors(default: Any = None) -> Callable[[F], F]:
    """Kurzform für UI-Refresh-Methoden, die nie crashen dürfen.

    Setzt ``level=WARNING`` und ``log_traceback=False`` für leiseres
    Logging, da UI-Fehler in der Regel schon durch Toast-Benachrichtigungen
    sichtbar sind.

    Beispiel::

        @swallow_ui_errors(default=[])
        def get_visible_rows(self) -> list:
            return self._filter_rows(self._all_rows())
    """
    return swallow_exceptions(
        default=default,
        message="UI-Operation {} fehlgeschlagen",
        level=logging.WARNING,
        log_traceback=False,
    )


__all__ = ["swallow_exceptions", "swallow_ui_errors"]