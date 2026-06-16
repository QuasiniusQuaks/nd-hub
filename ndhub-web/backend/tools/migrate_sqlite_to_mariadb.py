"""Migrate ndhub data from SQLite to MariaDB.

Usage:
  python -m backend.tools.migrate_sqlite_to_mariadb --sqlite /data/nd_hub_backend.db
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import re
import sqlite3
from typing import Any, Iterable

from backend.config import resolve_mariadb_settings


def _quote_ident(name: str) -> str:
    if not name or not re.fullmatch(r"[A-Za-z0-9_]+", name):
        raise ValueError(f"Ungueltiger SQL-Bezeichner: {name!r}")
    return f"`{name}`"


def _sqlite_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """,
    ).fetchall()
    return [str(row[0]) for row in rows]


@dataclass
class ColumnDef:
    name: str
    sqlite_type: str
    notnull: bool
    default: str | None
    pk_ordinal: int


def _table_columns(conn: sqlite3.Connection, table: str) -> list[ColumnDef]:
    rows = conn.execute(
        "".join(["PRAGMA table_info(", _quote_ident(table), ")"])
    ).fetchall()
    result: list[ColumnDef] = []
    for row in rows:
        result.append(
            ColumnDef(
                name=str(row[1]),
                sqlite_type=str(row[2] or "TEXT"),
                notnull=bool(row[3]),
                default=row[4],
                pk_ordinal=int(row[5] or 0),
            ),
        )
    return result


def _map_sqlite_type(sqlite_type: str) -> str:
    t = (sqlite_type or "").upper()
    if "INT" in t:
        return "BIGINT"
    if "CHAR" in t or "CLOB" in t or "TEXT" in t:
        return "LONGTEXT"
    if "BLOB" in t:
        return "LONGBLOB"
    if "REAL" in t or "FLOA" in t or "DOUB" in t:
        return "DOUBLE"
    if "NUMERIC" in t or "DECIMAL" in t:
        return "DECIMAL(20,6)"
    if "DATE" in t and "TIME" in t:
        return "DATETIME"
    if "DATE" in t:
        return "DATE"
    if "TIME" in t:
        return "TIME"
    return "LONGTEXT"


def _create_table_sql(table: str, columns: list[ColumnDef]) -> str:
    pk_columns = [c for c in columns if c.pk_ordinal > 0]
    pk_columns = sorted(pk_columns, key=lambda c: c.pk_ordinal)
    pk_names = [c.name for c in pk_columns]
    single_integer_pk = (
        len(pk_columns) == 1 and "INT" in (pk_columns[0].sqlite_type or "").upper()
    )

    lines: list[str] = []
    for col in columns:
        col_type = _map_sqlite_type(col.sqlite_type)
        is_auto_pk = single_integer_pk and col.name == pk_columns[0].name
        nullable = "" if (col.notnull or is_auto_pk) else " NULL"
        not_null = " NOT NULL" if (col.notnull or is_auto_pk) else ""
        auto_increment = " AUTO_INCREMENT" if is_auto_pk else ""
        # Keep defaults simple; complex SQLite expressions are intentionally skipped.
        default = ""
        if col.default is not None and not is_auto_pk:
            raw = str(col.default).strip()
            if raw and raw.upper() != "NULL":
                default = f" DEFAULT {raw}"
        lines.append(
            f"  {_quote_ident(col.name)} {col_type}{not_null}{nullable}{default}{auto_increment}",
        )

    if pk_names:
        pk_sql = ", ".join(_quote_ident(name) for name in pk_names)
        lines.append(f"  PRIMARY KEY ({pk_sql})")

    line_block = ",\n".join(lines)
    return (
        f"CREATE TABLE IF NOT EXISTS {_quote_ident(table)} (\n"
        f"{line_block}\n"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    )


