"""MS SQL Server identifier normalization — square brackets for tables, columns, aliases."""

from __future__ import annotations

import re

from schema_compact import get_compact_table_map

_AS_ALIAS = re.compile(r"\bAS\s+(?!\[)(?!\')(\w+)\b", re.IGNORECASE)


def _columns_for_tables(table_names: list[str] | None) -> list[str]:
    table_map = get_compact_table_map()
    if not table_names:
        columns: list[str] = []
        for cols in table_map.values():
            columns.extend(cols)
        return sorted(set(columns), key=len, reverse=True)

    columns = []
    for table in table_names:
        columns.extend(table_map.get(table, []))
    return sorted(set(columns), key=len, reverse=True)


def _bracket_identifier_if_bare(sql: str, identifier: str) -> str:
    if not identifier or f"[{identifier}]" in sql:
        return sql
    pattern = rf"(?<!\[)\b{re.escape(identifier)}\b(?!\])"
    return re.sub(pattern, f"[{identifier}]", sql)


_AGGREGATE_FN = re.compile(r"\b(SUM|AVG|COUNT|MIN|MAX)\s*\(", re.IGNORECASE)
_ORDER_BY = re.compile(r"\s+ORDER\s+BY\s+.+$", re.IGNORECASE | re.DOTALL)


def normalize_aggregate_sql(sql: str) -> str:
    """
    T-SQL rule: scalar aggregate (SUM/AVG/COUNT without GROUP BY) cannot ORDER BY non-aggregated columns.
    Strips trailing ORDER BY when the model copies it from row-returning few-shot examples.
    """
    if "GROUP BY" in sql.upper():
        return sql
    if not _AGGREGATE_FN.search(sql):
        return sql
    return _ORDER_BY.sub("", sql).strip()


def normalize_mssql_sql(sql: str, table_names: list[str] | None = None) -> str:
    """
    Wrap bare identifiers in [square brackets] for SQL Server.

    Fixes errors like: SELECT COUNT(*) AS RowCount FROM Dc1corp
    RowCount is reserved; unquoted aliases/tables can fail.
    """
    normalized = sql.strip()

    normalized = _AS_ALIAS.sub(lambda match: f"AS [{match.group(1)}]", normalized)

    table_map = get_compact_table_map()
    allowed_tables = table_names or list(table_map.keys())
    for table in sorted(allowed_tables, key=len, reverse=True):
        for prefix, keyword in (("FROM", "FROM"), ("JOIN", "JOIN"), ("INTO", "INTO")):
            pattern = rf"\b{keyword}\s+(?!\[){re.escape(table)}\b"
            normalized = re.sub(pattern, f"{keyword} [{table}]", normalized, flags=re.IGNORECASE)

    for column in _columns_for_tables(table_names):
        normalized = _bracket_identifier_if_bare(normalized, column)

    return normalized
