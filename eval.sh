#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NANOBOT_DIR="$ROOT_DIR/nanobot"
VENV_PY="$NANOBOT_DIR/.venv/bin/python"
VENV_ACTIVATE="$NANOBOT_DIR/.venv/bin/activate"
RUN_EVAL="$ROOT_DIR/eval_test/run_eval.py"

if [ -z "${DASHSCOPE_API_KEY:-}" ]; then
  echo "DASHSCOPE_API_KEY is required. Export it before running this script." >&2
  exit 1
fi
export DASHSCOPE_API_KEY

if [ ! -x "$VENV_PY" ]; then
  echo "Missing nanobot virtual environment: $VENV_PY" >&2
  echo "Run this once: cd \"$NANOBOT_DIR\" && python3 -m venv .venv && .venv/bin/python -m pip install -e ." >&2
  exit 1
fi

if [ ! -f "$VENV_ACTIVATE" ]; then
  echo "Missing nanobot virtual environment activation script: $VENV_ACTIVATE" >&2
  exit 1
fi

if [ ! -f "$RUN_EVAL" ]; then
  echo "Missing eval runner: $RUN_EVAL" >&2
  exit 1
fi

cd "$ROOT_DIR"
source "$VENV_ACTIVATE"
unset PYTHONHOME
exec python "$RUN_EVAL" "$@"
