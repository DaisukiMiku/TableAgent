#!/usr/bin/env python3
"""Parallel gold-case evaluator for the TableClaw nanobot workflow."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import time
import uuid
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
DEFAULT_REPORT = DEFAULT_OUTPUT_DIR / "latest_report.md"
DEFAULT_AGENT_CONFIG = ROOT / "nanobot/configs/tableclaw-bailian-dashscope-eval.json"
DEFAULT_JUDGE_MODEL = "deepseek-v4-pro"
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
JUDGE_PROMPT_VERSION = "data-correctness-v3-2026-06-15"
MAX_ANSWER_RETRIES = 3
ANSWER_RETRY_BASE_SECONDS = 15
TRANSIENT_ANSWER_MARKERS = (
    "RateLimitError",
    "limit_burst_rate",
    "Request rate increased too quickly",
    "request rate increased too quickly",
    "Too Many Requests",
    "rate limit",
    "rate_limit",
)

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
    pattern = re.compile(r"(?<![A-Za-z0-9])([-+]?\d+(?:\.\d+)?\s*%?)\s*(亿元|万元|元|百分点|pp|PP)?")
    for match in pattern.finditer(text.replace(",", "")):
        raw = match.group(1).strip()
        unit = match.group(2) or ""
        has_percent = raw.endswith("%")
        try:
            value = float(raw[:-1] if has_percent else raw)
        except ValueError:
            continue
        results.append({"raw": raw + unit, "value": value, "has_percent": has_percent, "unit": unit})
    return results


def _number_variants(item: dict[str, Any]) -> list[float]:
    value = float(item["value"])
    variants = [value]
    unit = item.get("unit") or ""
    if item.get("has_percent"):
        variants.append(value / 100.0)
    elif abs(value) <= 1:
        variants.append(value * 100.0)
    else:
        variants.append(value / 100.0)
    if unit == "万元":
        variants.append(value / 10000.0)
    elif unit == "亿元":
        variants.append(value * 10000.0)
    elif unit == "元":
        variants.append(value / 10000.0)
        variants.append(value / 100000000.0)
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


def _is_transient_answer_failure(answer: str) -> bool:
    text = answer or ""
    return any(marker in text for marker in TRANSIENT_ANSWER_MARKERS)


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


def _ambiguous_query_flags(question: str) -> list[str]:
    flags: list[str] = []
    has_year = bool(re.search(r"20\d{2}", question))
    if not has_year and re.search(r"(?<!\d)(?:1[0-2]|[1-9])\s*月", question):
        flags.append("month_without_year")
    if "月期间" in question and not has_year:
        flags.append("broken_month_phrase")
    if any(term in question for term in ("1-12月", "1至12月", "一到十二月", "全年")) and not has_year:
        flags.append("yearless_full_year_series")
    return flags


def _judge_disputed(judge: dict[str, Any], det: dict[str, Any], question: str) -> dict[str, Any]:
    label = str(judge.get("label") or "")
    numeric = det["numeric_f1"]
    entity = det["entity_f1"]
    flags: list[str] = []
    if label == "incorrect" and numeric["f1"] >= 0.8 and entity["f1"] >= 0.75:
        flags.append("high_deterministic_overlap")
    if label == "incorrect" and numeric["matched"] >= max(4, int(numeric["gold"] * 0.75)) and entity["recall"] >= 0.75:
        flags.append("likely_unit_or_rounding_issue")
    ambiguous = _ambiguous_query_flags(question)
    return {
        "is_disputed": bool(flags),
        "flags": flags,
        "ambiguous_query_flags": ambiguous,
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
    question = task["question"]
    gold_answer = task.get("gold_answer") or task.get("ground_truth") or ""
    task_type = task.get("task_type") or "unknown"
    metric_conflict_note = ""
    if ("占收比" in question or "占比" in question) and "应收总额" in gold_answer and "占收比" not in gold_answer:
        metric_conflict_note = (
            "\nMetric conflict detected: the user question explicitly asks for 占收比/占比, "
            "but the gold answer table appears to list 应收总额 only. For this case, evaluate the answer "
            "against the user-requested 占收比/占比 metric rather than penalizing it for not reproducing "
            "the conflicting gold metric label. Do not mark it incorrect solely for this mismatch."
        )
    visual_note = (
        "This is a chart/visualization task. In the current TableClaw stage, judge chart DATA correctness only: "
        "entities/categories, metric names, values, units, time period, filters/cohort, and required ordering if the user asked for ordering. "
        "Do NOT penalize the answer for not rendering an actual image, not using a polished chart style, imperfect Markdown layout, "
        "or missing narrative commentary, as long as it provides the correct underlying data table needed for plotting."
        if task.get("requires_visual_artifact")
        else "This is a table QA task. Judge semantic data correctness against the gold answer."
    )
    user = f"""Task type: {task_type}

Question:
{task["question"]}

Gold answer:
{gold_answer}

Model answer:
{answer}

