#!/usr/bin/env python3
"""Build a small focused JSONL subset from prior eval results.

The subset is meant for fast iteration: include recently failed/partial/runtime
cases first, then add a small random sample of previously correct cases to catch
obvious regressions without running the full benchmark every time.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _task_key(row: dict[str, Any]) -> str:
    return str(row.get("id") or row.get("task_id") or row.get("gold_case_index") or "")


def _result_key(row: dict[str, Any]) -> str:
    return str(row.get("task_id") or row.get("id") or row.get("gold_case_index") or "")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True, help="Source task JSONL.")
    parser.add_argument("--results", type=Path, action="append", required=True, help="Prior result JSONL. Can repeat.")
    parser.add_argument("--output", type=Path, required=True, help="Output subset JSONL.")
    parser.add_argument("--max-failed", type=int, default=24)
    parser.add_argument("--random-correct", type=int, default=12)
    parser.add_argument("--seed", type=int, default=20260616)
    args = parser.parse_args()

    source = args.source if args.source.is_absolute() else ROOT / args.source
    output = args.output if args.output.is_absolute() else ROOT / args.output
    tasks = _load_jsonl(source)
    task_by_id = {_task_key(task): task for task in tasks}
    task_by_index = {str(task.get("gold_case_index")): task for task in tasks if task.get("gold_case_index") is not None}

    failed: list[str] = []
    correct: list[str] = []
    seen_failed: set[str] = set()
    seen_correct: set[str] = set()
    for result_path in args.results:
        result_path = result_path if result_path.is_absolute() else ROOT / result_path
        for row in _load_jsonl(result_path):
            key = _result_key(row)
            task = task_by_id.get(key) or task_by_index.get(key)
            if not task:
                continue
            task_id = _task_key(task)
            label = str((row.get("judge") or {}).get("label") or "")
            if label == "correct":
                if task_id not in seen_correct:
                    seen_correct.add(task_id)
                    correct.append(task_id)
            else:
                if task_id not in seen_failed:
                    seen_failed.add(task_id)
                    failed.append(task_id)

    rng = random.Random(args.seed)
    failed = failed[: max(0, args.max_failed)]
    correct_pool = [item for item in correct if item not in set(failed)]
    rng.shuffle(correct_pool)
    selected_ids = [*failed, *correct_pool[: max(0, args.random_correct)]]
    selected = [task_by_id[item] for item in selected_ids if item in task_by_id]

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(task, ensure_ascii=False) + "\n" for task in selected),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "source": str(source),
                "output": str(output),
                "selected": len(selected),
                "failed_or_partial": len(failed),
                "random_correct": len(selected) - len(failed),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
