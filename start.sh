#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NANOBOT_DIR="$ROOT_DIR/nanobot"
VENV_PY="$NANOBOT_DIR/.venv/bin/python"
VENV_ACTIVATE="$NANOBOT_DIR/.venv/bin/activate"
CONFIG_FILE="$NANOBOT_DIR/configs/tableclaw-bailian-dashscope.json"
DOMAIN_PACK_DIR="$ROOT_DIR/domain_packs/sichuan-finance"
WORKSPACE_DIR="$ROOT_DIR/workspace"
SYNC_DOMAIN_PACK="$ROOT_DIR/scripts/sync_domain_pack.sh"

export DASHSCOPE_API_KEY="${DASHSCOPE_API_KEY:-sk-c353396b546c429dae1c36bdfdccc731}"

if [ ! -x "$VENV_PY" ]; then
  echo "Missing nanobot virtual environment: $VENV_PY" >&2
  echo "Run this once: cd \"$NANOBOT_DIR\" && python3 -m venv .venv && .venv/bin/python -m pip install -e ." >&2
  exit 1
fi

if [ ! -f "$VENV_ACTIVATE" ]; then
  echo "Missing nanobot virtual environment activation script: $VENV_ACTIVATE" >&2
  exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
  echo "Missing nanobot config: $CONFIG_FILE" >&2
  exit 1
fi

cd "$NANOBOT_DIR"
if [ -x "$SYNC_DOMAIN_PACK" ]; then
  "$SYNC_DOMAIN_PACK" "$DOMAIN_PACK_DIR" "$WORKSPACE_DIR"
fi
source "$VENV_ACTIVATE"
unset PYTHONHOME
exec python -m nanobot agent --config "$CONFIG_FILE" --no-logs "$@"