def _iter_rows(
    conn: sqlite3.Connection,
    table: str,
    columns: list[ColumnDef],
    batch_size: int,
) -> Iterable[list[tuple]]:
    quoted_cols = ", ".join(_quote_ident(col.name) for col in columns)
    sql = "".join(["SELECT ", quoted_cols, " FROM ", _quote_ident(table)])
    cursor = conn.execute(sql)
    batch: list[tuple] = []
    for row in cursor:
        batch.append(tuple(row))
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def _copy_table(
    sqlite_conn: sqlite3.Connection,
    maria_conn: Any,
    table: str,
    batch_size: int,
) -> None:
    columns = _table_columns(sqlite_conn, table)
    if not columns:
        return

    create_sql = _create_table_sql(table, columns)
    insert_cols = ", ".join(_quote_ident(col.name) for col in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    insert_sql = "".join(
        [
            "INSERT INTO ",
            _quote_ident(table),
            " (",
            insert_cols,
            ") VALUES (",
            placeholders,
            ")",
        ]
    )

    with maria_conn.cursor() as cur:
        cur.execute(create_sql)
        cur.execute("".join(["TRUNCATE TABLE ", _quote_ident(table)]))
        for batch in _iter_rows(sqlite_conn, table, columns, batch_size):
            cur.executemany(insert_sql, batch)
    maria_conn.commit()


def _count_rows_sqlite(conn: sqlite3.Connection, table: str) -> int:
    sql = "".join(["SELECT COUNT(*) FROM ", _quote_ident(table)])
    row = conn.execute(sql).fetchone()
    return int(row[0]) if row else 0


def _count_rows_mariadb(
    conn: Any,
    table: str,
) -> int:
    sql = "".join(["SELECT COUNT(*) FROM ", _quote_ident(table)])
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()
    return int(row[0]) if row else 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrates ND-Hub tables from SQLite to MariaDB.",
    )
    parser.add_argument(
        "--sqlite",
        required=True,
        help="Path to SQLite file",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Rows per MariaDB batch insert",
    )
    parser.add_argument(
        "--tables",
        default="",
        help="Comma-separated table allow-list (default: all tables)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur SQLite-Quelltabellen und Datensatzanzahlen pruefen, ohne MariaDB zu verbinden.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    batch_size = max(1, int(args.batch_size))
    table_allow = {
        entry.strip()
        for entry in (args.tables or "").split(",")
        if entry.strip()
    }

    sqlite_conn = sqlite3.connect(args.sqlite)
    sqlite_conn.row_factory = sqlite3.Row
    try:
        tables = _sqlite_tables(sqlite_conn)
        if table_allow:
            tables = [name for name in tables if name in table_allow]
        if not tables:
            raise SystemExit("Keine passenden Tabellen zur Migration gefunden.")

        if args.dry_run:
            print("Dry-run: SQLite Quellanalyse")
            for table in tables:
                count = _count_rows_sqlite(sqlite_conn, table)
                print(f"  - {table}: rows={count}")
            print("Dry-run erfolgreich abgeschlossen.")
            return

        try:
            import pymysql
        except ImportError as exc:  # pragma: no cover
            raise SystemExit(
                "PyMySQL fehlt. Bitte `pip install -r requirements.txt` ausfuehren.",
            ) from exc

        mariadb = resolve_mariadb_settings()
        maria_conn = pymysql.connect(
            host=mariadb.host,
            port=mariadb.port,
            user=mariadb.user,
            password=mariadb.password,
            database=mariadb.database,
            charset="utf8mb4",
            autocommit=False,
        )
        try:
            with maria_conn.cursor() as cur:
                cur.execute("SET FOREIGN_KEY_CHECKS=0")
            maria_conn.commit()

            print(f"Tabellen fuer Migration: {', '.join(tables)}")
            for table in tables:
                print(f"[MIGRATE] {table}")
                _copy_table(sqlite_conn, maria_conn, table, batch_size=batch_size)

            print("[VERIFY] Row counts")
            has_mismatch = False
            for table in tables:
                sqlite_count = _count_rows_sqlite(sqlite_conn, table)
                maria_count = _count_rows_mariadb(maria_conn, table)
                status = "OK" if sqlite_count == maria_count else "MISMATCH"
                if status != "OK":
                    has_mismatch = True
                print(f"  - {table}: sqlite={sqlite_count}, mariadb={maria_count} [{status}]")

            with maria_conn.cursor() as cur:
                cur.execute("SET FOREIGN_KEY_CHECKS=1")
            maria_conn.commit()

            if has_mismatch:
                raise SystemExit("Migration abgeschlossen, aber Konsistenzfehler erkannt.")
            print("Migration erfolgreich abgeschlossen.")
        finally:
            maria_conn.close()
    finally:
        sqlite_conn.close()


if __name__ == "__main__":
    main()

