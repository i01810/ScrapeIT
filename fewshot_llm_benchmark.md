# fewshot_llm_benchmark

Portable AskAI-style few-shot + text2SQL benchmark in a single Python file.

Copy these two files to another machine (same folder):

- `fewshot_llm_benchmark.py`
- `db_schema_snapshot.txt`

No dependency on the rest of goodSassDashboard2. Optional LLM: `langchain-ollama` + Ollama.

## What it includes

Self-contained logic with no imports from the main project:

1. **Schema parsing** from `db_schema_snapshot.txt` (4560 column refs, 24 tables)
2. **1000 few-shots** — 4 curated seeds + 996 synthetic examples rotating 10 patterns:
   - `latest` (TOP 1)
   - `sum`, `avg`, `min`, `max`, `count`
   - `multiply` (`SUM(col1 * col2)`)
   - `avg_daily` (GROUP BY day)
   - `sum_monthly` (GROUP BY month)
   - `trend` (TOP 200)
3. **Prompt builder** with grain/column/aggregate hints (same style as AskAI)
4. **SQL helpers** — extract, `normalize_aggregate_sql`, basic issue checks
5. **Optional Ollama LLM** via `langchain-ollama`

## Prompt sizes (verified)

| N few-shots | ~Tokens |
|-------------|---------|
| 12          | ~1,140  |
| 100         | ~7,460  |
| 500         | ~40,349 |
| 1000        | ~74,652 |

## Usage

### Size table only (no LLM)

```powershell
python fewshot_llm_benchmark.py --sizes --count 1000
```

### Export 1000 few-shots to JSON

```powershell
python fewshot_llm_benchmark.py --count 1000 --export few_shots_1000.json
```

### Run on Ollama

```powershell
set OLLAMA_MODEL=qwen2.5-coder:1.5b
set OLLAMA_BASE_URL=http://127.0.0.1:11434
python fewshot_llm_benchmark.py --count 100 --run-llm --question "Show me sum of kiln 3 production for last 3 years?"
```

### Compare multiple N values

```powershell
python fewshot_llm_benchmark.py --compare 12,100,500,1000 --question "Show me sum of kiln 3 production for last 3 years?"
```

## CLI options

| Flag | Description |
|------|-------------|
| `--snapshot` | Path to `db_schema_snapshot.txt` (default: same folder as script) |
| `--count` | Total few-shots to generate (default: 1000) |
| `--question` | Test question for prompt/LLM |
| `--export` | Write generated few-shots to JSON file |
| `--sizes` | Print prompt size table |
| `--size-counts` | Comma list for `--sizes` (default: `0,8,12,50,100,200,500,1000`) |
| `--run-llm` | Call Ollama once with `--count` few-shots |
| `--compare` | Run LLM for each N, e.g. `12,100,500,1000` |
| `--model` | Ollama model (default: `OLLAMA_MODEL` env or `qwen2.5-coder:1.5b`) |
| `--base-url` | Ollama URL (default: `OLLAMA_BASE_URL` env or `http://127.0.0.1:11434`) |

## Using with another LLM

For a non-Ollama system:

1. Use `--export` to get the JSON few-shots.
2. Import or copy `build_prompt()` from the script.
3. Send the prompt to your LLM and parse the response with `extract_sql()`.

Seed examples (always included):

- Row count on `Dc1corp`
- Kiln 1 feed (latest)
- Kiln 3 production sum (3 years)
- Kiln 3 production trend (3 years)

## Dependencies

- Python 3.10+
- `db_schema_snapshot.txt` in the same directory
- Optional: `pip install langchain-ollama` (only for `--run-llm` / `--compare`)
