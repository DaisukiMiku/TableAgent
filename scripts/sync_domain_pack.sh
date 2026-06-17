#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOMAIN_PACK_DIR="${1:-$ROOT_DIR/domain_packs/sichuan-finance}"
WORKSPACE_DIR="${2:-$ROOT_DIR/workspace}"

if [ ! -d "$DOMAIN_PACK_DIR" ]; then
  exit 0
fi

mkdir -p "$WORKSPACE_DIR/skills/sichuan-finance" "$WORKSPACE_DIR/domain_knowledge"

if [ -f "$DOMAIN_PACK_DIR/scripts/validate_knowledge.py" ]; then
  python3 "$DOMAIN_PACK_DIR/scripts/validate_knowledge.py" >/dev/null
fi

if [ -f "$DOMAIN_PACK_DIR/scripts/build_knowledge.py" ]; then
  python3 "$DOMAIN_PACK_DIR/scripts/build_knowledge.py" >/dev/null
fi

cp "$DOMAIN_PACK_DIR/skills/sichuan-finance/SKILL.md" "$WORKSPACE_DIR/skills/sichuan-finance/SKILL.md"
cp "$DOMAIN_PACK_DIR/knowledge/tableclaw_industrial_finance.json" "$WORKSPACE_DIR/domain_knowledge/tableclaw_industrial_finance.json"
