"""
Measure few-shot prompt scale and optional Ollama hallucination check.
Does NOT modify mappings.yaml — uses synthetic examples in memory.
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))

from prompt_builder import build_text2sql_prompt, load_mappings

SNAPSHOT = BACKEND / "schema_reference" / "db_schema_snapshot.txt"
QUESTION = "Show me sum of kiln 3 production for last 3 years?"


def _parse_dc_columns(limit_tables: int = 24) -> list[tuple[str, str]]:
    """table, column from snapshot (allowed Dc* tables only)."""
    allowed_suffix = ("corp", "Hour", "Day")
    pairs: list[tuple[str, str]] = []
    seen_tables: set[str] = set()
    for line in SNAPSHOT.read_text(encoding="utf-8").splitlines():
        if not line.startswith("dbo\t"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        table, col = parts[1], parts[2]
        if not table.startswith("Dc"):
            continue
        if not any(table.endswith(s) for s in allowed_suffix):
            continue
        if col == "DateAndTime":
            continue
        pairs.append((table, col))
        seen_tables.add(table)
        if len(seen_tables) >= limit_tables and len(pairs) > 500:
            break
    return pairs


def _synthetic_few_shots(n: int) -> list[dict[str, str]]:
    pairs = _parse_dc_columns()
    examples: list[dict[str, str]] = []
    for i in range(n):
        table, col = pairs[i % len(pairs)]
        q = f"What is latest [{col}] from [{table}]?"
        sql = (
            f"SELECT TOP 1 [DateAndTime], [{col}] FROM [{table}] "
            f"WHERE [{col}] IS NOT NULL ORDER BY [DateAndTime] DESC"
        )
        examples.append({"question": q, "sql": sql})
    return examples


def _prompt_size_with_n_few_shots(n: int) -> tuple[int, int]:
    """Patch load_mappings temporarily via monkeypatch on _few_shot_block data."""
    import prompt_builder as pb

    original = load_mappings()

    def _fake_load():
        data = dict(original)
        data["few_shot"] = _synthetic_few_shots(n)
        data["few_shot_max"] = n
        return data

    pb.load_mappings.cache_clear()
    old = pb.load_mappings
    pb.load_mappings = _fake_load  # type: ignore[assignment]
    try:
        prompt = build_text2sql_prompt(QUESTION, top_k=200)
    finally:
        pb.load_mappings = old
        pb.load_mappings.cache_clear()

    # rough token estimate (chars / 4 for English-ish)
    return len(prompt), len(prompt) // 4


def _try_ollama(prompt: str, model: str, base_url: str) -> tuple[bool, str, float]:
    """Returns (success, sql_snippet, seconds)."""
    try:
        from langchain_ollama import OllamaLLM
    except ImportError:
        return False, "langchain_ollama not available", 0.0

    llm = OllamaLLM(model=model, base_url=base_url, temperature=0.0)
    started = time.perf_counter()
    try:
        raw = str(llm.invoke(prompt))
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)[:200], time.perf_counter() - started
    elapsed = time.perf_counter() - started
    text = raw.strip()
    if "SQLQUERY:" in text.upper():
        text = text.split(":", 1)[-1] if text.upper().startswith("SQLQUERY:") else text
    # hallucination heuristics
    bad = []
    if re.search(r"\bFROM\s+\[?kiln\b", text, re.I):
        bad.append("invented_table_kiln")
    if "K3_Production" in text and "AverageProduction" not in text and "TotalProduction" not in text:
        bad.append("bad_column_K3_Production")
    if "ORDER BY" in text.upper() and "SUM(" in text.upper() and "GROUP BY" not in text.upper():
        bad.append("sum_with_order_by")
    flag = ", ".join(bad) if bad else "ok"
    return True, f"{flag} | {text[:180]}", elapsed


def main() -> None:
    load_mappings.cache_clear()
    base_chars, _ = _prompt_size_with_n_few_shots(0)
    current_n = len(load_mappings().get("few_shot", []))
    current_max = load_mappings().get("few_shot_max", 12)

    print("=== AskAI few-shot scale (synthetic examples from schema snapshot) ===\n")
    print(f"Test question: {QUESTION}")
    print(f"Current mappings.yaml: {current_n} examples, few_shot_max={current_max}")
    print(f"Base prompt (0 few-shot injected): ~{base_chars} chars\n")
    print(f"{'N few-shots':>12} | {'Prompt chars':>12} | {'~Tokens':>10} | {'MB':>6}")
    print("-" * 50)

    counts = [8, 12, 50, 100, 200, 500, 1000]
    sizes: dict[int, tuple[int, int]] = {}
    for n in counts:
        chars, tokens = _prompt_size_with_n_few_shots(n)
        sizes[n] = (chars, tokens)
        print(f"{n:>12} | {chars:>12,} | {tokens:>10,} | {chars / 1_048_576:>5.2f}")

    print("\n=== Practical limits (qwen2.5-coder:1.5b) ===")
    print("- Context window: often 32k tokens theoretical, but 1.5B models degrade long before that.")
    print("- Your working prompt today: ~3-4 KB (~1k tokens) with 8-12 ranked few-shots + schema slice.")
    print("- At 500-1000 few-shots: prompt becomes the entire context; model slows and ignores tail examples.")
    print("- This is still ONE LLM call — all few-shots are stuffed into that single prompt.\n")

    from config import get_settings

    settings = get_settings()
    print("=== Live Ollama spot-check (same question, varying N) ===\n")
    for n in [12, 50, 100]:
        chars, tokens = sizes[n]
        import prompt_builder as pb

        original = load_mappings()

        def _fake_load():
            data = dict(original)
            data["few_shot"] = _synthetic_few_shots(n)
            data["few_shot_max"] = n
            return data

        pb.load_mappings.cache_clear()
        old = pb.load_mappings
        pb.load_mappings = _fake_load  # type: ignore[assignment]
        try:
            prompt = build_text2sql_prompt(QUESTION, 200)
        finally:
            pb.load_mappings = old
            pb.load_mappings.cache_clear()

        ok, snippet, sec = _try_ollama(prompt, settings.ollama_model, settings.ollama_base_url)
        status = "OK" if ok else "FAIL"
        print(f"N={n:>3} (~{tokens:,} tok, {sec:.1f}s) [{status}] {snippet}")

    n1000_chars = sizes[1000][0]
    if n1000_chars > 500_000:
        print("\nSkipping N=500/1000 live Ollama calls — prompt too large for quick test on 1.5B.")
    else:
        for n in [500, 1000]:
            chars, tokens = sizes[n]
            print(f"\n(N={n} live test skipped or run manually — {tokens:,} est. tokens)")


if __name__ == "__main__":
    main()
