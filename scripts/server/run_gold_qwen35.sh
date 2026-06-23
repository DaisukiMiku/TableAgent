#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

export QWEN35_MODEL="${QWEN35_MODEL:-qwen3.5}"
export QWEN35_API_URL="${QWEN35_API_URL:-http://10.127.23.252:48057/v1}"
export QWEN35_API_KEY="${QWEN35_API_KEY:-EMPTY}"
export TABLEAGENT_WORKSPACE="${TABLEAGENT_WORKSPACE:-$ROOT_DIR/workspace}"

export DASHSCOPE_API_KEY="$QWEN35_API_KEY"
export DASHSCOPE_BASE_URL="$QWEN35_API_URL"

export model="$QWEN35_MODEL"
export api_key="$QWEN35_API_KEY"
export api_url="$QWEN35_API_URL"
export query_decompose_model="$QWEN35_MODEL"
export query_decompose_api_url="$QWEN35_API_URL"
export code_model="$QWEN35_MODEL"
export code_api_url="$QWEN35_API_URL"
export summarize_model="$QWEN35_MODEL"
export summarize_api_url="$QWEN35_API_URL"
export TABLEPIPELINE2_ROOT="${TABLEPIPELINE2_ROOT:-$ROOT_DIR/tablepipeline-2}"
export TABLEPIPELINE2_QQ_KNOWLEDGE_PATH="${TABLEPIPELINE2_QQ_KNOWLEDGE_PATH:-$ROOT_DIR/tablepipeline-2/指标知识库0123.xlsx}"

FRAMEWORK="nanobot-current"
HAS_CONFIG_PATH=0
ARGS=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --framework)
      FRAMEWORK="${2:-}"
      ARGS+=("$1" "$2")
      shift 2
      ;;
    --config-path)
      HAS_CONFIG_PATH=1
      ARGS+=("$1" "$2")
      shift 2
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

CONFIG_PATH="$ROOT_DIR/nanobot/configs/tableclaw-qwen35-server-eval.json"
if [ "$FRAMEWORK" = "nanobot-skill-off" ]; then
  CONFIG_PATH="$ROOT_DIR/nanobot/configs/tableclaw-qwen35-server-no-xlsx-skill.json"
fi

CONFIG_ARGS=()
if [ "$HAS_CONFIG_PATH" -eq 0 ]; then
  CONFIG_ARGS=(--config-path "$CONFIG_PATH")
fi

exec "$ROOT_DIR/eval_gold_parallel.sh" \
  "${CONFIG_ARGS[@]}" \
  --answer-model "$QWEN35_MODEL" \
  --answer-base-url "$QWEN35_API_URL" \
  --answer-api-key "$QWEN35_API_KEY" \
  --judge-model "$QWEN35_MODEL" \
  --judge-base-url "$QWEN35_API_URL" \
  --judge-api-key "$QWEN35_API_KEY" \
  "${ARGS[@]}"
