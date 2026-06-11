#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONHOME=""
unset PYTHONHOME

if [ -z "${DASHSCOPE_API_KEY:-}" ]; then
  echo "DASHSCOPE_API_KEY is not set; catalog descriptions may fall back or judge calls may fail." >&2
fi

RUN_ID="2026-06-10-v4-table-catalog"
REPORT="docs/实验评测/gold-cases/runs/${RUN_ID}.md"
LATEST_REPORT="docs/实验评测/gold-cases/latest-parallel-eval-summary.md"
LOG="logs/${RUN_ID}.log"

{
  echo "[$(date '+%F %T')] v4 table catalog eval start"
  echo "[$(date '+%F %T')] building full table catalog with deepseek-v4-pro"
  nanobot/.venv/bin/python - <<'PY'
import asyncio, json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'nanobot'))
from nanobot.agent.tools.tableclaw import TableClawCatalogTablesTool

async def main():
    tool = TableClawCatalogTablesTool(Path.cwd() / 'workspace')
    out = await tool.execute(rebuild_catalog=True, describe_with_llm=True, model='deepseek-v4-pro')
    data = json.loads(out)
    print(json.dumps({
        'status': data.get('status'),
        'catalog_file': data.get('catalog_file'),
        'uploaded_tables': data.get('uploaded_tables'),
        'cataloged_tables': data.get('cataloged_tables'),
        'describe_with_llm': data.get('describe_with_llm'),
        'model': data.get('model'),
    }, ensure_ascii=False, indent=2), flush=True)

asyncio.run(main())
PY

  echo "[$(date '+%F %T')] running 40 gold cases"
  ./eval_gold_parallel.sh \
    --concurrency 8 \
    --run-id "$RUN_ID" \
    --report "$REPORT" \
    --mode skill-on

  cp "$REPORT" "$LATEST_REPORT"
  echo "[$(date '+%F %T')] v4 table catalog eval finished"
  echo "Report: $REPORT"
} 2>&1 | tee "$LOG"
