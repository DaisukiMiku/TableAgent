#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NANOBOT_DIR="$ROOT_DIR/nanobot"
VENV_PY="$NANOBOT_DIR/.venv/bin/python"
VENV_ACTIVATE="$NANOBOT_DIR/.venv/bin/activate"
RUN_EVAL="$ROOT_DIR/eval_test/run_gold_parallel_eval.py"
SYNC_DOMAIN_PACK="$ROOT_DIR/scripts/sync_domain_pack.sh"

if [ -z "${DASHSCOPE_API_KEY:-}" ]; then
  echo "DASHSCOPE_API_KEY is required. Export it before running this script." >&2
  exit 1
fi
export DASHSCOPE_API_KEY

if [ ! -x "$VENV_PY" ]; then
  echo "Missing nanobot virtual environment: $VENV_PY" >&2
  exit 1
fi

if [ ! -f "$RUN_EVAL" ]; then
  echo "Missing parallel gold eval runner: $RUN_EVAL" >&2
  exit 1
fi

cd "$ROOT_DIR"
if [ -x "$SYNC_DOMAIN_PACK" ]; then
  "$SYNC_DOMAIN_PACK" "$ROOT_DIR/domain_packs/sichuan-finance" "$ROOT_DIR/workspace"
fi
source "$VENV_ACTIVATE"
unset PYTHONHOME
exec python "$RUN_EVAL" "$@"
