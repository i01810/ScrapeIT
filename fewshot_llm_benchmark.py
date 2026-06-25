#!/usr/bin/env python3
"""
Portable AskAI-style few-shot + text2SQL benchmark (single file).

Copy to another machine together with:
  - db_schema_snapshot.txt   (same folder as this script)

No dependency on the rest of goodSassDashboard2. Optional LLM: langchain-ollama + Ollama.

Usage:
  # Prompt size only (no LLM)
  python fewshot_llm_benchmark.py --sizes

  # Generate 1000 few-shots, export JSON, print size
  python fewshot_llm_benchmark.py --count 1000 --export few_shots_1000.json --sizes

  # Run LLM with N few-shots in prompt (Ollama)
  set OLLAMA_MODEL=qwen2.5-coder:1.5b
  set OLLAMA_BASE_URL=http://127.0.0.1:11434
  python fewshot_llm_benchmark.py --count 100 --run-llm --question "Show me sum of kiln 3 production for last 3 years?"

  # Compare multiple N values live
  python fewshot_llm_benchmark.py --run-llm --compare 12,100,500,1000
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Config (override via env or CLI)
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
SNAPSHOT_FILE = HERE / "db_schema_snapshot.txt"
DEFAULT_QUESTION = "Show me sum of kiln 3 production for last 3 years?"
DEFAULT_TOP_K = 200
ALLOWED_SUFFIXES = ("corp", "Hour", "Day")

GRAIN_HINT = (
    "Time grain: last N hours -> corp (minute); "
    "last N days/weeks/months/years -> Day table; hourly data -> Hour table."
)
COLUMN_HINT = (
    "Production columns use AverageProduction or TotalProduction suffixes "
    "(e.g. [K3_AverageProduction], not [K3_Production])."
)
AGGREGATE_HINT = (
    "For SUM/AVG/COUNT/MIN/MAX over a date range with no GROUP BY: return one aggregate row only. "
    "Do NOT use ORDER BY [DateAndTime] unless [DateAndTime] is in SELECT and GROUP BY."
)

# Hand-curated seeds (always prepended before synthetic examples)
SEED_FEW_SHOTS: list[dict[str, str]] = [
    {
        "question": "How many rows in Dc1corp?",
        "sql": "SELECT COUNT(*) AS [row_count] FROM [Dc1corp]",
    },
    {
        "question": "What is kiln 1 feed?",
        "sql": "SELECT TOP 1 [DateAndTime], [K1_Feed] FROM [Dc1corp] WHERE [K1_Feed] IS NOT NULL ORDER BY [DateAndTime] DESC",
    },
    {
        "question": "Show me sum of kiln 3 production for last 3 years",
        "sql": "SELECT SUM([K3_TotalProduction]) AS [sum_kiln_3_production] FROM [Dc6Day] WHERE [DateAndTime] >= DATEADD(year, -3, GETDATE())",
    },
    {
        "question": "Show kiln 3 production for last 3 years",
        "sql": "SELECT TOP 200 [DateAndTime], [K3_AverageProduction] FROM [Dc6Day] WHERE [DateAndTime] >= DATEADD(year, -3, GETDATE()) ORDER BY [DateAndTime] DESC",
    },
]


# ---------------------------------------------------------------------------
# Schema parsing
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ColumnRef:
    table: str
    column: str


def load_schema_pairs(snapshot_path: Path) -> list[ColumnRef]:
    if not snapshot_path.exists():
        raise FileNotFoundError(f"Missing schema snapshot: {snapshot_path}")

    pairs: list[ColumnRef] = []
    for line in snapshot_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("dbo\t"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        table, column = parts[1], parts[2]
        if not table.startswith("Dc") or column == "DateAndTime":
            continue
        if not any(table.endswith(s) for s in ALLOWED_SUFFIXES):
            continue
        pairs.append(ColumnRef(table=table, column=column))
    if not pairs:
        raise ValueError("No Dc*corp/Hour/Day columns found in snapshot.")
    return pairs


def columns_by_table(pairs: list[ColumnRef]) -> dict[str, list[str]]:
    tables: dict[str, list[str]] = {}
    for ref in pairs:
        tables.setdefault(ref.table, [])
        if ref.column not in tables[ref.table]:
            tables[ref.table].append(ref.column)
    for table in tables:
        tables[table].insert(0, "DateAndTime")
    return tables


def _second_column_same_prefix(table: str, col: str, table_cols: dict[str, list[str]]) -> str | None:
    if "_" not in col:
        return None
    prefix = col.split("_", 1)[0]
    for other in table_cols.get(table, []):
        if other != col and other.startswith(prefix + "_") and other != "DateAndTime":
            return other
    return None


# ---------------------------------------------------------------------------
# Synthetic few-shot generation (up to 1000+)
# ---------------------------------------------------------------------------


def _date_filter(table: str) -> str:
    if table.endswith("Day"):
        return "[DateAndTime] >= DATEADD(year, -3, GETDATE())"
    if table.endswith("Hour"):
        return "[DateAndTime] >= DATEADD(day, -30, GETDATE())"
    return "[DateAndTime] >= DATEADD(hour, -24, GETDATE())"


def build_synthetic_few_shot(index: int, ref: ColumnRef, table_cols: dict[str, list[str]]) -> dict[str, str]:
    """Rotate query patterns: latest, sum, avg, min, max, count, multiply, group-by."""
    table, col = ref.table, ref.column
    where = _date_filter(table)
    kind = index % 10

    if kind == 0:
        q = f"What is the latest value of [{col}] from [{table}]?"
        sql = (
            f"SELECT TOP 1 [DateAndTime], [{col}] FROM [{table}] "
            f"WHERE [{col}] IS NOT NULL ORDER BY [DateAndTime] DESC"
        )
    elif kind == 1:
        q = f"Show sum of [{col}] from [{table}] for the filtered period"
        sql = f"SELECT SUM([{col}]) AS [sum_{col}] FROM [{table}] WHERE {where} AND [{col}] IS NOT NULL"
    elif kind == 2:
        q = f"Show average of [{col}] from [{table}] for the filtered period"
        sql = f"SELECT AVG([{col}]) AS [avg_{col}] FROM [{table}] WHERE {where} AND [{col}] IS NOT NULL"
    elif kind == 3:
        q = f"What is minimum [{col}] in [{table}] for the filtered period?"
        sql = f"SELECT MIN([{col}]) AS [min_{col}] FROM [{table}] WHERE {where} AND [{col}] IS NOT NULL"
    elif kind == 4:
        q = f"What is maximum [{col}] in [{table}] for the filtered period?"
        sql = f"SELECT MAX([{col}]) AS [max_{col}] FROM [{table}] WHERE {where} AND [{col}] IS NOT NULL"
    elif kind == 5:
        q = f"How many non-null [{col}] readings in [{table}] for the filtered period?"
        sql = f"SELECT COUNT([{col}]) AS [count_{col}] FROM [{table}] WHERE {where} AND [{col}] IS NOT NULL"
    elif kind == 6:
        col2 = _second_column_same_prefix(table, col, table_cols)
        if col2:
            q = f"Show sum of [{col}] multiplied by [{col2}] in [{table}]"
            sql = (
                f"SELECT SUM([{col}] * [{col2}]) AS [sum_product_{col}_{col2}] "
                f"FROM [{table}] WHERE {where} AND [{col}] IS NOT NULL AND [{col2}] IS NOT NULL"
            )
        else:
            q = f"Show sum of [{col}] times 1.0 in [{table}]"
            sql = f"SELECT SUM([{col}] * 1.0) AS [sum_scaled_{col}] FROM [{table}] WHERE {where}"
    elif kind == 7:
        q = f"Show daily average of [{col}] in [{table}]"
        sql = (
            f"SELECT TOP {DEFAULT_TOP_K} CAST([DateAndTime] AS date) AS [day_date], "
            f"AVG([{col}]) AS [avg_{col}] FROM [{table}] WHERE {where} AND [{col}] IS NOT NULL "
            f"GROUP BY CAST([DateAndTime] AS date) ORDER BY [day_date] DESC"
        )
    elif kind == 8:
        q = f"Show monthly sum of [{col}] in [{table}]"
        sql = (
            f"SELECT TOP {DEFAULT_TOP_K} DATEFROMPARTS(YEAR([DateAndTime]), MONTH([DateAndTime]), 1) AS [month_start], "
            f"SUM([{col}]) AS [sum_{col}] FROM [{table}] WHERE {where} AND [{col}] IS NOT NULL "
            f"GROUP BY YEAR([DateAndTime]), MONTH([DateAndTime]) ORDER BY [month_start] DESC"
        )
    else:
        q = f"Show trend of [{col}] from [{table}] (top rows)"
        sql = (
            f"SELECT TOP {DEFAULT_TOP_K} [DateAndTime], [{col}] FROM [{table}] "
            f"WHERE {where} AND [{col}] IS NOT NULL ORDER BY [DateAndTime] DESC"
        )

    return {"question": q, "sql": sql}


def generate_few_shots(total: int, pairs: list[ColumnRef], table_cols: dict[str, list[str]]) -> list[dict[str, str]]:
    """SEED_FEW_SHOTS + synthetic until `total` examples."""
    out: list[dict[str, str]] = list(SEED_FEW_SHOTS)
    if total <= len(out):
        return out[:total]

    need = total - len(out)
    for i in range(need):
        ref = pairs[i % len(pairs)]
        out.append(build_synthetic_few_shot(i, ref, table_cols))
    return out


# ---------------------------------------------------------------------------
# Prompt builder (standalone — mirrors AskAI text2SQL prompt shape)
# ---------------------------------------------------------------------------


def rank_few_shots(examples: list[dict[str, str]], question: str, max_n: int) -> list[dict[str, str]]:
    words = {w for w in re.split(r"[^a-z0-9]+", question.lower()) if len(w) > 1}

    def score(ex: dict[str, str]) -> int:
        q = ex.get("question", "").lower()
        return sum(1 for w in words if w in q)

    ranked = sorted(examples, key=score, reverse=True)
    return ranked[:max_n]


def build_prompt(
    question: str,
    few_shots: list[dict[str, str]],
    few_shot_max: int,
    schema_tables: dict[str, list[str]],
    top_k: int = DEFAULT_TOP_K,
) -> str:
    ranked = rank_few_shots(few_shots, question, few_shot_max)

    lines = [
        "You are an MS SQL expert for a cement plant PDM database.",
        "Write exactly ONE SELECT query to answer the question.",
        "Output only the SQL after the line SQLQuery: (no explanation).",
        "",
        "Rules:",
        f"- MS SQL syntax. Use TOP {top_k} when returning rows unless the query is COUNT/SUM/AVG/MIN/MAX only.",
        "- Never use SELECT *. Pick only needed columns from the schema below.",
        "- Use ONLY tables and columns listed below. NEVER invent names like kiln, kiln_feed, tags.",
        "- Real tables: [Dc1corp]..[Dc8corp] (minute), [Dc1Hour]..[Dc8Hour], [Dc1Day]..[Dc8Day].",
        f"- {GRAIN_HINT}",
        f"- {COLUMN_HINT}",
        f"- {AGGREGATE_HINT}",
        "- Wrap every table, column, and alias in [square brackets].",
        "- SELECT only. No INSERT, UPDATE, DELETE, DROP, or DDL.",
        "",
        "Examples (follow these SQL patterns exactly):",
    ]
    for ex in ranked:
        lines.append(f"Question: {ex['question']}")
        lines.append(f"SQLQuery: {ex['sql']}")
        lines.append("")

    # Compact schema: table names only (full column list would blow the prompt)
    allowed = sorted(schema_tables.keys())
    lines.append("Allowed tables:")
    lines.append(", ".join(f"[{t}]" for t in allowed))
    lines.append("")
    lines.append(f"Question: {question}")
    lines.append("SQLQuery:")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# SQL post-processing + checks
# ---------------------------------------------------------------------------

_AGG_FN = re.compile(r"\b(SUM|AVG|COUNT|MIN|MAX)\s*\(", re.IGNORECASE)
_ORDER_BY = re.compile(r"\s+ORDER\s+BY\s+.+$", re.IGNORECASE | re.DOTALL)


def normalize_aggregate_sql(sql: str) -> str:
    if "GROUP BY" in sql.upper():
        return sql
    if not _AGG_FN.search(sql):
        return sql
    return _ORDER_BY.sub("", sql).strip()


def extract_sql(raw: str) -> str:
    text = raw.strip()
    if "SQLQUERY:" in text.upper():
        idx = text.upper().index("SQLQUERY:")
        text = text[idx + len("SQLQUERY:") :].strip()
    if "```" in text:
        text = re.sub(r"```(?:sql)?", "", text, flags=re.IGNORECASE).strip()
    return text.rstrip(";").strip()


def check_sql_issues(sql: str, question: str) -> list[str]:
    issues: list[str] = []
    if re.search(r"\bFROM\s+\[?kiln\b", sql, re.I):
        issues.append("invented_kiln_table")
    if re.search(r"\bK3_Production\b", sql) and "TotalProduction" not in sql and "AverageProduction" not in sql:
        issues.append("bad_K3_Production")
    if "SUM(" in sql.upper() and "ORDER BY" in sql.upper() and "GROUP BY" not in sql.upper():
        issues.append("sum_with_order_by")
    if "sum" in question.lower() and "SUM(" not in sql.upper():
        issues.append("expected_sum_missing")
    return issues


# ---------------------------------------------------------------------------
# LLM (optional)
# ---------------------------------------------------------------------------


def invoke_llm(prompt: str, model: str, base_url: str) -> tuple[str, float]:
    try:
        from langchain_ollama import OllamaLLM
    except ImportError as exc:
        raise RuntimeError("Install: pip install langchain-ollama") from exc

    llm = OllamaLLM(model=model, base_url=base_url, temperature=0.0)
    started = time.perf_counter()
    raw = str(llm.invoke(prompt))
    return raw, time.perf_counter() - started


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def print_sizes(few_shots: list[dict[str, str]], question: str, counts: list[int], table_cols: dict[str, list[str]]) -> None:
    print(f"\n{'N few-shots':>12} | {'Prompt chars':>14} | {'~Tokens':>10} | {'MB':>6}")
    print("-" * 50)
    for n in counts:
        prompt = build_prompt(question, few_shots, n, table_cols)
        print(f"{n:>12} | {len(prompt):>14,} | {len(prompt) // 4:>10,} | {len(prompt) / 1_048_576:>5.2f}")


def run_llm_test(
    few_shots: list[dict[str, str]],
    question: str,
    n: int,
    table_cols: dict[str, list[str]],
    model: str,
    base_url: str,
) -> None:
    prompt = build_prompt(question, few_shots, n, table_cols)
    print(f"\n--- LLM test N={n} | prompt {len(prompt):,} chars (~{len(prompt)//4:,} tok) ---")
    raw, sec = invoke_llm(prompt, model, base_url)
    sql = normalize_aggregate_sql(extract_sql(raw))
    issues = check_sql_issues(sql, question)
    print(f"Time: {sec:.1f}s")
    print(f"Issues: {issues or ['none']}")
    print(f"SQL: {sql[:400]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Portable few-shot text2SQL benchmark")
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT_FILE, help="Path to db_schema_snapshot.txt")
    parser.add_argument("--count", type=int, default=1000, help="Total few-shots to generate (default 1000)")
    parser.add_argument("--question", type=str, default=DEFAULT_QUESTION, help="Test question for prompt/LLM")
    parser.add_argument("--export", type=Path, default=None, help="Write generated few-shots to JSON file")
    parser.add_argument("--sizes", action="store_true", help="Print prompt size table")
    parser.add_argument("--size-counts", type=str, default="0,8,12,50,100,200,500,1000", help="Comma list for --sizes")
    parser.add_argument("--run-llm", action="store_true", help="Call Ollama once with --count few-shots")
    parser.add_argument("--compare", type=str, default="", help="Run LLM for each N e.g. 12,100,500,1000")
    parser.add_argument("--model", type=str, default=os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:1.5b"))
    parser.add_argument("--base-url", type=str, default=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    args = parser.parse_args()

    pairs = load_schema_pairs(args.snapshot)
    table_cols = columns_by_table(pairs)
    few_shots = generate_few_shots(args.count, pairs, table_cols)

    print(f"Schema: {len(pairs)} column refs across {len(table_cols)} tables")
    print(f"Generated few-shots: {len(few_shots)} (includes {len(SEED_FEW_SHOTS)} seed examples)")
    kinds = ["latest", "sum", "avg", "min", "max", "count", "multiply", "avg_daily", "sum_monthly", "trend"]
    print(f"Synthetic pattern rotation: {', '.join(kinds)} (index % 10)")

    if args.export:
        args.export.write_text(json.dumps(few_shots, indent=2), encoding="utf-8")
        print(f"Exported: {args.export.resolve()}")

    if args.sizes:
        counts = [int(x.strip()) for x in args.size_counts.split(",") if x.strip()]
        print_sizes(few_shots, args.question, counts, table_cols)

    if args.run_llm:
        run_llm_test(few_shots, args.question, args.count, table_cols, args.model, args.base_url)

    if args.compare:
        for n in [int(x.strip()) for x in args.compare.split(",") if x.strip()]:
            run_llm_test(few_shots, args.question, n, table_cols, args.model, args.base_url)

    if not (args.sizes or args.run_llm or args.compare or args.export):
        parser.print_help()


if __name__ == "__main__":
    main()
