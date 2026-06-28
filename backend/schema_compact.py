"""Build a stripped-down schema (table names + column names only) for V2 SQL chain."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from rules_loader import get_allowed_tables

BACKEND_DIR = Path(__file__).resolve().parent
SCHEMA_SNAPSHOT_FILE = BACKEND_DIR / "schema_reference" / "db_schema_snapshot.txt"


def _parse_snapshot_tables(snapshot_path: Path, allowed: set[str]) -> dict[str, list[str]]:
    tables: dict[str, list[str]] = {name: [] for name in sorted(allowed)}
    if not snapshot_path.exists():
        return tables

    for line in snapshot_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("dbo\t"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        table_name, column_name = parts[1], parts[2]
        if table_name in allowed and column_name not in tables[table_name]:
            tables[table_name].append(column_name)

    return {name: cols for name, cols in tables.items() if cols}


def _load_columns_from_db(table_names: list[str]) -> dict[str, list[str]]:
    from sqlalchemy import create_engine, text

    from config import get_settings

    settings = get_settings()
    allowed = set(table_names)
    tables: dict[str, list[str]] = {name: [] for name in sorted(allowed)}
    if not allowed:
        return tables

    placeholders = ", ".join(f":t{i}" for i in range(len(table_names)))
    params = {f"t{i}": name for i, name in enumerate(table_names)}
    sql = text(
        f"""
        SELECT TABLE_NAME, COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME IN ({placeholders})
        ORDER BY TABLE_NAME, ORDINAL_POSITION
        """
    )

    engine = create_engine(settings.sqlalchemy_uri)
    with engine.connect() as conn:
        for row in conn.execute(sql, params):
            table_name = str(row[0])
            column_name = str(row[1])
            if table_name in allowed and column_name not in tables[table_name]:
                tables[table_name].append(column_name)

    return {name: cols for name, cols in tables.items() if cols}


@lru_cache
def get_compact_table_map() -> dict[str, list[str]]:
    allowed = get_allowed_tables()
    if not allowed:
        return {}

    allowed_set = set(allowed)
    tables = _parse_snapshot_tables(SCHEMA_SNAPSHOT_FILE, allowed_set)

    missing = [name for name in allowed if name not in tables or not tables[name]]
    if missing:
        db_tables = _load_columns_from_db(missing)
        for name, cols in db_tables.items():
            tables[name] = cols

    return {name: tables[name] for name in sorted(tables) if tables.get(name)}


def build_compact_schema_text(table_names: list[str] | None = None) -> str:
    tables = get_compact_table_map()
    if not tables:
        return "No allowed tables configured."

    if table_names:
        selected = {name for name in table_names if name in tables}
        tables = {name: tables[name] for name in sorted(selected)}

    lines = [
        "Compact schema (TableName: col1, col2, ...). Shared time column: DateAndTime.",
        "",
    ]
    for table_name, columns in tables.items():
        lines.append(f"{table_name}: {', '.join(columns)}")
    return "\n".join(lines)


def infer_tables_for_question(question: str) -> list[str] | None:
    """If the question names specific allowed tables, return only those for a smaller prompt."""
    allowed = get_allowed_tables()
    matched = sorted({table for table in allowed if table.lower() in question.lower()})
    return matched or None
