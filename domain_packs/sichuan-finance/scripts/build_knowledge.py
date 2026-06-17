#!/usr/bin/env python3
"""Build the compiled Sichuan finance domain knowledge JSON.

The files under ``knowledge_src/`` are the human-maintained source of truth.
Nanobot still reads ``knowledge/tableclaw_industrial_finance.json`` at runtime,
so this script compiles the split source files back into the legacy-compatible
single JSON document.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PACK_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PACK_ROOT / "knowledge_src"
OUTPUT_FILE = PACK_ROOT / "knowledge" / "tableclaw_industrial_finance.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number} must be a JSON object")
        rows.append(value)
    return rows


def build_payload() -> dict[str, Any]:
    meta = read_json(SOURCE_DIR / "meta.json")
    experiences_dir = SOURCE_DIR / "experiences"

    return {
        "version": meta["version"],
        "name": meta["name"],
        "generated_from": meta.get("generated_from", []),
        "principles": meta.get("principles", []),
        "cohorts": read_json(SOURCE_DIR / "cohorts.json"),
        "regions": read_json(SOURCE_DIR / "regions.json"),
        "ranking_policy": read_json(SOURCE_DIR / "ranking_policy.json"),
        "recommended_plans": read_jsonl(SOURCE_DIR / "recommended_plans.jsonl"),
        "validation_overrides": read_jsonl(SOURCE_DIR / "validation_overrides.jsonl"),
        "indicator_mappings": read_jsonl(SOURCE_DIR / "indicator_mappings.jsonl"),
        "indicator_synonyms": read_json(SOURCE_DIR / "indicator_synonyms.json"),
        "table_families": read_json(SOURCE_DIR / "table_families.json"),
        "formulas": read_json(SOURCE_DIR / "formulas.json"),
        "experiences": {
            path.stem: read_jsonl(path)
            for path in sorted(experiences_dir.glob("*.jsonl"))
        },
        "derived_metric_modifiers": read_json(SOURCE_DIR / "derived_metric_modifiers.json"),
    }


def dumps_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build compiled Sichuan finance domain knowledge.")
    parser.add_argument("--check", action="store_true", help="Verify the compiled JSON is up to date.")
    args = parser.parse_args()

    payload = build_payload()
    compiled = dumps_payload(payload)

    if args.check:
        current = OUTPUT_FILE.read_text(encoding="utf-8") if OUTPUT_FILE.exists() else ""
        if current != compiled:
            print(f"{OUTPUT_FILE} is out of date; run this script without --check.")
            return 1
        print(f"{OUTPUT_FILE} is up to date.")
        return 0

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    current = OUTPUT_FILE.read_text(encoding="utf-8") if OUTPUT_FILE.exists() else ""
    if current != compiled:
        OUTPUT_FILE.write_text(compiled, encoding="utf-8")
        print(f"updated {OUTPUT_FILE}")
    else:
        print(f"unchanged {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
