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
RAW_CLEANED_TASK_FILE = DATASET_DIR / "raw_eval_cleaned.jsonl"
GOLD_CASES_TASK_FILE = DATASET_DIR / "gold_cases.jsonl"
DEFAULT_JSON_OUTPUT = "eval_test/results/skill_matrix/latest_eval.json"
DEFAULT_MD_OUTPUT = "docs/实验评测/skill-matrix/latest-eval-summary.md"
RAW_CLEANED_JSON_OUTPUT = "eval_test/results/uploaded_table_workflow/latest_eval.json"
RAW_CLEANED_MD_OUTPUT = "docs/实验评测/uploaded-table-workflow/latest-eval-summary.md"
GOLD_CASES_JSON_OUTPUT = "eval_test/results/gold_cases/latest_eval.json"
GOLD_CASES_MD_OUTPUT = "docs/实验评测/gold-cases/latest-eval-summary.md"
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
TRACKED_TABLECLAW_TOOLS = (
    "tableclaw_catalog_tables",
    "tableclaw_retrieve_tables",
    "tableclaw_inspect",
    "tableclaw_locate_column",
    "tableclaw_extract_series",
    "tableclaw_topk",
    "tableclaw_rank",
    "tableclaw_filter",
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
    question = task["question"]
    if "{table_path}" in question and task.get("table_path"):
        table_path = DATASET_DIR / task["table_path"]
        return question.format(table_path=table_path)
    if task.get("recommended_eval_mode") or task.get("source", {}).get("raw_file"):
        visual_note = (
            "如果这是画图/可视化类任务，本轮评测只要求输出可用于绘图的底层数据表，不需要真正生成图片文件。"
            if task.get("requires_visual_artifact")
            else "请直接回答问题，并说明使用了哪些上传表。"
        )
        gold_note = ""
        if task.get("gold_case_index"):
            gold_note = "\n这是人工整理的 gold case。标准答案只给评测器使用，不能假设或引用标准答案。"
        return f"""用户问题：
{question}

这是 TableClaw workflow 评测。用户已将相关工业表上传到 workspace/uploads，但没有显式指定文件路径。
{gold_note}

执行要求：
1. 请自主选择最可靠的方式完成任务，可以使用可用工具、skill 或简短代码，但不要假设标准答案或 gold table path。
2. 不要把所有上传表完整塞入上下文；优先围绕问题中的时间、指标、地域/单位和表名线索选择相关表格。
3. 如果候选表不足或字段缺失，请明确说明，并基于最相关表格给出 best-effort 结果。
4. {visual_note}
5. 最后列出使用的表文件名，并说明是否成功完成。"""
    return question


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


def _is_tableclaw_retrieval(event: dict[str, Any]) -> bool:
    return event.get("tool") in TRACKED_TABLECLAW_TOOLS


def _select_raw_cleaned_tasks(tasks: list[dict[str, Any]], limit: int | None) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for task in tasks:
        if task.get("data_eval_ready"):
            buckets.setdefault(task.get("task_type") or "unknown", []).append(task)
    selected: list[dict[str, Any]] = []
    for task_type, quota in (("chart_generation", 4), ("table_qa", 3), ("ranking_qa", 3)):
        selected.extend(buckets.get(task_type, [])[:quota])
    selected_ids = {task["id"] for task in selected}
    selected.extend(
        task for task in tasks
        if task.get("data_eval_ready") and task["id"] not in selected_ids
    )
    return selected[:limit] if limit else selected


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
    if not required_facts and not numeric_checks:
        return {
            "facts_passed": 0,
            "facts_total": 0,
            "numeric_passed": 0,
            "numeric_total": 0,
            "fact_results": [],
            "numeric_results": [],
            "passed": None,
            "needs_manual_or_judge_eval": True,
        }

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
        "retrieval_tool_called": any(_is_tableclaw_retrieval(event) for event in timeline),
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
            "| Task | Difficulty | Case | Mode | Retrieval | Skills read | Skill sequence | Skill step | Correct | Total tokens | Prompt | Completion | Cached | Tools | Elapsed ms |",
            "| --- | --- | --- | --- | --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: |",
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
                    f"`{item.get('retrieval_tool_called', False)}`",
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
    parser.add_argument("--raw-cleaned", action="store_true", help="Use raw_eval_cleaned.jsonl and run the uploaded-table retrieval workflow.")
    parser.add_argument("--gold-cases", action="store_true", help="Use curated gold_cases.jsonl. Defaults to all curated gold cases unless --limit is supplied.")
    parser.add_argument("--limit", type=int, help="Limit selected tasks after filtering.")
    parser.add_argument("--list-tasks", action="store_true", help="List selected tasks without running models.")
    parser.add_argument("--json-output", default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args()

    task_files = [GOLD_CASES_TASK_FILE] if args.gold_cases else [RAW_CLEANED_TASK_FILE] if args.raw_cleaned else [
        Path(path) if Path(path).is_absolute() else ROOT / path
        for path in args.task_files
    ]
    raw_cleaned = args.raw_cleaned or any(path.name == "raw_eval_cleaned.jsonl" for path in task_files)
    gold_cases = args.gold_cases or any(path.name == "gold_cases.jsonl" for path in task_files)
    if raw_cleaned and args.json_output == DEFAULT_JSON_OUTPUT:
        args.json_output = RAW_CLEANED_JSON_OUTPUT
    if raw_cleaned and args.md_output == DEFAULT_MD_OUTPUT:
        args.md_output = RAW_CLEANED_MD_OUTPUT
    if gold_cases and args.json_output == DEFAULT_JSON_OUTPUT:
        args.json_output = GOLD_CASES_JSON_OUTPUT
    if gold_cases and args.md_output == DEFAULT_MD_OUTPUT:
        args.md_output = GOLD_CASES_MD_OUTPUT
    tasks = load_tasks(task_files)
    tasks = select_tasks(
        tasks,
        task_ids=args.task_id,
        difficulties=args.difficulty,
        cases=args.case,
    )
    if raw_cleaned and not args.task_id and not args.difficulty and not args.case:
        tasks = _select_raw_cleaned_tasks(tasks, args.limit)
    elif gold_cases and not args.task_id and not args.difficulty and not args.case:
        tasks = tasks[: args.limit] if args.limit else tasks
    elif args.limit:
        tasks = tasks[: args.limit]

    if args.list_tasks:
        for task in tasks:
            print(
                f"{task['id']}\t{task.get('difficulty') or '-'}\t"
                f"{task.get('case') or '-'}\t{task['_task_file']}"
            )
        return

    if not os.environ.get("DASHSCOPE_API_KEY"):
        print("Warning: DASHSCOPE_API_KEY is not set; DashScope-backed model calls may fail.", flush=True)

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
