"""SQL dialect helpers + shared query fragments (Issue #70).

Both SqliteRepository and MariaDbRepository use mostly the same SQL shapes;
placeholders differ (`?` vs `%s`). Shared fragments keep SELECT/INSERT bodies
in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PlaceholderStyle(str, Enum):
    QMARK = "qmark"  # SQLite
    PYFORMAT = "pyformat"  # pymysql %s


@dataclass(frozen=True)
class SqlDialect:
    style: PlaceholderStyle

    @property
    def ph(self) -> str:
        return "?" if self.style is PlaceholderStyle.QMARK else "%s"

    def placeholders(self, count: int) -> str:
        return ", ".join(self.ph for _ in range(max(0, int(count))))

    def format(self, sql: str) -> str:
        """Replace ``{ph}`` markers with dialect placeholders."""
        return sql.replace("{ph}", self.ph)


SQLITE = SqlDialect(PlaceholderStyle.QMARK)
MYSQL = SqlDialect(PlaceholderStyle.PYFORMAT)

# --- Shared SELECT lists / simple statements ---

DEPOT_SELECT_COLUMNS = """
depots.id, depots.name, depots.adresse, depots.strasse, depots.hausnummer, depots.postleitzahl, depots.stadt, depots.telefon, depots.email,
depots.institution_id, depots.latitude, depots.longitude, institutions.name AS institution_name
""".strip()

SQL_GET_DEPOT = f"""
SELECT {DEPOT_SELECT_COLUMNS}
FROM depots
LEFT JOIN institutions ON institutions.id = depots.institution_id
WHERE depots.id = {{ph}}
"""

SQL_GET_DEPOT_NAME = """
SELECT name FROM depots WHERE id = {ph}
"""

SQL_LIST_PRAEPARATE = """
SELECT id, name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller
FROM praeparate
WHERE {ph} = '%%' OR name LIKE {ph}
ORDER BY name
LIMIT {ph} OFFSET {ph}
"""

SQL_GET_PRAEPARAT = """
SELECT id, name, wirkstoff, darreichungsform, staerke, einheit, pzn, hersteller
FROM praeparate
WHERE id = {ph}
"""

SQL_DELETE_DEPOT = """
DELETE FROM depots WHERE id = {ph}
"""

SQL_DELETE_PRAEPARAT = """
DELETE FROM praeparate WHERE id = {ph}
"""

SQL_DELETE_INSTITUTION = """
DELETE FROM institutions WHERE id = {ph}
"""

SQL_GET_KONTAKT = """
SELECT id, depot_id, name, rolle, telefon, email, notizen
FROM kontakte
WHERE id = {ph}
"""

SQL_DELETE_KONTAKT = """
DELETE FROM kontakte WHERE id = {ph}
"""

SQL_LIST_KONTAKTE = """
SELECT id, depot_id, name, rolle, telefon, email, notizen
FROM kontakte
ORDER BY name
LIMIT {ph} OFFSET {ph}
"""

ALLOWED_MOVEMENT_TYPES = frozenset({"Zugang", "Abgang", "Vernichtung"})
