"""
Build the single text2SQL prompt: few-shot examples + auto schema linking.

Domain knowledge lives in YAML (synonyms + few_shot), not in Python routers.
Python only: route tables/columns from the question, then let the LLM write SQL once.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from rules_loader import get_allowed_tables, load_synonyms
from schema_compact import get_compact_table_map, infer_tables_for_question

_MAPPINGS_FILE = Path(__file__).resolve().parent / "askai_rules" / "mappings.yaml"


@lru_cache
def load_mappings() -> dict[str, Any]:
    if not _MAPPINGS_FILE.exists():
        return {}
    with _MAPPINGS_FILE.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _normalize_question(question: str) -> str:
    return re.sub(r"\s+", " ", question.lower().strip())


def _question_words(question: str) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9]+", _normalize_question(question)) if len(w) > 1]


def match_equipment_prefix(question: str) -> str | None:
    """kiln 1 -> K1 from synonyms.yaml (longest phrase wins)."""
    synonyms = load_synonyms()
    q = _normalize_question(question)
    for phrase, meta in sorted(
        synonyms.get("synonyms", {}).items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        if not isinstance(meta, dict):
            continue
        prefix = meta.get("equipment_prefix")
        if prefix and phrase.lower() in q:
            return str(prefix)
    return None


def match_metric_suffix(question: str) -> str | None:
    """feed -> Feed from synonyms.yaml (longest phrase wins)."""
    synonyms = load_synonyms()
    q = _normalize_question(question)
    for phrase, meta in sorted(
        synonyms.get("synonyms", {}).items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        if not isinstance(meta, dict):
            continue
        suffix = meta.get("column_suffix")
        if suffix and phrase.lower() in q:
            return str(suffix)
    return None


def resolve_metric_columns(question: str, equipment: str | None) -> list[str]:
    """
    Resolve column names for the prompt only (never patches SQL after LLM).
    1. equipment_column_overrides in mappings.yaml (phrase -> exact column list)
    2. else synonyms.yaml metric word -> {equipment}_{column_suffix}
    """
    if not equipment:
        return []

    q = _normalize_question(question)
    overrides = (load_mappings().get("equipment_column_overrides") or {}).get(equipment, {})
    for phrase in sorted(overrides.keys(), key=lambda item: len(str(item)), reverse=True):
        if str(phrase).lower() in q:
            cols = overrides[phrase]
            if isinstance(cols, list):
                return [str(c) for c in cols]
            return [str(cols)]

    suffix = match_metric_suffix(question)
    if suffix:
        return [f"{equipment}_{suffix}"]
    return []

_DURATION_RE = re.compile(r"\b(?:last|past)\s+\d+\s+(\w+)\b")


def infer_grain(question: str) -> str:
    """Read grain rules from mappings.yaml — no hardcoded duration logic here."""
    mappings = load_mappings()
    synonyms = load_synonyms()
    default = str(
        mappings.get("default_grain") or synonyms.get("routing", {}).get("default_grain", "minute")
    )
    q = _normalize_question(question)

    duration_match = _DURATION_RE.search(q)
    if duration_match:
        unit = duration_match.group(1).lower()
        for grain, units in (mappings.get("duration_grain") or {}).items():
            if isinstance(units, list) and unit in [str(u).lower() for u in units]:
                return str(grain)

    for grain, keywords in (mappings.get("explicit_grain") or {}).items():
        if not isinstance(keywords, list):
            continue
        for keyword in sorted((str(k).lower() for k in keywords), key=len, reverse=True):
            if keyword in q:
                return str(grain)

    return default


def _table_for_prefix(prefix: str, grain: str) -> str | None:
    synonyms = load_synonyms()
    for group in synonyms.get("dc_groups", {}).values():
        if prefix in group.get("equipment_prefixes", []):
            return group.get("tables", {}).get(grain)
    return None


def infer_tables_from_question(question: str) -> list[str]:
    """Route to 1-2 tables via explicit name or equipment + time grain."""
    tables = set(infer_tables_for_question(question) or [])
    grain = infer_grain(question)
    prefix = match_equipment_prefix(question)
    if prefix:
        table = _table_for_prefix(prefix, grain)
        if table:
            tables.add(table)
    return sorted(tables)


def shortlist_columns(question: str, table: str, max_cols: int = 22) -> list[str]:
    """Schema linking: rank columns by equipment prefix, metric suffix, and word overlap."""
    all_cols = get_compact_table_map().get(table, [])
    if not all_cols:
        return ["DateAndTime"]

    equipment = match_equipment_prefix(question)
    suffix = match_metric_suffix(question)
    metric_cols = resolve_metric_columns(question, equipment)
    words = _question_words(question)

    scored: list[tuple[int, str]] = []
    for col in all_cols:
        score = 0
        col_lower = col.lower()
        if col == "DateAndTime":
            score = 1000
        if col in metric_cols:
            score += 200
        if equipment and col.startswith(f"{equipment}_"):
            score += 120
        if suffix and (col.endswith(suffix) or f"_{suffix}" in col):
            score += 90
        for word in words:
            if word in col_lower:
                score += 12
        if score > 0:
            scored.append((score, col))

    scored.sort(key=lambda item: (-item[0], item[1]))
    picked: list[str] = []
    for _, col in scored:
        if col not in picked:
            picked.append(col)
        if len(picked) >= max_cols:
            break

    if not picked:
        return ["DateAndTime", *all_cols[: min(15, len(all_cols))]]
    return picked


def _few_shot_block(question: str) -> str:
    mappings = load_mappings()
    examples = mappings.get("few_shot", [])
    max_n = int(mappings.get("few_shot_max", 12))
    if not examples:
        return ""

    words = set(_question_words(question))

    def _example_score(ex: dict) -> int:
        q = str(ex.get("question", "")).lower()
        return sum(1 for w in words if w in q)

    ranked = sorted(
        (ex for ex in examples if isinstance(ex, dict)),
        key=_example_score,
        reverse=True,
    )

    lines = ["Examples (follow these SQL patterns exactly):"]
    for ex in ranked[:max_n]:
        q = ex.get("question", "")
        sql = ex.get("sql", "")
        if q and sql:
            lines.append(f"Question: {q}")
            lines.append(f"SQLQuery: {sql}")
            lines.append("")
    return "\n".join(lines)


def build_text2sql_prompt(question: str, top_k: int) -> str:
    """One prompt for one LLM call. No agent loop."""
    mappings = load_mappings()
    tables = infer_tables_from_question(question)
    equipment = match_equipment_prefix(question)
    suffix = match_metric_suffix(question)
    metric_cols = resolve_metric_columns(question, equipment)
    grain = infer_grain(question)

    grain_hint = str(mappings.get("grain_hint", "")).strip()
    column_hint = str(mappings.get("column_hint", "")).strip()
    aggregate_hint = str(mappings.get("aggregate_hint", "")).strip()

    lines = [
        "You are an MS SQL expert for a cement plant PDM database.",
        "Write exactly ONE SELECT query to answer the question.",
        "Output only the SQL after the line SQLQuery: (no explanation).",
        "",
        "Rules:",
        f"- MS SQL syntax. Use TOP {top_k} when returning rows unless the question is COUNT/SUM/AVG only.",
        "- Never use SELECT *. Pick only needed columns from the schema below.",
        "- Use ONLY tables and columns listed below. NEVER invent names like kiln, kiln_feed, tags.",
        "- Real tables: [Dc1corp]..[Dc8corp] (minute), [Dc1Hour]..[Dc8Hour], [Dc1Day]..[Dc8Day].",
        f"- {grain_hint}" if grain_hint else "",
        f"- {column_hint}" if column_hint else "",
        f"- {aggregate_hint}" if aggregate_hint else "",
        "- Column pattern: [EquipmentPrefix]_[Metric] e.g. [K1_Feed], [K1_Current], [K3_AverageProduction]. Time: [DateAndTime].",
        "- Wrap every table, column, and alias in [square brackets].",
        "- SELECT only. No INSERT, UPDATE, DELETE, DROP, or DDL.",
        "",
    ]

    few_shot = _few_shot_block(question)
    if few_shot:
        lines.append(few_shot)

    if tables:
        lines.append(f"Schema for this question (grain={grain}):")
        for table in tables:
            cols = shortlist_columns(question, table)
            lines.append(f"  [{table}]: " + ", ".join(f"[{c}]" for c in cols))
        lines.append("")
        if equipment:
            if metric_cols:
                lines.append(
                    "Metric columns for this question: " + ", ".join(f"[{c}]" for c in metric_cols) + "."
                )
            elif suffix:
                lines.append(f"Equipment maps to prefix [{equipment}]; metric maps to [{equipment}_{suffix}].")
            else:
                lines.append(f"Equipment maps to prefix [{equipment}].")
            lines.append("")
    else:
        allowed = get_allowed_tables()
        lines.append("Allowed tables (pick the best match):")
        lines.append(", ".join(f"[{t}]" for t in allowed))
        lines.append("")

    lines.append(f"Question: {question}")
    lines.append("SQLQuery:")
    return "\n".join(lines)
