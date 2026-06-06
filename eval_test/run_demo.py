#!/usr/bin/env python3
"""TableClaw mentor demo: skill-pipeline vs no-skill on one composite task.

Outputs a single JSON with both trajectories (for later plotting), plus a
side-by-side Markdown report. Reuses the timeline / scoring helpers from
``run_eval.py`` so the data shape stays consistent with the existing eval.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from nanobot.nanobot import Nanobot

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval_test"))

from run_eval import (  # noqa: E402  (path setup above)
    extract_tool_timeline,
    score_answer,
    _usage,
)

DEFAULT_TASK_FILE = ROOT / "eval_test/test_dataset/demo_tasks.jsonl"
DEFAULT_TASK_ID = "tc_demo_pipeline_001"

CONFIGS = {
    "skill-on": ROOT / "nanobot/configs/tableclaw-demo-skill-on.json",
    "skill-off": ROOT / "nanobot/configs/tableclaw-demo-skill-off.json",
}

TRACKED_SKILLS = (
    "tc-bigtable-header",
    "tc-bigtable-aggregate",
    "xlsx",
)

OUTPUT_DIR = ROOT / "eval_test/results/mentor_demo"
MD_REPORT = ROOT / "docs/实验评测/mentor-demo/pipeline.md"


def load_task(task_file: Path, task_id: str) -> dict[str, Any]:
    with task_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            task = json.loads(line)
            if task["id"] == task_id:
                return task
    raise SystemExit(f"task {task_id} not found in {task_file}")


def _detect_skill_in_args(args_text: str) -> str | None:
    for skill in TRACKED_SKILLS:
        if (
            f"skills/{skill}/SKILL.md" in args_text
            or f"/{skill}/SKILL.md" in args_text
        ):
            return skill
    return None


def annotate_timeline(timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Re-tag each event with our wider TRACKED_SKILLS set."""
    out = []
    for event in timeline:
        args_text = json.dumps(event.get("args") or {}, ensure_ascii=False)
        skill = _detect_skill_in_args(args_text)
        new_event = dict(event)
        new_event["skill_read"] = skill
        new_event["is_tracked_skill_read"] = skill is not None
        out.append(new_event)
    return out


