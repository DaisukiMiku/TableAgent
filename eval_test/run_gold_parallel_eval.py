#!/usr/bin/env python3
"""Parallel gold-case evaluator for the TableClaw nanobot workflow."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from run_eval import (
    CONFIGS,
    GOLD_CASES_TASK_FILE,
    ROOT,
    TRACKED_TABLECLAW_TOOLS,
    _usage,
    extract_tool_timeline,
    load_tasks,
    render_prompt,
)
from nanobot.nanobot import Nanobot


DEFAULT_OUTPUT_DIR = ROOT / "eval_test/results/gold_cases/parallel"
DEFAULT_REPORT = ROOT / "docs/实验评测/gold-cases/latest-parallel-eval-summary.md"
DEFAULT_JUDGE_MODEL = "deepseek-v4-pro"
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

ENTITY_TERMS = {
    "四川", "广东", "江苏", "浙江", "上海", "安徽", "湖南", "福建", "湖北", "陕西", "广西", "云南",
    "成都", "自贡", "攀枝花", "泸州", "德阳", "绵阳", "广元", "遂宁", "内江", "乐山", "南充",
    "眉山", "宜宾", "广安", "达州", "雅安", "巴中", "资阳", "阿坝", "甘孜", "凉山",
    "全省", "200亿省", "全国", "市州", "区县",
    "应收账款", "应收占收比", "产数应收", "产数应收占收比", "应收总额", "收入同比增幅",
    "应收总额同比增幅", "总欠费", "已列收", "未列收", "一年以上", "小微ICT", "欠费金额",
    "营业收现率", "营业现金比率",
}


def _now_stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _numbers(text: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    pattern = re.compile(r"(?<![A-Za-z0-9])[-+]?\d+(?:\.\d+)?\s*%?")
    for match in pattern.finditer(text.replace(",", "")):
        raw = match.group(0).strip()
        has_percent = raw.endswith("%")
        try:
            value = float(raw[:-1] if has_percent else raw)
        except ValueError:
            continue
        results.append({"raw": raw, "value": value, "has_percent": has_percent})
    return results


def _number_variants(item: dict[str, Any]) -> list[float]:
    value = float(item["value"])
    variants = [value]
    if item.get("has_percent"):
        variants.append(value / 100.0)
    elif abs(value) <= 1:
        variants.append(value * 100.0)
    else:
        variants.append(value / 100.0)
    return variants


def _numeric_match(gold: dict[str, Any], predicted: dict[str, Any]) -> bool:
    gold_values = _number_variants(gold)
    pred_values = _number_variants(predicted)
    for expected in gold_values:
        tolerance = max(0.02, abs(expected) * 0.015)
        for actual in pred_values:
            if abs(expected - actual) <= tolerance:
                return True
    return False


def _f1(gold_items: list[Any], pred_items: list[Any], *, matcher: Any | None = None) -> dict[str, Any]:
    if not gold_items and not pred_items:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "matched": 0, "gold": 0, "predicted": 0}
    matched = 0
    used: set[int] = set()
    matcher = matcher or (lambda gold, pred: gold == pred)
    for gold in gold_items:
        for idx, pred in enumerate(pred_items):
            if idx in used:
                continue
            if matcher(gold, pred):
                used.add(idx)
                matched += 1
                break
    precision = matched / len(pred_items) if pred_items else 0.0
    recall = matched / len(gold_items) if gold_items else 0.0
    score = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(score, 4),
        "matched": matched,
        "gold": len(gold_items),
        "predicted": len(pred_items),
    }


def _entities(text: str) -> list[str]:
    found = [term for term in sorted(ENTITY_TERMS, key=len, reverse=True) if term in text]
    deduped: list[str] = []
    for item in found:
        if item not in deduped:
            deduped.append(item)
    return deduped


def deterministic_metrics(answer: str, gold_answer: str) -> dict[str, Any]:
    gold_numbers = _numbers(gold_answer)
    answer_numbers = _numbers(answer)
    gold_entities = _entities(gold_answer)
    answer_entities = _entities(answer)
    return {
        "numeric_f1": _f1(gold_numbers, answer_numbers, matcher=_numeric_match),
        "entity_f1": _f1(gold_entities, answer_entities),
        "gold_numbers": [item["raw"] for item in gold_numbers],
        "answer_numbers": [item["raw"] for item in answer_numbers[:80]],
        "gold_entities": gold_entities,
        "answer_entities": answer_entities,
    }


def _json_from_text(text: str) -> dict[str, Any]:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    if fenced:
        text = fenced.group(1)
    else:
        first = text.find("{")
        last = text.rfind("}")
        if first >= 0 and last > first:
            text = text[first : last + 1]
    return json.loads(text)


def _judge_prompt(task: dict[str, Any], answer: str) -> list[dict[str, str]]:
    visual_note = (
        "This is a chart task. Judge only whether the underlying data values, labels, units, and conclusions match the gold answer. "
        "Do not penalize missing image aesthetics if the answer provides the data needed for the chart."
        if task.get("requires_visual_artifact")
        else "This is a table QA task. Judge semantic correctness against the gold answer."
    )
    user = f"""Question:
{task["question"]}

