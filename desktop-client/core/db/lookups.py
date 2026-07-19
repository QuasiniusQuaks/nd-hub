"""Cached Name/ID-Lookups. Issue #66 Phase 4."""
from __future__ import annotations

from core.cache_helpers import cached_method


class LookupsMixin:
    """Lookup-Helfer mit TTL-Cache. Erwartet ``self.cur``."""

    @cached_method(ttl_seconds=300, maxsize=128)
    def get_depot_name(self, depot_id):
        row = self.cur.execute("SELECT name FROM depots WHERE id=?", (depot_id,)).fetchone()
        return row[0] if row else None

    @cached_method(ttl_seconds=300, maxsize=256)
    def get_praeparat_name(self, praeparat_id):
        row = self.cur.execute("SELECT name FROM praeparate WHERE id=?", (praeparat_id,)).fetchone()
        return row[0] if row else None

    @cached_method(ttl_seconds=300, maxsize=128)
    def get_all_praeparate_names(self):
        return [row[0] for row in self.cur.execute("SELECT name FROM praeparate ORDER BY name").fetchall()]

    @cached_method(ttl_seconds=300, maxsize=128)
    def get_all_depot_names(self):
        return [row[0] for row in self.cur.execute("SELECT name FROM depots ORDER BY name").fetchall()]

    @cached_method(ttl_seconds=300, maxsize=256)
    def get_depot_id_by_name(self, name):
        row = self.cur.execute("SELECT id FROM depots WHERE name=?", (name,)).fetchone()
        return row[0] if row else None

    @cached_method(ttl_seconds=300, maxsize=256)
    def get_praeparat_id_by_name(self, name):
        row = self.cur.execute("SELECT id FROM praeparate WHERE name=?", (name,)).fetchone()
        return row[0] if row else None