async def run_one(task: dict[str, Any], mode: str) -> dict[str, Any]:
    config_path = CONFIGS[mode]
    bot = Nanobot.from_config(config_path)
    table_path = ROOT / "eval_test/test_dataset" / task["table_path"]
    prompt = task["question"].format(table_path=table_path)
    started = time.time()
    result = await bot.run(
        prompt,
        session_key=f"sdk:demo-{task['id']}-{mode}-{int(started)}",
    )
    elapsed_ms = int((time.time() - started) * 1000)
    usage = dict(getattr(bot._loop, "_last_usage", {}) or {})
    await bot._loop.close_mcp()

    timeline = annotate_timeline(extract_tool_timeline(result.messages))
    skill_events = [e for e in timeline if e["is_tracked_skill_read"]]
    selected_skills: list[str] = []
    for e in skill_events:
        skill = e.get("skill_read")
        if skill and skill not in selected_skills:
            selected_skills.append(skill)
    skill_steps = {s: next(e["step"] for e in skill_events if e["skill_read"] == s) for s in selected_skills}
    score = score_answer(task, result.content)

    return {
        "mode": mode,
        "config": str(config_path.relative_to(ROOT)),
        "task_id": task["id"],
        "elapsed_ms": elapsed_ms,
        "usage": usage,
        "tools_used": list(result.tools_used or []),
        "tool_steps": len(timeline),
        "tool_timeline": timeline,
        "skill_selected": bool(skill_events),
        "selected_skills": selected_skills,
        "skill_first_step": skill_steps,
        "skill_count": len(selected_skills),
        "first_tool": timeline[0]["tool"] if timeline else None,
        "score": score,
        "answer": result.content,
        "answer_preview": result.content[:1500],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    task = payload["task"]
    runs = payload["runs"]
    on = runs.get("skill-on")
    off = runs.get("skill-off")

    lines = [
        "# TableClaw Mentor Demo: Skill Pipeline vs No-Skill",
        "",
        f"> Generated: {payload['generated_at']}",
        "",
        "## Concept",
        "",
        "![TableAgent overview](TabelAgent.png)",
        "",
        "Without skills the generic agent has to discover the table layout itself; with TableClaw skills it picks up structural shortcuts before touching the table.",
        "",
        "![NoResult vs Result](TableAgent_NoResult.png)",
        "",
        "![Case overview](case.png)",
        "",
        "![Case detail 1](case1.png)",
        "",
        "![Case detail 2](case2.png)",
        "",
        "## Task",
        "",
        f"- **id**: `{task['id']}`",
        f"- **table**: `{task['table_path']}`",
        f"- **difficulty / case**: `{task.get('difficulty')}` / `{task.get('case')}`",
        "",
        "Prompt (verbatim):",
        "",
        "```text",
        task["question"].replace("{table_path}", f"<{task['table_path']}>"),
        "```",
        "",
    ]

    if on and off:
        lines.extend([
            "## Headline Comparison",
            "",
            "| Metric | skill-on (TableClaw pipeline) | skill-off (generic agent) |",
            "| --- | ---: | ---: |",
            f"| Skills read | `{','.join(on['selected_skills']) or '-'}` | `{','.join(off['selected_skills']) or '-'}` |",
            f"| Distinct skills used | {on['skill_count']} | {off['skill_count']} |",
            f"| Tool steps | {on['tool_steps']} | {off['tool_steps']} |",
            f"| Total tokens | {_usage(on, 'total_tokens')} | {_usage(off, 'total_tokens')} |",
            f"| Prompt tokens | {_usage(on, 'prompt_tokens')} | {_usage(off, 'prompt_tokens')} |",
            f"| Completion tokens | {_usage(on, 'completion_tokens')} | {_usage(off, 'completion_tokens')} |",
            f"| Cached tokens | {_usage(on, 'cached_tokens')} | {_usage(off, 'cached_tokens')} |",
            f"| Elapsed ms | {on['elapsed_ms']} | {off['elapsed_ms']} |",
            f"| Auto score | `{on['score']['passed']}` | `{off['score']['passed']}` |",
            "",
        ])
        on_tokens = _usage(on, "total_tokens")
        off_tokens = _usage(off, "total_tokens")
        if off_tokens:
            delta = on_tokens - off_tokens
            pct = delta / off_tokens * 100
            lines.append(f"Δ total tokens (on - off) = `{delta}` (`{pct:+.1f}%`)")
            lines.append("")

    mode_runs: list[tuple[str, dict[str, Any]]] = []
    if on:
        mode_runs.append(("skill-on (TableClaw pipeline)", on))
    if off:
        mode_runs.append(("skill-off (generic agent)", off))

    for mode_label, run in mode_runs:
        lines.extend([
            f"## Tool Timeline — {mode_label}",
            "",
            "| Step | Tool | Skill read | Args preview |",
            "| ---: | --- | --- | --- |",
        ])
        for e in run["tool_timeline"]:
            lines.append(
                f"| {e['step']} | `{e['tool']}` | `{e.get('skill_read') or '-'}` | {e['args_preview']} |"
            )
        lines.extend([
            "",
            "Answer:",
            "",
            "```text",
            run["answer"],
            "```",
            "",
        ])

    lines.append("## Score Detail")
    lines.append("")
    for mode, run in runs.items():
        lines.append(f"### {mode}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(run["score"], ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-file", default=str(DEFAULT_TASK_FILE))
    parser.add_argument("--task-id", default=DEFAULT_TASK_ID)
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=list(CONFIGS),
        default=["skill-on", "skill-off"],
    )
    parser.add_argument("--json-output", default=str(OUTPUT_DIR / "run.json"))
    parser.add_argument("--md-output", default=str(MD_REPORT))
    args = parser.parse_args()

    if not os.environ.get("DASHSCOPE_API_KEY"):
        os.environ["DASHSCOPE_API_KEY"] = "sk-439b8ec88a614cd5a74f7c2cd1d9714f"

    task_file = Path(args.task_file) if Path(args.task_file).is_absolute() else ROOT / args.task_file
    task = load_task(task_file, args.task_id)

    runs: dict[str, dict[str, Any]] = {}
    for mode in args.modes:
        print(f"[demo] running {task['id']} / {mode} ...", flush=True)
        runs[mode] = await run_one(task, mode)

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "task": task,
        "runs": runs,
        "tracked_skills": list(TRACKED_SKILLS),
    }

    json_path = Path(args.json_output) if Path(args.json_output).is_absolute() else ROOT / args.json_output
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Per-mode trimmed timelines for plotting convenience.
    for mode, run in runs.items():
        slim = {
            "mode": mode,
            "task_id": run["task_id"],
            "selected_skills": run["selected_skills"],
            "skill_first_step": run["skill_first_step"],
            "tool_timeline": [
                {
                    "step": e["step"],
                    "tool": e["tool"],
                    "skill_read": e.get("skill_read"),
                    "args_preview": e["args_preview"],
                }
                for e in run["tool_timeline"]
            ],
            "usage": run["usage"],
            "tool_steps": run["tool_steps"],
            "elapsed_ms": run["elapsed_ms"],
            "score_passed": run["score"]["passed"],
        }
        slim_path = json_path.parent / f"timeline_{mode.replace('-', '_')}.json"
        slim_path.write_text(json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = Path(args.md_output) if Path(args.md_output).is_absolute() else ROOT / args.md_output
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    # Timestamped per-run archive so subsequent runs don't overwrite history.
    archive_root = json_path.parent / "runs"
    archive_dir = archive_root / time.strftime("%Y%m%d-%H%M%S")
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "run.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (archive_dir / "pipeline.md").write_text(render_markdown(payload), encoding="utf-8")
    for mode in runs:
        slim_src = json_path.parent / f"timeline_{mode.replace('-', '_')}.json"
        if slim_src.exists():
            (archive_dir / slim_src.name).write_text(
                slim_src.read_text(encoding="utf-8"), encoding="utf-8"
            )

    print(f"\nJSON   : {json_path}")
    print(f"MD     : {md_path}")
    print(f"Archive: {archive_dir}")
    print(f"Skill-on   skills: {runs.get('skill-on', {}).get('selected_skills')}")
    print(f"Skill-off  skills: {runs.get('skill-off', {}).get('selected_skills')}")


if __name__ == "__main__":
    asyncio.run(main())
