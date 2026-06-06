#!/usr/bin/env python3
"""Run TableClaw spreadsheet eval tasks with skill-on/off configs."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from nanobot.nanobot import Nanobot


ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "eval_test/test_dataset"
DEFAULT_TASK_FILES = (
    DATASET_DIR / "tasks.jsonl",
)
CONFIGS = {
    "skill-on": ROOT / "nanobot/configs/tableclaw-bailian-dashscope.json",
    "skill-off": ROOT / "nanobot/configs/tableclaw-bailian-dashscope-no-xlsx-skill.json",
}
TRACKED_SKILLS = (
    "xlsx",
    "table-read",
    "table-clean",
    "table-validate",
    "table-report",
    "table-formula-debug",
    "table-chart",
)


def _loads_maybe(raw: Any) -> Any:
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _compact(value: Any, max_len: int = 220) -> str:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    text = " ".join(text.split()).replace("|", "\\|")
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def _num(value: Any) -> int:
    return int(value) if isinstance(value, int | float) else 0


def _usage(result: dict[str, Any], key: str) -> int:
    return _num((result.get("usage") or {}).get(key))


def load_tasks(task_files: list[Path]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for path in task_files:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                task = json.loads(line)
                task["_task_file"] = str(path.relative_to(ROOT))
                tasks.append(task)
    return tasks


def select_tasks(
    tasks: list[dict[str, Any]],
    *,
    task_ids: list[str] | None = None,
    difficulties: list[str] | None = None,
    cases: list[str] | None = None,
) -> list[dict[str, Any]]:
    selected = tasks
    if task_ids:
        wanted = set(task_ids)
        selected = [task for task in selected if task["id"] in wanted]
    if difficulties:
        wanted = set(difficulties)
        selected = [task for task in selected if task.get("difficulty") in wanted]
    if cases:
        wanted = set(cases)
        selected = [task for task in selected if task.get("case") in wanted]
    return selected


def render_prompt(task: dict[str, Any], mode: str = "skill-on") -> str:
    table_path = DATASET_DIR / task["table_path"]
    return task["question"].format(table_path=table_path)


def extract_tool_timeline(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    tool_step = 0
    for message_index, message in enumerate(messages):
        if message.get("role") != "assistant":
            continue
        for tool_call in message.get("tool_calls") or []:
            tool_step += 1
            fn = tool_call.get("function") or {}
            name = fn.get("name") or tool_call.get("name") or "unknown"
            args = _loads_maybe(fn.get("arguments") or tool_call.get("arguments") or {})
            args_text = json.dumps(args, ensure_ascii=False) if not isinstance(args, str) else args
            skill_read = _detected_skill_read(args_text)
            timeline.append(
                {
                    "step": tool_step,
                    "message_index": message_index,
                    "tool": name,
                    "args": args,
                    "args_preview": _compact(args),
                    "skill_read": skill_read,
                    "is_xlsx_skill_read": skill_read == "xlsx",
                    "is_tracked_skill_read": skill_read is not None,
                }
            )
    return timeline


def _detected_skill_read(args_text: str) -> str | None:
    for skill in TRACKED_SKILLS:
        paths = (
            f"workspace/skills/{skill}/SKILL.md",
            f"nanobot/nanobot/skills/{skill}/SKILL.md",
            f"skills/{skill}/SKILL.md",
        )
        if any(path in args_text for path in paths):
            return skill
    return None


def _contains_number(answer: str, expected: float, tolerance: float) -> bool:
    numbers = re.findall(r"[-+]?\d+(?:\.\d+)?", answer.replace(",", ""))
    for raw in numbers:
        try:
            if abs(float(raw) - expected) <= tolerance:
                return True
        except ValueError:
            continue
    return False


def _parse_number_literal(value: str) -> float | None:
    normalized = value.strip().replace(",", "")
    if not re.fullmatch(r"[-+]?\d+(?:\.\d+)?", normalized):
        return None
    try:
        return float(normalized)
    except ValueError:
        return None


def _fact_matches(answer: str, fact: str) -> bool:
    if " include " in fact:
        _, rhs = fact.split(" include ", 1)
        return all(part.strip() in answer for part in rhs.split(","))
    if "=" in fact:
        _, rhs = fact.split("=", 1)
        expected_number = _parse_number_literal(rhs)
        if expected_number is not None:
            return _contains_number(answer, expected_number, 0.0)
        return rhs.strip() in answer
    return fact in answer


def score_answer(task: dict[str, Any], answer: str) -> dict[str, Any]:
    evaluation = task.get("evaluation") or {}
    required_facts = evaluation.get("required_facts") or []
    numeric_checks = evaluation.get("numeric_checks") or []

    fact_results = [
        {"fact": fact, "passed": _fact_matches(answer, str(fact))}
        for fact in required_facts
    ]
    numeric_results = []
    for check in numeric_checks:
        expected = check.get("expected")
        tolerance = float(check.get("tolerance", 0))
        passed = False
        if isinstance(expected, int | float):
            passed = _contains_number(answer, float(expected), tolerance)
        numeric_results.append(
            {
                "name": check.get("name"),
                "expected": expected,
                "tolerance": tolerance,
                "passed": passed,
            }
        )

    return {
        "facts_passed": sum(1 for item in fact_results if item["passed"]),
        "facts_total": len(fact_results),
        "numeric_passed": sum(1 for item in numeric_results if item["passed"]),
        "numeric_total": len(numeric_results),
        "fact_results": fact_results,
        "numeric_results": numeric_results,
        "passed": all(item["passed"] for item in fact_results + numeric_results),
    }


async def run_one(task: dict[str, Any], mode: str) -> dict[str, Any]:
    bot = Nanobot.from_config(CONFIGS[mode])
    prompt = render_prompt(task, mode)
    started = time.time()
    result = await bot.run(
        prompt,
        session_key=f"sdk:eval-{task['id']}-{mode}-{int(started)}",
    )
    elapsed_ms = int((time.time() - started) * 1000)
    usage = dict(getattr(bot._loop, "_last_usage", {}) or {})
    await bot._loop.close_mcp()

    timeline = extract_tool_timeline(result.messages)
    skill_events = [event for event in timeline if event["is_tracked_skill_read"]]
    skill_step = skill_events[0]["step"] if skill_events else None
    selected_skills = []
    for event in skill_events:
        skill = event.get("skill_read")
        if skill and skill not in selected_skills:
            selected_skills.append(skill)
    score = score_answer(task, result.content)

    return {
        "task_id": task["id"],
        "case": task.get("case"),
        "difficulty": task.get("difficulty"),
        "mode": mode,
        "task_file": task["_task_file"],
        "config": str(CONFIGS[mode]),
        "elapsed_ms": elapsed_ms,
        "usage": usage,
        "tools_used": result.tools_used,
        "tool_timeline": timeline,
        "skill_selected": bool(skill_events),
        "selected_skills": selected_skills,
        "skill_read_sequence": [event.get("skill_read") for event in skill_events],
        "skill_selected_at_step": skill_step,
        "tools_before_skill": (skill_step - 1) if skill_step is not None else None,
        "first_tool": timeline[0]["tool"] if timeline else None,
        "score": score,
        "answer": result.content,
        "answer_preview": result.content[:1200],
    }


def build_summary(payload: dict[str, Any]) -> str:
    results = payload["results"]
    lines = [
        "# TableClaw Eval Summary",
        "",
        f"> Generated at: {payload['generated_at']}",
        "",
        "## Scope",
        "",
        "This report is generated by `eval_test/run_eval.py`.",
        "",
        "Task files:",
        "",
    ]
    for path in payload["task_files"]:
        lines.append(f"- `{path}`")

    lines.extend(
        [
            "",
            "## Summary",
            "",
            "| Task | Difficulty | Case | Mode | Skills read | Skill sequence | Skill step | Correct | Total tokens | Prompt | Completion | Cached | Tools | Elapsed ms |",
            "| --- | --- | --- | --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: |",
        ]
    )
    for item in results:
        skills_label = ",".join(item.get("selected_skills") or []) or "-"
        sequence_label = " -> ".join(item.get("skill_read_sequence") or []) or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    item["task_id"],
                    str(item.get("difficulty") or "-"),
                    str(item.get("case") or "-"),
                    item["mode"],
                    f"`{skills_label}`",
                    f"`{sequence_label}`",
                    str(item["skill_selected_at_step"] or "-"),
                    f"`{item['score']['passed']}`",
                    str(_usage(item, "total_tokens")),
                    str(_usage(item, "prompt_tokens")),
                    str(_usage(item, "completion_tokens")),
                    str(_usage(item, "cached_tokens")),
                    ",".join(item.get("tools_used") or []) or "-",
                    str(item["elapsed_ms"]),
                ]
            )
            + " |"
        )

    matrix = [
        item
        for item in results
        if item.get("case") in {"simple", "complex"}
        and item["mode"] in {"skill-on", "skill-off"}
    ]
    if matrix:
        lines.extend(["", "## Skill Matrix Insight", ""])
        by_key = {(item["case"], item["mode"]): item for item in matrix}
        for case in ("simple", "complex"):
            on = by_key.get((case, "skill-on"))
            off = by_key.get((case, "skill-off"))
            if not on or not off:
                continue
            delta = _usage(on, "total_tokens") - _usage(off, "total_tokens")
            pct = (delta / _usage(off, "total_tokens") * 100) if _usage(off, "total_tokens") else 0
            lines.append(
                f"- `{case}`: skill-on selected skill at step `{on['skill_selected_at_step']}`; "
                f"skill-on minus skill-off = `{delta}` total tokens (`{pct:.1f}%`)."
            )

    lines.extend(["", "## Tool Timelines", ""])
    for item in results:
        lines.extend(
            [
                f"### {item['task_id']} / {item['mode']}",
                "",
                "| Step | Tool | Skill read | Args preview |",
                "| ---: | --- | --- | --- |",
            ]
        )
        for event in item["tool_timeline"]:
            lines.append(
                f"| {event['step']} | `{event['tool']}` | "
                f"`{event.get('skill_read') or '-'}` | {event['args_preview']} |"
            )
        lines.extend(["", "Answer preview:", "", "```text", item["answer_preview"], "```", ""])
    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--task-files",
        nargs="+",
        default=[str(path) for path in DEFAULT_TASK_FILES],
        help="JSONL task files to run.",
    )
    parser.add_argument("--modes", nargs="+", choices=CONFIGS.keys(), default=["skill-on", "skill-off"])
    parser.add_argument("--task-id", action="append", help="Run only the specified task id. Can be repeated.")
    parser.add_argument("--difficulty", nargs="+", choices=["simple", "medium", "hard"], help="Run only selected difficulty levels.")
    parser.add_argument("--case", nargs="+", choices=["simple", "medium", "complex", "workflow"], help="Run only selected case tags.")
    parser.add_argument("--list-tasks", action="store_true", help="List selected tasks without running models.")
    parser.add_argument("--json-output", default="eval_test/results/skill_matrix/latest_eval.json")
    parser.add_argument("--md-output", default="docs/实验评测/skill-matrix/latest-eval-summary.md")
    args = parser.parse_args()

    task_files = [Path(path) if Path(path).is_absolute() else ROOT / path for path in args.task_files]
    tasks = load_tasks(task_files)
    tasks = select_tasks(
        tasks,
        task_ids=args.task_id,
        difficulties=args.difficulty,
        cases=args.case,
    )

    if args.list_tasks:
        for task in tasks:
            print(
                f"{task['id']}\t{task.get('difficulty') or '-'}\t"
                f"{task.get('case') or '-'}\t{task['_task_file']}"
            )
        return

    if not os.environ.get("DASHSCOPE_API_KEY"):
        os.environ["DASHSCOPE_API_KEY"] = "sk-439b8ec88a614cd5a74f7c2cd1d9714f"

    results: list[dict[str, Any]] = []
    for task in tasks:
        for mode in args.modes:
            print(f"Running {task['id']}/{mode}...", flush=True)
            results.append(await run_one(task, mode))

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "task_files": [str(path.relative_to(ROOT)) for path in task_files],
        "modes": args.modes,
        "results": results,
    }

    json_path = ROOT / args.json_output
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = build_summary(payload)
    md_path = ROOT / args.md_output
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(summary, encoding="utf-8")
    print(summary)
    print(f"\nJSON: {json_path}")
    print(f"Markdown: {md_path}")


if __name__ == "__main__":
    asyncio.run(main())
