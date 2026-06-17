#!/usr/bin/env python3
"""Validate the Sichuan finance domain knowledge source files."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from build_knowledge import SOURCE_DIR, build_payload


REQUIRED_TOP_LEVEL_KEYS = {
    "version",
    "name",
    "generated_from",
    "principles",
    "cohorts",
    "regions",
    "ranking_policy",
    "recommended_plans",
    "validation_overrides",
    "indicator_mappings",
    "indicator_synonyms",
    "table_families",
    "formulas",
    "experiences",
    "derived_metric_modifiers",
}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def require_fields(errors: list[str], item: dict[str, Any], fields: list[str], label: str) -> None:
    for field in fields:
        value = item.get(field)
        if value in (None, "", []):
            fail(errors, f"{label} missing required field: {field}")


def validate_jsonl(path: Path, errors: list[str]) -> None:
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            fail(errors, f"{path}:{line_number} invalid JSONL: {exc}")
            continue
        if not isinstance(value, dict):
            fail(errors, f"{path}:{line_number} must be a JSON object")


def main() -> int:
    errors: list[str] = []

    for path in SOURCE_DIR.rglob("*.jsonl"):
        validate_jsonl(path, errors)

    try:
        payload = build_payload()
    except Exception as exc:
        print(f"failed to build knowledge payload: {exc}", file=sys.stderr)
        return 1

    missing = sorted(REQUIRED_TOP_LEVEL_KEYS - set(payload))
    if missing:
        fail(errors, f"compiled payload missing keys: {', '.join(missing)}")

    if not isinstance(payload.get("version"), int):
        fail(errors, "version must be an integer")

    cohort_names: set[str] = set()
    for index, cohort in enumerate(payload.get("cohorts") or [], start=1):
        label = f"cohorts[{index}]"
        require_fields(errors, cohort, ["name", "entities", "usage"], label)
        name = cohort.get("name")
        if name in cohort_names:
            fail(errors, f"duplicate cohort name: {name}")
        cohort_names.add(name)

    synonym_names = payload.get("indicator_synonyms") or {}
    if not isinstance(synonym_names, dict):
        fail(errors, "indicator_synonyms must be an object")
    for indicator, aliases in synonym_names.items():
        if not indicator:
            fail(errors, "indicator_synonyms contains empty indicator")
        if not isinstance(aliases, list) or not aliases:
            fail(errors, f"indicator_synonyms[{indicator}] must be a non-empty list")

    mapping_keys: set[tuple[str, str, str, str]] = set()
    for index, mapping in enumerate(payload.get("indicator_mappings") or [], start=1):
        label = f"indicator_mappings[{index}]"
        require_fields(errors, mapping, ["scope", "indicator", "table", "source"], label)
        key = (
            str(mapping.get("scope")),
            str(mapping.get("indicator")),
            str(mapping.get("table")),
            str(mapping.get("subtable")),
            str(mapping.get("hint")),
            str(mapping.get("source")),
        )
        if key in mapping_keys:
            fail(errors, f"duplicate indicator mapping: {key}")
        mapping_keys.add(key)

    for index, plan in enumerate(payload.get("recommended_plans") or [], start=1):
        label = f"recommended_plans[{index}]"
        require_fields(errors, plan, ["name", "task_signals", "tool_guidance"], label)

    for index, override in enumerate(payload.get("validation_overrides") or [], start=1):
        label = f"validation_overrides[{index}]"
        require_fields(errors, override, ["name", "applies_when", "facts", "source", "usage"], label)
        if override.get("must_use_when_applies") and not override.get("priority"):
            fail(errors, f"{label} has must_use_when_applies but no priority")

    regions = payload.get("regions") or {}
    for key in ["provinces", "sichuan_cities"]:
        if not isinstance(regions.get(key), list) or not regions.get(key):
            fail(errors, f"regions.{key} must be a non-empty list")

    if errors:
        print("Domain knowledge validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Domain knowledge validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
