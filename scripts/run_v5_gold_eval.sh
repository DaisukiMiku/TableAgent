#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONHOME=""
unset PYTHONHOME

if [ -z "${DASHSCOPE_API_KEY:-}" ]; then
  echo "DASHSCOPE_API_KEY is not set; judge calls may fail unless the evaluator has another configured default." >&2
fi

RUN_ID="2026-06-10-v5-structured-retrieval"
REPORT="docs/实验评测/gold-cases/runs/${RUN_ID}.md"
LATEST_REPORT="docs/实验评测/gold-cases/latest-parallel-eval-summary.md"
LOG="logs/${RUN_ID}.log"

{
  echo "[$(date '+%F %T')] v5 structured retrieval eval start"
  echo "[$(date '+%F %T')] using existing table catalog; retrieve version v5-structured-intent"

  ./eval_gold_parallel.sh \
    --concurrency 8 \
    --run-id "$RUN_ID" \
    --report "$REPORT" \
    --mode skill-on

  cp "$REPORT" "$LATEST_REPORT"
  echo "[$(date '+%F %T')] v5 structured retrieval eval finished"
  echo "Report: $REPORT"
} 2>&1 | tee "$LOG"
