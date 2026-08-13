#!/usr/bin/env bash
# Full pipeline, GPU steps excluded (run chains on Kaggle; see kaggle/).
# Steps 3-6 run on a laptop CPU.
set -euo pipefail

echo "== 1. fetch abstracts (skip if data/abstracts.jsonl exists) =="
[ -f data/abstracts.jsonl ] || python3 -m src.fetch_abstracts --per-class 20

echo "== 2. chains =="
echo "Run on Kaggle T4: bash kaggle/push_kernels.sh <username>"
echo "Then download chains_*.jsonl into data/. Continuing if present."
ls data/chains_*.jsonl >/dev/null 2>&1 || {
  echo "no chain files yet; stopping before scoring"; exit 0; }

echo "== 3. score =="
python3 -m src.score --chains 'data/chains_*.jsonl'

echo "== 4. analysis =="
python3 -m src.analysis

echo "== 5. openalex depth + composition =="
python3 -m src.openalex_depth --mailto "${OPENALEX_MAILTO:-}"
python3 -m src.compose

echo "== 6. figures =="
python3 -m src.figures
echo "Done. Numbers: results/results.json, results/composed.json;"
echo "figures: figures/out/."
