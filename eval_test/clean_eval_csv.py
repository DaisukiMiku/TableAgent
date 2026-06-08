#!/usr/bin/env python3
"""Clean raw eval_test.csv into retrieval/eval-ready task assets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "eval_test/eval_test.csv"
DEFAULT_OUTPUT_DIR = ROOT / "eval_test/test_dataset"


TASK_PATTERNS = {
    "chart": re.compile(r"图|图表|绘制|画|柱状|折线|饼图|组合图|可视化|横轴|纵轴|series|chart", re.I),
    "formula": re.compile(r"公式|函数|单元格公式|引用|#REF|#DIV|VLOOKUP|SUMIF|透视", re.I),
    "clean": re.compile(r"清洗|去重|缺失|空值|异常|格式|统一|填充|删除", re.I),
    "report": re.compile(r"报告|总结|分析报告|建议|洞察|解读|结论|风险|原因", re.I),
    "ranking": re.compile(r"最高|最低|排名|top|Top|前\d+|后\d+|排序|最大|最小", re.I),
    "filter": re.compile(r"哪些|筛选|超过|低于|大于|小于|不少于|不超过|>=|<=", re.I),
    "multi_turn": re.compile(r"继续|再|上面|刚才|前面|这些|该图|这个图|它们|上述", re.I),
}

SCOPE_PATTERNS = {
    "province_200b": re.compile(r"200亿省|高收入省|省"),
    "city_prefecture": re.compile(r"市州|自贡|成都|攀枝花|泸州|德阳|绵阳|广元|遂宁|内江|乐山|南充|眉山|宜宾|广安|达州|雅安|巴中|资阳|阿坝|甘孜|凉山"),
}


def normalize_text(value: str) -> str:
    value = (value or "").replace("\ufeff", "").strip()
    value = re.sub(r"\r\n?", "\n", value)
    value = re.sub(r"[ \t]+", " ", value)
    return value


def stable_id(question: str, answer: str, index: int) -> str:
    digest = hashlib.sha1(f"{question}\n---\n{answer}".encode("utf-8")).hexdigest()[:10]
    return f"raw_eval_{index:04d}_{digest}"


def parse_number(value: str) -> float | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def parse_markdown_table(markdown: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    table_lines = [line for line in lines if line.startswith("|") and line.endswith("|")]
    if len(table_lines) < 2:
        return []

    def split_row(line: str) -> list[str]:
        return [cell.strip() for cell in line.strip("|").split("|")]

    header = split_row(table_lines[0])
    body_lines = []
    for line in table_lines[1:]:
        cells = split_row(line)
        if cells and all(re.fullmatch(r":?-{2,}:?", cell or "") for cell in cells):
            continue
        body_lines.append(cells)

    rows: list[dict[str, str]] = []
    for cells in body_lines:
        row = {}
        for i, name in enumerate(header):
            row[name or f"col_{i+1}"] = cells[i] if i < len(cells) else ""
        rows.append(row)
    return rows


def classify_question(question: str) -> dict[str, Any]:
    facets = [name for name, pattern in TASK_PATTERNS.items() if pattern.search(question)]
    if "chart" in facets:
        task_type = "chart_generation"
    elif "formula" in facets:
        task_type = "formula_debug"
    elif "clean" in facets:
        task_type = "data_cleaning"
    elif "report" in facets:
        task_type = "report_generation"
    elif "ranking" in facets:
        task_type = "ranking_qa"
    elif "filter" in facets:
        task_type = "filter_qa"
    else:
        task_type = "table_qa"

    scopes = [name for name, pattern in SCOPE_PATTERNS.items() if pattern.search(question)]
    years = sorted(set(re.findall(r"20\d{2}", question)))
    months = sorted(set(re.findall(r"(?:20\d{2}年)?(?:1[0-2]|[1-9])月", question)))

    return {
        "task_type": task_type,
        "facets": facets,
        "table_scope_hints": scopes,
        "years": years,
        "month_mentions": months,
        "requires_visual_artifact": "chart" in facets,
        "requires_file_edit": task_type in {"formula_debug", "data_cleaning", "chart_generation", "report_generation"},
        "is_multi_turn_like": "multi_turn" in facets,
    }


def build_record(index: int, question: str, answer: str, rows: list[dict[str, str]]) -> dict[str, Any]:
    classification = classify_question(question)
    answer_table = parse_markdown_table(answer)
    scores = [parse_number(row.get("评分", "")) for row in rows]
    new_scores = [parse_number(row.get("新评分", "")) for row in rows]
    scores = [score for score in scores if score is not None]
    new_scores = [score for score in new_scores if score is not None]
    categories = sorted({normalize_text(row.get("归类", "")) for row in rows if normalize_text(row.get("归类", ""))})
    attributions = sorted({normalize_text(row.get("归因", "")) for row in rows if normalize_text(row.get("归因", ""))})

    data_eval_ready = bool(answer_table)
    visual_eval_ready = False
    if classification["requires_visual_artifact"]:
        recommended_eval_mode = "chart_data_table_only"
    elif classification["requires_file_edit"]:
        recommended_eval_mode = "artifact_or_manual_eval"
    else:
        recommended_eval_mode = "structured_table_qa"

    return {
        "id": stable_id(question, answer, index),
        "source": {
            "raw_file": "eval_test/eval_test.csv",
            "trace_ids": [row.get("traceId", "") for row in rows],
            "duplicate_count": len(rows),
            "source_categories": categories,
            "source_attributions": attributions,
            "score_avg": round(mean(scores), 4) if scores else None,
            "new_score_avg": round(mean(new_scores), 4) if new_scores else None,
        },
        "question": question,
        "ground_truth": answer,
        "ground_truth_format": "markdown_table" if answer_table else "text",
        "ground_truth_table": answer_table,
        **classification,
        "data_eval_ready": data_eval_ready,
        "visual_eval_ready": visual_eval_ready,
        "retrieval_eval_ready": False,
        "table_id": None,
        "table_path": None,
        "recommended_eval_mode": recommended_eval_mode,
        "notes": "Raw task has no source table mapping yet. Chart tasks should evaluate underlying data table first; visual artifact quality needs a separate chart evaluator.",
    }


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    fieldnames = [
        "id",
        "question",
        "ground_truth",
        "task_type",
        "facets",
        "table_scope_hints",
        "requires_visual_artifact",
        "requires_file_edit",
        "data_eval_ready",
        "visual_eval_ready",
        "retrieval_eval_ready",
        "recommended_eval_mode",
        "duplicate_count",
        "score_avg",
        "new_score_avg",
        "trace_ids",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "id": record["id"],
                    "question": record["question"],
                    "ground_truth": record["ground_truth"],
                    "task_type": record["task_type"],
                    "facets": ",".join(record["facets"]),
                    "table_scope_hints": ",".join(record["table_scope_hints"]),
                    "requires_visual_artifact": record["requires_visual_artifact"],
                    "requires_file_edit": record["requires_file_edit"],
                    "data_eval_ready": record["data_eval_ready"],
                    "visual_eval_ready": record["visual_eval_ready"],
                    "retrieval_eval_ready": record["retrieval_eval_ready"],
                    "recommended_eval_mode": record["recommended_eval_mode"],
                    "duplicate_count": record["source"]["duplicate_count"],
                    "score_avg": record["source"]["score_avg"],
                    "new_score_avg": record["source"]["new_score_avg"],
                    "trace_ids": ",".join(record["source"]["trace_ids"]),
                }
            )


def build_report(records: list[dict[str, Any]], raw_count: int, valid_count: int) -> str:
    task_counts = Counter(record["task_type"] for record in records)
    facet_counts = Counter(facet for record in records for facet in record["facets"])
    mode_counts = Counter(record["recommended_eval_mode"] for record in records)
    duplicate_counts = Counter(record["source"]["duplicate_count"] for record in records)
    chart_count = sum(1 for record in records if record["requires_visual_artifact"])
    data_ready = sum(1 for record in records if record["data_eval_ready"])

    lines = [
        "# Raw Eval CSV Cleaning Report",
        "",
        "> Generated by `eval_test/clean_eval_csv.py`.",
        "",
        "## Summary",
        "",
        f"- Raw rows: `{raw_count}`",
        f"- Rows with non-empty question and ground truth: `{valid_count}`",
        f"- Deduplicated tasks by exact question + ground truth: `{len(records)}`",
        f"- Data-table eval ready: `{data_ready}`",
        f"- Requires visual artifact: `{chart_count}`",
        "",
        "Important: chart tasks are not removed. They are marked as `requires_visual_artifact=true`; the current ground truth is a markdown data table, so the first-stage evaluator should check the underlying data, not the rendered chart quality.",
        "",
        "## Task Types",
        "",
        "| Task type | Count |",
        "| --- | ---: |",
    ]
    for task_type, count in task_counts.most_common():
        lines.append(f"| `{task_type}` | {count} |")

    lines.extend(["", "## Facets", "", "| Facet | Count |", "| --- | ---: |"])
    for facet, count in facet_counts.most_common():
        lines.append(f"| `{facet}` | {count} |")

    lines.extend(["", "## Recommended Eval Modes", "", "| Mode | Count |", "| --- | ---: |"])
    for mode, count in mode_counts.most_common():
        lines.append(f"| `{mode}` | {count} |")

    lines.extend(["", "## Duplicate Groups", "", "| Raw attempts per dedup task | Task count |", "| ---: | ---: |"])
    for attempts, count in sorted(duplicate_counts.items()):
        lines.append(f"| {attempts} | {count} |")

    lines.extend(
        [
            "",
            "## Outputs",
            "",
            "- `eval_test/test_dataset/raw_eval_cleaned.jsonl`",
            "- `eval_test/test_dataset/raw_eval_cleaned.csv`",
            "",
            "## Next Steps",
            "",
            "1. Map each cleaned task to a real source workbook/table id.",
            "2. Move or copy mapped tables into `workspace/uploads/` to simulate user-uploaded files.",
            "3. Build a table index from uploaded workbooks: schema, sheet summary, metric columns, date/period hints.",
            "4. Add retrieval evaluation: question -> top-k table candidates -> run TableClaw answer workflow.",
            "5. Split chart tasks into two eval layers: underlying data correctness and visual artifact quality.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    rows: list[dict[str, str]] = []
    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        question = normalize_text(row.get("问题", ""))
        answer = normalize_text(row.get("标准答案", ""))
        if not question or not answer:
            continue
        grouped[(question, answer)].append(row)

    records = [
        build_record(index, question, answer, grouped_rows)
        for index, ((question, answer), grouped_rows) in enumerate(sorted(grouped.items()), 1)
    ]

    jsonl_path = output_dir / "raw_eval_cleaned.jsonl"
    csv_path = output_dir / "raw_eval_cleaned.csv"
    report_path = output_dir / "raw_eval_cleaning_report.md"
    write_jsonl(jsonl_path, records)
    write_csv(csv_path, records)
    report_path.write_text(build_report(records, len(rows), sum(len(v) for v in grouped.values())), encoding="utf-8")

    print(f"raw rows: {len(rows)}")
    print(f"clean records: {len(records)}")
    print(f"jsonl: {jsonl_path}")
    print(f"csv: {csv_path}")
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()
