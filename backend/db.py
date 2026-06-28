"""Database helpers for SQL Server connectivity, query execution, and schema export."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pyodbc
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Result

from config import Settings, get_settings

BACKEND_DIR = Path(__file__).resolve().parent
SQL_INFO_FILE = BACKEND_DIR / "sqlDBinfo.sql"
SCHEMA_OUTPUT_DIR = BACKEND_DIR / "schema_reference"
SCHEMA_OUTPUT_FILE = SCHEMA_OUTPUT_DIR / "db_schema_snapshot.txt"


def test_db_connection(settings: Settings | None = None) -> tuple[bool, str]:
    settings = settings or get_settings()
    try:
        with pyodbc.connect(settings.pyodbc_connection_string, timeout=8) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DB_NAME() AS db_name, @@VERSION AS version")
            row = cursor.fetchone()
            db_name = row[0] if row else settings.db_name
            return True, f"Connected to database '{db_name}' on server '{settings.db_server}'."
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


@lru_cache
def get_sqlalchemy_engine() -> Engine:
    return create_engine(get_settings().sqlalchemy_uri)


def execute_select_query(sql: str, max_rows: int | None = None) -> tuple[list[str], list[tuple[Any, ...]]]:
    """Run a validated SELECT via SQLAlchemy. LangChain does not execute queries."""
    settings = get_settings()
    row_limit = max_rows if max_rows is not None else settings.max_query_rows

    with get_sqlalchemy_engine().connect() as conn:
        result: Result[Any] = conn.execute(text(sql))
        if not result.returns_rows:
            return [], []
        columns = list(result.keys())
        rows = list(result.fetchmany(row_limit + 1))
        return columns, rows


def _read_sql_batches(sql_path: Path) -> list[str]:
    text = sql_path.read_text(encoding="utf-8")
    batches: list[str] = []
    current: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        if stripped.upper() == "GO":
            batch = "\n".join(current).strip()
            if batch:
                batches.append(batch)
            current = []
            continue
        current.append(line)

    final = "\n".join(current).strip()
    if final:
        batches.append(final)
    return batches


def export_schema_snapshot(
    settings: Settings | None = None,
    sql_path: Path = SQL_INFO_FILE,
    output_path: Path = SCHEMA_OUTPUT_FILE,
) -> tuple[bool, str]:
    settings = settings or get_settings()
    SCHEMA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not sql_path.exists():
        return False, f"SQL file not found: {sql_path}"

    batches = _read_sql_batches(sql_path)
    if not batches:
        return False, f"No executable SQL found in {sql_path}"

    lines: list[str] = [
        "# PDM Database Schema Snapshot",
        f"# Server: {settings.db_server}",
        f"# Database: {settings.db_name}",
        "",
    ]

    try:
        with pyodbc.connect(settings.pyodbc_connection_string, timeout=20) as conn:
            cursor = conn.cursor()
            for idx, batch in enumerate(batches, start=1):
                lines.append(f"## Query Batch {idx}")
                lines.append("")
                cursor.execute(batch)
                columns = [col[0] for col in cursor.description] if cursor.description else []
                rows = cursor.fetchall()

                if not columns:
                    lines.append("(No result set)")
                    lines.append("")
                    continue

                lines.append("\t".join(columns))
                lines.append("-" * 80)
                for row in rows:
                    lines.append("\t".join(str(value) if value is not None else "NULL" for value in row))
                lines.append("")
                lines.append(f"Total rows: {len(rows)}")
                lines.append("")

        output_path.write_text("\n".join(lines), encoding="utf-8")
        return True, f"Schema snapshot saved to {output_path}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
