#!/usr/bin/env python3
"""Summarize TableClaw per-turn token usage logs."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _num(value: Any) -> int:
    return int(value) if isinstance(value, int | float) else 0


def _load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _usage(record: dict[str, Any], key: str) -> int:
    return _num((record.get("usage") or {}).get(key))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--log",
        default="workspace/usage/usage.jsonl",
        help="Path to usage JSONL log.",
    )
    parser.add_argument(
        "--last",
        type=int,
        default=5,
        help="Show this many latest per-turn records.",
    )
    args = parser.parse_args()

    log_path = Path(args.log)
    records = _load_records(log_path)
    if not records:
        print(f"No usage records found: {log_path}")
        return

    total_prompt = sum(_usage(r, "prompt_tokens") for r in records)
    total_completion = sum(_usage(r, "completion_tokens") for r in records)
    total_tokens = sum(_usage(r, "total_tokens") for r in records)
    total_cached = sum(_usage(r, "cached_tokens") for r in records)

    print(f"Usage log: {log_path}")
    print(f"Turns: {len(records)}")
    print(
        "Tokens: "
        f"prompt={total_prompt}, completion={total_completion}, "
        f"total={total_tokens}, cached={total_cached}"
    )

    by_session: dict[str, dict[str, int]] = defaultdict(
        lambda: {"turns": 0, "prompt": 0, "completion": 0, "total": 0, "cached": 0}
    )
    for record in records:
        row = by_session[str(record.get("session_key") or "unknown")]
        row["turns"] += 1
        row["prompt"] += _usage(record, "prompt_tokens")
        row["completion"] += _usage(record, "completion_tokens")
        row["total"] += _usage(record, "total_tokens")
        row["cached"] += _usage(record, "cached_tokens")

    print("\nBy session:")
    for session_key, row in sorted(
        by_session.items(), key=lambda item: item[1]["total"], reverse=True
    ):
        print(
            f"- {session_key}: turns={row['turns']}, total={row['total']}, "
            f"prompt={row['prompt']}, completion={row['completion']}, cached={row['cached']}"
        )

    print(f"\nLatest {min(args.last, len(records))} records:")
    for record in records[-args.last:]:
        tools = ",".join(record.get("tools_used") or []) or "-"
        print(
            f"- {record.get('timestamp')} | {record.get('session_key')} | "
            f"model={record.get('model')} | total={_usage(record, 'total_tokens')} | "
            f"prompt={_usage(record, 'prompt_tokens')} | "
            f"completion={_usage(record, 'completion_tokens')} | "
            f"cached={_usage(record, 'cached_tokens')} | "
            f"latency_ms={record.get('latency_ms')} | tools={tools}"
        )


if __name__ == "__main__":
    main()
