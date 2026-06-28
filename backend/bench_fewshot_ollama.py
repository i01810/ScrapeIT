"""Ollama hallucination spot-check: N=12 vs N=100 few-shots (synthetic)."""
import re
import sys
import time
from functools import lru_cache
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))

import prompt_builder as pb
from config import get_settings
from prompt_builder import build_text2sql_prompt
from langchain_ollama import OllamaLLM

SNAPSHOT = BACKEND / "schema_reference" / "db_schema_snapshot.txt"
Q = "Show me sum of kiln 3 production for last 3 years?"

pairs = []
for line in SNAPSHOT.read_text(encoding="utf-8").splitlines():
    if not line.startswith("dbo\t"):
        continue
    parts = line.split("\t")
    if len(parts) < 3:
        continue
    table, col = parts[1], parts[2]
    if not table.startswith("Dc") or col == "DateAndTime":
        continue
    if not (table.endswith("corp") or table.endswith("Hour") or table.endswith("Day")):
        continue
    pairs.append((table, col))


def synth(n: int):
    out = []
    for i in range(n):
        t, c = pairs[i % len(pairs)]
        out.append(
            {
                "question": f"What is latest [{c}] from [{t}]?",
                "sql": (
                    f"SELECT TOP 1 [DateAndTime], [{c}] FROM [{t}] "
                    f"WHERE [{c}] IS NOT NULL ORDER BY [DateAndTime] DESC"
                ),
            }
        )
    return out


def check_sql(text: str) -> list[str]:
    issues = []
    if re.search(r"\bFROM\s+\[?kiln\b", text, re.I):
        issues.append("invented_kiln_table")
    if re.search(r"\bK3_Production\b", text) and "TotalProduction" not in text and "AverageProduction" not in text:
        issues.append("bad_K3_Production")
    if "SUM(" in text.upper() and "ORDER BY" in text.upper() and "GROUP BY" not in text.upper():
        issues.append("sum_plus_order_by")
    if "Dc6Day" not in text and "Dc6" not in text:
        issues.append("maybe_wrong_table")
    return issues


def run_n(n: int) -> None:
    real_load = pb.load_mappings
    payload = dict(real_load())
    payload["few_shot"] = synth(n)
    payload["few_shot_max"] = n

    @lru_cache
    def _fake(_p=payload):
        return _p

    pb.load_mappings = _fake
    prompt = build_text2sql_prompt(Q, 200)
    _fake.cache_clear()
    pb.load_mappings = real_load
    real_load.cache_clear()

    settings = get_settings()
    llm = OllamaLLM(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.0,
    )
    t0 = time.perf_counter()
    raw = str(llm.invoke(prompt))
    sec = time.perf_counter() - t0
    sql = raw.strip()
    if "SQLQUERY:" in sql.upper():
        idx = sql.upper().find("SQLQUERY:")
        sql = sql[idx + len("SQLQUERY:") :].strip()
    issues = check_sql(sql)
    print(f"\n=== N={n} | prompt {len(prompt):,} chars (~{len(prompt)//4:,} tok) | {sec:.1f}s ===")
    print("issues:", issues or ["none"])
    print("sql:", sql[:220])


for n in [12, 100]:
    run_n(n)

print("\n(Skipped N=500/1000 live — est. 27k–53k extra tokens; impractical on 1.5B / 16GB RAM)")
