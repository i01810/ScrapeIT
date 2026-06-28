"""
AskAI text2SQL — one LLM call, no ReAct loop.

Pipeline:
  question -> build_text2sql_prompt (YAML few-shot + schema linking)
           -> OllamaLLM (single invoke)
           -> validate SELECT + allowlist
           -> db.execute_select_query (SQLAlchemy)
           -> formatted response
"""

from __future__ import annotations

import re
import time
from functools import lru_cache
from typing import Any

from langchain_core.callbacks import StdOutCallbackHandler
from langchain_ollama import OllamaLLM

from askai_verbose import vlog, vlog_block, vlog_step
from config import Settings, get_settings
from db import execute_select_query
from prompt_builder import build_text2sql_prompt, infer_tables_from_question, match_equipment_prefix, match_metric_suffix
from rules_loader import get_allowed_tables
from sql_mssql import normalize_aggregate_sql, normalize_mssql_sql

_FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|EXEC|EXECUTE|MERGE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)
_FROM_JOIN_TABLE = re.compile(r"\b(?:FROM|JOIN)\s+\[?(\w+)\]?", re.IGNORECASE)


def _extract_sql(raw: str) -> str:
    text_out = raw.strip()
    if "SQLQUERY:" in text_out.upper():
        idx = text_out.upper().index("SQLQUERY:")
        text_out = text_out[idx + len("SQLQUERY:") :].strip()
    if "```" in text_out:
        text_out = re.sub(r"```(?:sql)?", "", text_out, flags=re.IGNORECASE).strip()
    for stop in ("\nSQLResult:", "\nAnswer:", "\nQuestion:"):
        if stop in text_out:
            text_out = text_out.split(stop, 1)[0].strip()
    return text_out.rstrip(";").strip()


def _validate_select_only(sql: str) -> None:
    if not sql:
        raise ValueError("Model returned an empty SQL query.")
    normalized = sql.strip()
    if not normalized.upper().startswith("SELECT"):
        raise ValueError(f"Only SELECT queries are allowed. Got: {sql[:120]}")
    if _FORBIDDEN_SQL.search(normalized):
        raise ValueError("Query contains forbidden SQL keywords.")


def _validate_allowed_tables(sql: str) -> None:
    if "INFORMATION_SCHEMA" in sql.upper():
        return
    allowed = set(get_allowed_tables())
    referenced = {m.group(1) for m in _FROM_JOIN_TABLE.finditer(sql)}
    unknown = referenced - allowed
    if unknown:
        raise ValueError(f"SQL uses tables not in allowlist: {', '.join(sorted(unknown))}")


def _format_rows(columns: list[str], rows: list[tuple[Any, ...]], sql: str, question: str) -> str:
    if not rows:
        return f"No rows returned.\n\nQuestion: {question}\nSQL: {sql}"

    if len(rows) == 1 and len(columns) == 1:
        value = rows[0][0]
        return f"Answer: {value}\n\nSQL: {sql}"

    header = " | ".join(columns)
    divider = " | ".join("---" for _ in columns)
    body_lines = [" | ".join("" if v is None else str(v) for v in row) for row in rows[:50]]
    suffix = f"\n\n(Showing {len(body_lines)} of {len(rows)} rows)" if len(rows) > 50 else ""
    table = "\n".join([header, divider, *body_lines])
    return f"{table}{suffix}\n\nSQL: {sql}"


class AskAISqlChainService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._llm = OllamaLLM(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=settings.ollama_temperature,
        )

    def ask(self, question: str) -> str:
        cleaned = question.strip()
        started = time.perf_counter()

        vlog("=" * 60)
        vlog(f"QUESTION: {cleaned}")
        vlog(f"MODEL: {self.settings.ollama_model} @ {self.settings.ollama_base_url}")

        equipment = match_equipment_prefix(cleaned)
        suffix = match_metric_suffix(cleaned)
        if equipment:
            vlog(f"SCHEMA LINK: equipment={equipment}" + (f", metric={suffix}" if suffix else ""))
        tables = infer_tables_from_question(cleaned)
        if tables:
            vlog(f"TABLES: {', '.join(tables)}")

        prompt = build_text2sql_prompt(cleaned, self.settings.max_query_rows)
        vlog(f"PROMPT SIZE: {len(prompt)} chars (~{len(prompt) / 1024:.1f} KB)")
        vlog_block("text2SQL prompt", prompt)

        with vlog_step("Ollama text2SQL (1 call)"):
            callbacks = [StdOutCallbackHandler()] if self.settings.askai_verbose else []
            raw_sql = self._llm.invoke(prompt, config={"callbacks": callbacks})

        vlog_block("LLM raw output", str(raw_sql))

        sql = _extract_sql(str(raw_sql))
        vlog(f"SQL extracted: {sql}")
        agg_fixed = normalize_aggregate_sql(sql)
        if agg_fixed != sql:
            vlog(f"SQL aggregate fix (drop invalid ORDER BY): {agg_fixed}")
        sql = agg_fixed
        normalized = normalize_mssql_sql(sql, infer_tables_from_question(cleaned))
        if normalized != sql:
            vlog(f"SQL normalized: {normalized}")
        sql = normalized

        with vlog_step("Validate SELECT-only"):
            _validate_select_only(sql)

        with vlog_step("Validate table allowlist"):
            _validate_allowed_tables(sql)

        with vlog_step("Execute SQL (SQLAlchemy)"):
            columns, rows = execute_select_query(sql)

        vlog(f"RESULT: {len(rows)} row(s), columns={columns}")
        answer = _format_rows(columns, rows, sql, cleaned)
        elapsed_ms = (time.perf_counter() - started) * 1000
        vlog(f"DONE: text2sql total={elapsed_ms:.0f} ms")
        vlog("=" * 60)
        return answer


@lru_cache
def get_askai_service() -> AskAISqlChainService:
    return AskAISqlChainService(get_settings())


get_agent_service = get_askai_service
