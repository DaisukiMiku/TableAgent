#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NANOBOT_DIR="$ROOT_DIR/nanobot"
VENV_PY="$NANOBOT_DIR/.venv/bin/python"
VENV_ACTIVATE="$NANOBOT_DIR/.venv/bin/activate"
RUN_EVAL="$ROOT_DIR/eval_test/run_gold_parallel_eval.py"

export DASHSCOPE_API_KEY="${DASHSCOPE_API_KEY:-sk-439b8ec88a614cd5a74f7c2cd1d9714f}"

if [ ! -x "$VENV_PY" ]; then
  echo "Missing nanobot virtual environment: $VENV_PY" >&2
  exit 1
fi

if [ ! -f "$RUN_EVAL" ]; then
  echo "Missing parallel gold eval runner: $RUN_EVAL" >&2
  exit 1
fi

cd "$ROOT_DIR"
source "$VENV_ACTIVATE"
unset PYTHONHOME
exec python "$RUN_EVAL" "$@"
