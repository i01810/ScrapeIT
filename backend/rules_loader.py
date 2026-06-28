"""Load AskAI YAML rules and build compact prompt context for the SQL chain."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

RULES_DIR = Path(__file__).resolve().parent / "askai_rules"
SYNONYMS_FILE = RULES_DIR / "synonyms.yaml"
METRICS_FILE = RULES_DIR / "metrics.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


@lru_cache
def load_synonyms() -> dict[str, Any]:
    return _load_yaml(SYNONYMS_FILE)


@lru_cache
def load_metrics() -> dict[str, Any]:
    return _load_yaml(METRICS_FILE)


def get_allowed_tables() -> list[str]:
    synonyms = load_synonyms()
    tables: list[str] = []
    for group in synonyms.get("dc_groups", {}).values():
        group_tables = group.get("tables", {})
        for table_name in group_tables.values():
            if table_name and table_name not in tables:
                tables.append(str(table_name))
    return sorted(tables)


def build_domain_context() -> str:
    synonyms = load_synonyms()
    metrics = load_metrics()

    lines: list[str] = [
        "PDM DOMAIN RULES (from askai_rules YAML):",
        "- Use only corp/Hour/Day table families for process analytics.",
        "- Ignore other tables unless user explicitly asks for them.",
        "- Shared timestamp column: DateAndTime.",
        "- Column naming pattern: <EquipmentPrefix>_<MetricSuffix> (example: K1_Current, FM1_Feed).",
        "",
        "MS SQL Server quoting (required):",
        "- Wrap every table, column, and alias in square brackets: [Dc1corp], [K1_Current], AS [row_count].",
        "- Use [DateAndTime] in WHERE clauses for date/time filters.",
        "- Example: SELECT COUNT(*) AS [row_count] FROM [Dc1corp]",
        "",
        "Table grain mapping:",
        "- minute -> *corp (example: Dc1corp)",
        "- hour -> *Hour (example: Dc1Hour)",
        "- day -> *Day (example: Dc1Day)",
        "",
        "Dc group to equipment prefixes:",
    ]

    for dc_name, group in synonyms.get("dc_groups", {}).items():
        prefixes = ", ".join(group.get("equipment_prefixes", []))
        minute_table = group.get("tables", {}).get("minute", "")
        hour_table = group.get("tables", {}).get("hour", "")
        day_table = group.get("tables", {}).get("day", "")
        lines.append(
            f"- {dc_name}: prefixes [{prefixes}] | minute={minute_table}, hour={hour_table}, day={day_table}"
        )

    lines.extend(["", "Equipment dictionary:"])
    for prefix, meta in synonyms.get("equipment_prefixes", {}).items():
        lines.append(f"- {prefix}: {meta.get('name', '')} (dc_group={meta.get('dc_group', '')})")

    lines.extend(["", "Common synonyms:"])
    for key, value in list(synonyms.get("synonyms", {}).items())[:20]:
        if "equipment_prefix" in value:
            lines.append(f"- '{key}' -> equipment_prefix {value['equipment_prefix']}")
        elif "column_suffix" in value:
            lines.append(f"- '{key}' -> column suffix {value['column_suffix']}")
        elif "grain" in value:
            lines.append(f"- '{key}' -> grain {value['grain']}")

    lines.extend(["", "Approved fast metrics (template path):"])
    for metric_name, metric in metrics.get("metrics", {}).items():
        lines.append(f"- {metric_name}: {metric.get('description', '')}")

    starter = metrics.get("starter_questions", [])
    if starter:
        lines.extend(["", "Starter test questions:"])
        for item in starter:
            lines.append(f"- {item.get('text', '')}")

    allowed = get_allowed_tables()
    if allowed:
        lines.extend(["", "Allowed tables:", ", ".join(allowed)])

    return "\n".join(lines)