Evaluation notes:
{metric_conflict_note}
- {visual_note}
- Data correctness has priority over presentation. Be strict about table/month/scope, entities, metric columns, values, units, filters, ranking direction, and required calculations.
- Be lenient about Markdown formatting, row/column orientation, prose style, chart aesthetics, and whether a real image file was generated.
- Ignore whether the model used a particular tool, skill, code style, trace format, or narrative structure. Judge only the final business result.
- Do not reward long explanations by themselves. A short answer with the right data is correct; a polished answer with wrong data is incorrect.
- Accept equivalent unit conversions, formatting differences, percentage vs ratio notation, and reasonable rounding.
- Unit conversions are equivalent when mathematically consistent. In particular, 1亿元 = 10000万元 and 1万元 = 10000元. For example, 372563.75万元 should match 37.26亿元 after conversion and rounding; 146833.78万元 should match 14.7亿元.
- For rounded gold answers, accept source-accurate decimals that round to the gold value, and accept rounded integers that are within normal rounding tolerance of source decimals.
- Do not mark an answer wrong only because it reports more precise decimals than the gold or uses a different but explicitly stated unit. For example, 26.16亿元 should match a gold value of 26.2亿元; 11.47% should match 11.5%; 1196.87万元 should match 1197万元.
- Use practical tolerance when the same unit is used: about 0.05 for values rounded to 1 decimal place, about 0.5 for integer 万元 amounts, and about 0.15 percentage points for rounded percentages, unless this would hide a wrong table/month/scope.
- If a model reports exact source values with two decimals while the gold rounds to one decimal, treat it as correct when rounding reconciles the values. Do not require the same number of decimal places.
- For chart-ready monthly series where the gold answer is rounded to one decimal place but the model reports source values with two decimals, accept small systematic rounding/display differences up to about 0.08 in the same unit when the period, metric, entity, and overall series all match. Examples: 25.56 vs 25.6, 22.55 vs 22.6, 23.98 vs 24.0, 24.83 vs 24.8, and 27.85 vs 27.8 should not by themselves make an answer incorrect.
- If the gold uses integer 万元 values, exact source values with decimals are equivalent when they round to that integer. For example, 183967.20万元 matches 183967万元, 17604.87万元 matches 17605万元, and 23027.67万元 matches 23028万元.
- If the gold uses integer percentages for chart data, exact source percentages within normal rounding are equivalent. For example, 17.91% matches 18%, 9.67% matches 10%, 20.53% matches 21%, and 12.77% matches 13%.
- For monthly percentage series where all other months match and only one month differs by a tiny amount such as 1.60% vs 1.63% or 0.00% vs -0.05%, treat it as correct or at most partial unless the discrepancy changes the business conclusion.
- Do not mark an answer incorrect only because it contains extra harmless explanation or a different but readable table layout.
- If the user explicitly asks for a metric that conflicts with the gold table's metric label, judge the answer against the user's explicit metric. For example, if the question asks for 应收账款占收比 / 占收比 but the gold table only lists 应收总额, do not mark an answer wrong solely because it provided the requested 占收比 data instead of the gold's different metric. In that situation, mark correct or partial based on whether the requested metric's entities, values, period, scope, and ordering are reasonable.

Rubric:
- correct / passed=true / score=1.0: all core requested facts are present and correct: period, scope/cohort, entities, metric meaning, values, units, ranking/order if requested, and derived calculations. Formatting, prose, and chart rendering do not matter.
- partial / passed=false / score around 0.3-0.7: the answer uses the mostly right table/scope/metric and gets some important facts right, but misses one or more requested rows/fields, has a non-trivial numeric error, omits required ordering, or has an ambiguity that prevents full acceptance.
- incorrect / passed=false / score=0.0: the answer uses the wrong month/table/scope/metric, confuses a specific metric family with a broader one, includes/excludes material cohort entities incorrectly, fabricates values, says the result cannot be determined when the gold answer provides it, or misses the core requested result.

