"""Prompt size vs few-shot count (no Ollama)."""
import sys
import time
from functools import lru_cache
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))

import prompt_builder as pb
from prompt_builder import build_text2sql_prompt

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

print("schema pairs for synth few-shots:", len(pairs))


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


real_load = pb.load_mappings
print(f"{'N':>6} {'chars':>12} {'~tokens':>10} {'MB':>7} {'build_s':>8}")
for n in [0, 8, 12, 50, 100, 200, 500, 1000]:
    payload = dict(real_load())
    payload["few_shot"] = synth(n)
    payload["few_shot_max"] = n

    @lru_cache
    def _fake_mappings(_payload=payload):
        return _payload

    pb.load_mappings = _fake_mappings
    t0 = time.perf_counter()
    prompt = build_text2sql_prompt(Q, 200)
    dt = time.perf_counter() - t0
    print(f"{n:>6} {len(prompt):>12,} {len(prompt)//4:>10,} {len(prompt)/1048576:>7.2f} {dt:>8.2f}")
    _fake_mappings.cache_clear()

pb.load_mappings = real_load
real_load.cache_clear()
