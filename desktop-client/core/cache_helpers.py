"""Cache-Helper für ND-Hub: Wrapper um ``cachetools.TTLCache`` für Instanzmethoden.

Hintergrund (Issue #17, Audit 2026-06):
    ``functools.lru_cache`` auf Instanz-Methoden hat zwei Probleme:

    1. ``self`` ist Teil des Cache-Keys → jede Instanz hat ihren eigenen
       Cache, was bei vielen kurzlebigen Instanzen zu Memory-Leaks führt.
    2. Kein TTL → veraltete Werte bleiben potenziell ewig im Cache.

    ``cachetools.TTLCache`` bietet TTL + maxsize. Allerdings hat es ein
    anderes API als ``lru_cache``: Decorator auf Methoden erfordert ein
    bisschen Boilerplate (Cache-Objekt pro Instanz muss verwaltet werden).

    Dieses Modul bietet zwei Wege:

    - ``cached_method(ttl_seconds, maxsize)``: Decorator für
      Instanzmethoden, der pro Instanz einen Cache automatisch anlegt.
    - ``clear_method_cache(instance, method_name)``: Cache einer Methode
      manuell leeren (z.B. nach DB-Mutation).

    Beispiel::

        class Database:
            @cached_method(ttl_seconds=60, maxsize=128)
            def get_user(self, user_id: int) -> User:
                return self._query_user(user_id)

        # Nach Mutation:
        clear_method_cache(db, "get_user")
"""
from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar

try:
    from cachetools import TTLCache
    HAS_CACHETOOLS = True
except ImportError:  # pragma: no cover
    HAS_CACHETOOLS = False
    TTLCache = None  # type: ignore[assignment,misc]

F = TypeVar("F", bound=Callable[..., Any])

# Cache-Storage: id(instance) → {method_name → TTLCache}
# id(instance) ist sicher, weil wir weakref nicht brauchen —
# bei GC der Instanz wird auch der Cache per weakref cleanup.
import weakref

_METHOD_CACHES: weakref.WeakKeyDictionary[Any, dict[str, Any]] = weakref.WeakKeyDictionary()


def cached_method(
    ttl_seconds: int = 60,
    maxsize: int = 128,
) -> Callable[[F], F]:
    """Decorator für Instanzmethoden mit TTL-Cache.

    Args:
        ttl_seconds: Wie lange ein Eintrag maximal gültig bleibt.
        maxsize: Maximale Anzahl Einträge im Cache (LRU-Eviction).

    Returns:
        Decorator, der die Methode wrappt.

    Falls ``cachetools`` nicht installiert ist, wird die Methode
    unverändert zurückgegeben (kein Caching) — das verhindert Import-Errors
    in Entwicklungsumgebungen, die das Dependency noch nicht haben.
    """
    if not HAS_CACHETOOLS:
        # Graceful degradation: kein Cache, aber Funktion bleibt funktional
        def decorator(func: F) -> F:
            @functools.wraps(func)
            def wrapper(self, *args: Any, **kwargs: Any) -> Any:
                return func(self, *args, **kwargs)
            wrapper.__wrapped__ = func  # type: ignore[attr-defined]
            return wrapper  # type: ignore[return-value]
        return decorator

    def decorator(func: F) -> F:
        method_name = func.__name__

        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Cache pro Instanz
            if self not in _METHOD_CACHES:
                _METHOD_CACHES[self] = {}
            instance_caches = _METHOD_CACHES[self]

            if method_name not in instance_caches:
                # TTLCache ist zur Laufzeit garantiert nicht None,
                # weil wir nur in diesen Branch kommen wenn HAS_CACHETOOLS True ist
                instance_caches[method_name] = TTLCache(  # type: ignore[misc]
                    maxsize=maxsize, ttl=ttl_seconds
                )
            cache = instance_caches[method_name]

            # Key muss hashbar sein — kwargs kommen als Dict und sind nicht hashbar
            key = (args, tuple(sorted(kwargs.items())))

            if key not in cache:
                cache[key] = func(self, *args, **kwargs)
            return cache[key]

        wrapper.__wrapped__ = func  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator


def clear_method_cache(instance: Any, method_name: str) -> None:
    """Leert den Cache einer Methode auf einer Instanz.

    Aufruf typischerweise nach ``INSERT``/``UPDATE``/``DELETE``-Operationen,
    damit der nächste Aufruf frische Daten lädt.
    """
    if instance in _METHOD_CACHES:
        _METHOD_CACHES[instance].pop(method_name, None)


def clear_all_caches(instance: Any) -> None:
    """Leert alle Method-Caches einer Instanz."""
    if instance in _METHOD_CACHES:
        _METHOD_CACHES[instance].clear()


def cache_info(instance: Any, method_name: str) -> dict[str, int]:
    """Liefert Cache-Statistiken für eine Methode (hits/misses/Größe)."""
    if HAS_CACHETOOLS and instance in _METHOD_CACHES:
        cache = _METHOD_CACHES[instance].get(method_name)
        if cache is not None:
            currsize = len(cache)
            # TTLCache hat kein offizielles hits/misses-API,
            # wir nutzen die manuelle Größe als Indikator
            return {"size": currsize, "maxsize": cache.maxsize}
    return {"size": 0, "maxsize": 0}


__all__ = [
    "cached_method",
    "clear_method_cache",
    "clear_all_caches",
    "cache_info",
    "HAS_CACHETOOLS",
]