Return strict JSON only with this schema:
{{"label":"correct|partial|incorrect","passed":true|false,"score":0.0,"reason":"short Chinese explanation","missing":["..."],"extra_errors":["..."]}}"""
    return [
        {
            "role": "system",
            "content": (
                "You are a data-focused evaluator for Chinese spreadsheet analysis tasks. "
                "Prioritize factual spreadsheet data correctness over presentation quality. Return valid JSON only."
            ),
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
    label = str(parsed.get("label") or "").strip().lower()
    if label in {"correct", "partial", "incorrect"}:
        parsed["label"] = label
        parsed["passed"] = label == "correct"
        if label == "correct":
            parsed["score"] = 1.0
        elif label == "incorrect":
            parsed["score"] = 0.0
        else:
            try:
                parsed["score"] = min(0.7, max(0.3, float(parsed.get("score") or 0.5)))
            except (TypeError, ValueError):
                parsed["score"] = 0.5
    parsed["usage"] = usage
    parsed["raw"] = content
    parsed["model"] = model
    parsed["prompt_version"] = JUDGE_PROMPT_VERSION
    return parsed


async def run_answer(
    task: dict[str, Any],
    mode: str,
    *,
    run_id: str,
    config_path: Path | None = None,
) -> dict[str, Any]:
    bot = Nanobot.from_config(config_path or CONFIGS[mode])
    prompt = render_prompt(task, mode)
    started = time.time()
    result = await bot.run(
        prompt,
        session_key=f"sdk:gold-parallel-{run_id}-{task['id']}-{mode}-{int(started)}-{uuid.uuid4().hex[:8]}",
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
    run_id: str,
    config_path: Path | None,
    judge_model: str,
    judge_base_url: str,
    judge_api_key: str,
) -> dict[str, Any]:
    answer_attempts: list[dict[str, Any]] = []
    answer_result: dict[str, Any] | None = None
    for attempt in range(1, MAX_ANSWER_RETRIES + 2):
        try:
            answer_result = await run_answer(task, mode, run_id=run_id, config_path=config_path)
            transient_failure = _is_transient_answer_failure(answer_result.get("answer") or "")
            answer_attempts.append(
                {
                    "attempt": attempt,
                    "transient_failure": transient_failure,
                    "elapsed_ms": answer_result.get("elapsed_ms"),
                    "answer_preview": (answer_result.get("answer") or "")[:240],
                }
            )
            if not transient_failure or attempt > MAX_ANSWER_RETRIES:
                break
        except Exception as exc:
            transient_failure = _is_transient_answer_failure(repr(exc))
            answer_attempts.append(
                {
                    "attempt": attempt,
                    "transient_failure": transient_failure,
                    "exception": repr(exc),
                    "elapsed_ms": 0,
                    "answer_preview": "",
                }
            )
            if not transient_failure or attempt > MAX_ANSWER_RETRIES:
                raise
        await asyncio.sleep(ANSWER_RETRY_BASE_SECONDS * attempt)

    assert answer_result is not None
    gold_answer = task.get("gold_answer") or task.get("ground_truth") or ""
    det = deterministic_metrics(answer_result["answer"], gold_answer)
    judge = await judge_answer(
        task,
        answer_result["answer"],
        model=judge_model,
        base_url=judge_base_url,
        api_key=judge_api_key,
    )
    dispute = _judge_disputed(judge, det, task["question"])
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
        "judge_disputed": dispute["is_disputed"],
        "judge_dispute_flags": dispute["flags"],
        "ambiguous_query_flags": dispute["ambiguous_query_flags"],
        "deterministic_metrics": det,
        "usage": answer_result["usage"],
        "judge_usage": judge.get("usage") or {},
        "answer_retry_count": max(0, len(answer_attempts) - 1),
        "answer_attempts": answer_attempts,
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
        "agent_config": str(args.config_path) if getattr(args, "config_path", None) else None,
        "judge_model": args.judge_model,
        "judge_prompt_version": JUDGE_PROMPT_VERSION,
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
        "judge_disputed_count": sum(1 for item in results if item.get("judge_disputed")),
        "ambiguous_query_count": sum(1 for item in results if item.get("ambiguous_query_flags")),
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
        f"> Agent config: `{summary.get('agent_config') or 'mode default'}`",
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
        f"| Judge disputed cases | {summary.get('judge_disputed_count', 0)} |",
        f"| Ambiguous query cases | {summary.get('ambiguous_query_count', 0)} |",
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
                f"- Judge disputed: `{bool(item.get('judge_disputed'))}` ({', '.join(item.get('judge_dispute_flags') or []) or '-'})",
                f"- Ambiguous query flags: `{', '.join(item.get('ambiguous_query_flags') or []) or '-'}`",
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
    parser.add_argument(
        "--task-file",
        type=Path,
        action="append",
        help="Override evaluation dataset JSONL. Can repeat. Defaults to curated gold_cases.jsonl.",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--run-id", default=_now_stamp(), help="Stable id for archived result artifacts.")
    parser.add_argument(
        "--config-path",
        type=Path,
        default=DEFAULT_AGENT_CONFIG,
        help="Override the Nanobot config used for agent calls. Defaults to the low-temperature eval config.",
    )
    parser.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
    parser.add_argument("--judge-base-url", default=os.environ.get("DASHSCOPE_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--judge-api-key", default=os.environ.get("DASHSCOPE_API_KEY"))
    args = parser.parse_args()

    if not args.judge_api_key:
        raise SystemExit("DASHSCOPE_API_KEY is required for LLM judge calls.")
    os.environ.setdefault("DASHSCOPE_API_KEY", args.judge_api_key)

    task_files = args.task_file or [GOLD_CASES_TASK_FILE]
    task_files = [path if path.is_absolute() else ROOT / path for path in task_files]
    tasks = load_tasks(task_files)
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
                    run_id=args.run_id,
                    config_path=args.config_path,
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
                    "judge_disputed": False,
                    "judge_dispute_flags": [],
                    "ambiguous_query_flags": _ambiguous_query_flags(task["question"]),
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