Gold answer:
{task.get("gold_answer") or task.get("ground_truth")}

Model answer:
{answer}

Evaluation notes:
- {visual_note}
- Accept equivalent unit conversions, formatting differences, and reasonable rounding.
- Mark partial if some key numbers/entities are correct but important fields are missing or wrong.
- Mark incorrect if the answer uses the wrong table/month/scope, fabricates values, or misses the core requested result.

Return strict JSON only with this schema:
{{"label":"correct|partial|incorrect","passed":true|false,"score":0.0,"reason":"short Chinese explanation","missing":["..."],"extra_errors":["..."]}}"""
    return [
        {
            "role": "system",
            "content": "You are a strict evaluator for Chinese spreadsheet analysis tasks. Return valid JSON only.",
        },
        {"role": "user", "content": user},
    ]


async def judge_answer(task: dict[str, Any], answer: str, *, model: str, base_url: str, api_key: str) -> dict[str, Any]:
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    kwargs = {
        "model": model,
        "messages": _judge_prompt(task, answer),
        "temperature": 0,
        "max_tokens": 900,
    }
    try:
        response = await client.chat.completions.create(
            **kwargs,
            extra_body={"enable_thinking": False},
        )
    except Exception:
        response = await client.chat.completions.create(**kwargs)

    content = response.choices[0].message.content or "{}"
    try:
        parsed = _json_from_text(content)
    except Exception as exc:
        parsed = {
            "label": "judge_parse_error",
            "passed": False,
            "score": 0.0,
            "reason": f"Judge JSON parse failed: {exc}; raw={content[:300]}",
            "missing": [],
            "extra_errors": [],
        }
    usage = response.usage.model_dump() if response.usage else {}
    parsed["usage"] = usage
    parsed["raw"] = content
    parsed["model"] = model
    return parsed


async def run_answer(task: dict[str, Any], mode: str) -> dict[str, Any]:
    bot = Nanobot.from_config(CONFIGS[mode])
    prompt = render_prompt(task, mode)
    started = time.time()
    result = await bot.run(
        prompt,
        session_key=f"sdk:gold-parallel-{task['id']}-{mode}-{int(started)}",
    )
    elapsed_ms = int((time.time() - started) * 1000)
    usage = dict(getattr(bot._loop, "_last_usage", {}) or {})
    await bot._loop.close_mcp()

    timeline = extract_tool_timeline(result.messages)
    tableclaw_tools = [event for event in timeline if event.get("tool") in TRACKED_TABLECLAW_TOOLS]
    skill_events = [event for event in timeline if event.get("is_tracked_skill_read")]
    return {
        "answer": result.content,
        "usage": usage,
        "elapsed_ms": elapsed_ms,
        "tools_used": result.tools_used,
        "tool_timeline": timeline,
        "retrieval_tool_called": any(event.get("tool") == "tableclaw_retrieve_tables" for event in tableclaw_tools),
        "inspect_tool_called": any(event.get("tool") == "tableclaw_inspect" for event in tableclaw_tools),
        "tableclaw_tools_used": list(dict.fromkeys(event.get("tool") for event in tableclaw_tools if event.get("tool"))),
        "skill_selected": bool(skill_events),
        "selected_skills": list(dict.fromkeys(event.get("skill_read") for event in skill_events if event.get("skill_read"))),
    }


async def evaluate_one(
    task: dict[str, Any],
    *,
    mode: str,
    judge_model: str,
    judge_base_url: str,
    judge_api_key: str,
) -> dict[str, Any]:
    answer_result = await run_answer(task, mode)
    gold_answer = task.get("gold_answer") or task.get("ground_truth") or ""
    det = deterministic_metrics(answer_result["answer"], gold_answer)
    judge = await judge_answer(
        task,
        answer_result["answer"],
        model=judge_model,
        base_url=judge_base_url,
        api_key=judge_api_key,
    )
    return {
        "task_id": task["id"],
        "gold_case_index": task.get("gold_case_index"),
        "task_type": task.get("task_type"),
        "mode": mode,
        "question": task["question"],
        "gold_answer": gold_answer,
        "answer": answer_result["answer"],
        "answer_preview": answer_result["answer"][:1600],
        "judge": judge,
        "deterministic_metrics": det,
        "usage": answer_result["usage"],
        "judge_usage": judge.get("usage") or {},
        "elapsed_ms": answer_result["elapsed_ms"],
        "tools_used": answer_result["tools_used"],
        "retrieval_tool_called": answer_result["retrieval_tool_called"],
        "inspect_tool_called": answer_result["inspect_tool_called"],
        "skill_selected": answer_result["skill_selected"],
        "selected_skills": answer_result["selected_skills"],
        "tableclaw_tools_used": answer_result.get("tableclaw_tools_used", []),
        "tool_timeline": answer_result["tool_timeline"],
    }


def build_summary(results: list[dict[str, Any]], *, started_at: str, finished_at: str, args: argparse.Namespace) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for item in results if bool(item["judge"].get("passed")))
    labels = defaultdict(int)
    by_type: dict[str, dict[str, Any]] = {}
    for item in results:
        labels[item["judge"].get("label") or "unknown"] += 1
    for task_type in sorted({item.get("task_type") or "unknown" for item in results}):
        bucket = [item for item in results if (item.get("task_type") or "unknown") == task_type]
        by_type[task_type] = {
            "count": len(bucket),
            "judge_accuracy": round(sum(1 for item in bucket if item["judge"].get("passed")) / len(bucket), 4),
            "avg_score": round(sum(float(item["judge"].get("score") or 0) for item in bucket) / len(bucket), 4),
            "avg_numeric_f1": round(sum(item["deterministic_metrics"]["numeric_f1"]["f1"] for item in bucket) / len(bucket), 4),
            "avg_entity_f1": round(sum(item["deterministic_metrics"]["entity_f1"]["f1"] for item in bucket) / len(bucket), 4),
        }

    return {
        "started_at": started_at,
        "finished_at": finished_at,
        "mode": args.mode,
        "concurrency": args.concurrency,
        "run_id": getattr(args, "run_id", None),
        "judge_model": args.judge_model,
        "total_cases": total,
        "judge_passed": passed,
        "judge_accuracy": round(passed / total, 4) if total else 0.0,
        "judge_label_counts": dict(labels),
        "avg_judge_score": round(sum(float(item["judge"].get("score") or 0) for item in results) / total, 4) if total else 0.0,
        "macro_numeric_f1": round(sum(item["deterministic_metrics"]["numeric_f1"]["f1"] for item in results) / total, 4) if total else 0.0,
        "macro_entity_f1": round(sum(item["deterministic_metrics"]["entity_f1"]["f1"] for item in results) / total, 4) if total else 0.0,
        "retrieval_rate": round(sum(1 for item in results if item["retrieval_tool_called"]) / total, 4) if total else 0.0,
        "inspect_rate": round(sum(1 for item in results if item["inspect_tool_called"]) / total, 4) if total else 0.0,
        "skill_rate": round(sum(1 for item in results if item["skill_selected"]) / total, 4) if total else 0.0,
        "tableclaw_tool_counts": {
            tool: sum(1 for item in results if tool in (item.get("tableclaw_tools_used") or []))
            for tool in TRACKED_TABLECLAW_TOOLS
        },
        "total_answer_tokens": sum(_usage(item, "total_tokens") for item in results),
        "total_judge_tokens": sum(int((item.get("judge_usage") or {}).get("total_tokens") or 0) for item in results),
        "avg_elapsed_ms": round(sum(item["elapsed_ms"] for item in results) / total, 2) if total else 0.0,
        "by_task_type": by_type,
    }


def write_markdown(path: Path, summary: dict[str, Any], results: list[dict[str, Any]]) -> None:
    lines = [
        "# Gold Cases Parallel Eval Summary",
        "",
        f"> Started: {summary['started_at']}  ",
        f"> Finished: {summary['finished_at']}  ",
        f"> Mode: `{summary['mode']}` | Judge: `{summary['judge_model']}` | Cases: `{summary['total_cases']}`",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| LLM judge ACC | {summary['judge_accuracy']:.2%} |",
        f"| Avg judge score | {summary['avg_judge_score']:.4f} |",
        f"| Macro numeric F1 | {summary['macro_numeric_f1']:.4f} |",
        f"| Macro entity F1 | {summary['macro_entity_f1']:.4f} |",
        f"| Retrieval tool call rate | {summary['retrieval_rate']:.2%} |",
        f"| Inspect tool call rate | {summary['inspect_rate']:.2%} |",
        f"| Skill selection rate | {summary['skill_rate']:.2%} |",
        f"| Total answer tokens | {summary['total_answer_tokens']} |",
        f"| Total judge tokens | {summary['total_judge_tokens']} |",
        f"| Avg elapsed ms | {summary['avg_elapsed_ms']:.2f} |",
        "",
        "## By Task Type",
        "",
        "| Task type | Count | ACC | Avg score | Numeric F1 | Entity F1 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for task_type, item in summary["by_task_type"].items():
        lines.append(
            f"| {task_type} | {item['count']} | {item['judge_accuracy']:.2%} | "
            f"{item['avg_score']:.4f} | {item['avg_numeric_f1']:.4f} | {item['avg_entity_f1']:.4f} |"
        )

    lines.extend(["", "## TableClaw Tool Calls", "", "| Tool | Cases used |", "| --- | ---: |"])
    for tool, count in summary.get("tableclaw_tool_counts", {}).items():
        lines.append(f"| `{tool}` | {count} |")

    lines.extend(
        [
            "",
            "## Case Comparison",
            "",
            "| # | Task | Type | Judge | Score | Numeric F1 | Entity F1 | Retrieval | Inspect | TableClaw tools | Skills | Tokens | Gold answer | Model preview | Reason |",
            "| ---: | --- | --- | --- | ---: | ---: | ---: | --- | --- | --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for item in sorted(results, key=lambda row: int(row.get("gold_case_index") or 0)):
        judge = item["judge"]
        det = item["deterministic_metrics"]
        skills = ",".join(item.get("selected_skills") or []) or "-"
        table_tools = ",".join(item.get("tableclaw_tools_used") or []) or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item.get("gold_case_index") or "-"),
                    f"`{item['task_id']}`",
                    str(item.get("task_type") or "-"),
                    str(judge.get("label") or "-"),
                    f"{float(judge.get('score') or 0):.2f}",
                    f"{det['numeric_f1']['f1']:.2f}",
                    f"{det['entity_f1']['f1']:.2f}",
                    f"`{item['retrieval_tool_called']}`",
                    f"`{item['inspect_tool_called']}`",
                    f"`{table_tools}`",
                    f"`{skills}`",
                    str(_usage(item, "total_tokens")),
                    _normalize_space(item["gold_answer"])[:220].replace("|", "\\|"),
                    _normalize_space(item["answer"])[:260].replace("|", "\\|"),
                    _normalize_space(str(judge.get("reason") or ""))[:220].replace("|", "\\|"),
                ]
            )
            + " |"
        )

    lines.extend(["", "## Case Details", ""])
    for item in sorted(results, key=lambda row: int(row.get("gold_case_index") or 0)):
        judge = item["judge"]
        det = item["deterministic_metrics"]
        skills = ", ".join(item.get("selected_skills") or []) or "-"
        table_tools = ", ".join(item.get("tableclaw_tools_used") or []) or "-"
        lines.extend(
            [
                f"### Case {item.get('gold_case_index') or '-'} / `{item['task_id']}`",
                "",
                f"- Type: `{item.get('task_type') or '-'}`",
                f"- Judge: `{judge.get('label') or '-'}` / score `{float(judge.get('score') or 0):.2f}`",
                f"- Numeric F1: `{det['numeric_f1']['f1']:.4f}`",
                f"- Entity F1: `{det['entity_f1']['f1']:.4f}`",
                f"- TableClaw tools: `{table_tools}`",
                f"- Skills: `{skills}`",
                f"- Tokens: `{_usage(item, 'total_tokens')}`",
                "",
                "**Question**",
                "",
                "```text",
                item["question"],
                "```",
                "",
                "**Gold Answer**",
                "",
                "```text",
                item["gold_answer"],
                "```",
                "",
                "**Model Answer**",
                "",
                "```text",
                item["answer"],
                "```",
                "",
                "**Judge Reason**",
                "",
                "```text",
                str(judge.get("reason") or ""),
                "```",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=CONFIGS.keys(), default="skill-on")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--case-index", type=int, action="append", help="Run selected gold case index. Can repeat.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--run-id", default=_now_stamp(), help="Stable id for archived result artifacts.")
    parser.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
    parser.add_argument("--judge-base-url", default=os.environ.get("DASHSCOPE_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--judge-api-key", default=os.environ.get("DASHSCOPE_API_KEY"))
    args = parser.parse_args()

    if not args.judge_api_key:
        raise SystemExit("DASHSCOPE_API_KEY is required for LLM judge calls.")
    os.environ.setdefault("DASHSCOPE_API_KEY", args.judge_api_key)

    tasks = load_tasks([GOLD_CASES_TASK_FILE])
    if args.case_index:
        wanted = set(args.case_index)
        tasks = [task for task in tasks if task.get("gold_case_index") in wanted]
    if args.limit:
        tasks = tasks[: args.limit]

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    result_jsonl = output_dir / "latest_results.jsonl"
    summary_json = output_dir / "latest_summary.json"
    archive_dir = output_dir / "runs"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_result_jsonl = archive_dir / f"{args.run_id}_results.jsonl"
    archive_summary_json = archive_dir / f"{args.run_id}_summary.json"
    result_jsonl.write_text("", encoding="utf-8")
    archive_result_jsonl.write_text("", encoding="utf-8")

    started_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    sem = asyncio.Semaphore(max(1, args.concurrency))
    lock = asyncio.Lock()
    results: list[dict[str, Any]] = []

    async def worker(idx: int, task: dict[str, Any]) -> None:
        async with sem:
            print(f"[{idx}/{len(tasks)}] running {task['id']}...", flush=True)
            try:
                item = await evaluate_one(
                    task,
                    mode=args.mode,
                    judge_model=args.judge_model,
                    judge_base_url=args.judge_base_url,
                    judge_api_key=args.judge_api_key,
                )
            except Exception as exc:
                item = {
                    "task_id": task["id"],
                    "gold_case_index": task.get("gold_case_index"),
                    "task_type": task.get("task_type"),
                    "mode": args.mode,
                    "question": task["question"],
                    "gold_answer": task.get("gold_answer") or task.get("ground_truth") or "",
                    "answer": "",
                    "judge": {
                        "label": "runtime_error",
                        "passed": False,
                        "score": 0.0,
                        "reason": repr(exc),
                        "missing": [],
                        "extra_errors": [],
                    },
                    "deterministic_metrics": deterministic_metrics("", task.get("gold_answer") or task.get("ground_truth") or ""),
                    "usage": {},
                    "judge_usage": {},
                    "elapsed_ms": 0,
                    "tools_used": [],
                    "retrieval_tool_called": False,
                    "inspect_tool_called": False,
                    "skill_selected": False,
                    "selected_skills": [],
                    "tableclaw_tools_used": [],
                    "tool_timeline": [],
                }
            async with lock:
                results.append(item)
                with result_jsonl.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
                with archive_result_jsonl.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
                print(
                    f"[{idx}/{len(tasks)}] done {task['id']} "
                    f"label={item['judge'].get('label')} score={item['judge'].get('score')} "
                    f"tokens={_usage(item, 'total_tokens')} elapsed_ms={item.get('elapsed_ms')}",
                    flush=True,
                )

    await asyncio.gather(*(worker(idx, task) for idx, task in enumerate(tasks, start=1)))
    results.sort(key=lambda item: int(item.get("gold_case_index") or 0))
    finished_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    summary = build_summary(results, started_at=started_at, finished_at=finished_at, args=args)
    summary_json.write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    archive_summary_json.write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(Path(args.report), summary, results)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    print(f"Results JSONL: {result_jsonl}", flush=True)
    print(f"Summary JSON: {summary_json}", flush=True)
    print(f"Archived results JSONL: {archive_result_jsonl}", flush=True)
    print(f"Archived summary JSON: {archive_summary_json}", flush=True)
    print(f"Markdown report: {Path(args.report)}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
