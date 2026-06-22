from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .base import FrameworkRunContext, FrameworkRunResult, ensure_framework_result


EvalHelpers = tuple[tuple[str, ...], Callable[[list[dict[str, Any]]], list[dict[str, Any]]]]


def _default_nanobot_factory(config_path: Path) -> Any:
    from nanobot.nanobot import Nanobot

    return Nanobot.from_config(config_path)


def _default_eval_helpers() -> EvalHelpers:
    try:
        from eval_test.run_eval import TRACKED_TABLECLAW_TOOLS, extract_tool_timeline
    except ModuleNotFoundError as exc:
        if exc.name not in {"eval_test", "eval_test.run_eval"}:
            raise
        from run_eval import TRACKED_TABLECLAW_TOOLS, extract_tool_timeline

    return TRACKED_TABLECLAW_TOOLS, extract_tool_timeline


class NanobotRunner:
    name = "nanobot"

    def __init__(
        self,
        nanobot_factory: Callable[[Path], Any] | None = None,
        eval_helpers: EvalHelpers | None = None,
    ) -> None:
        self._nanobot_factory = nanobot_factory or _default_nanobot_factory
        self._eval_helpers = eval_helpers

    async def run(
        self,
        task: dict[str, Any],
        prompt: str,
        context: FrameworkRunContext,
    ) -> FrameworkRunResult:
        if context.config_path is None:
            raise ValueError("NanobotRunner requires config_path")

        bot = self._nanobot_factory(context.config_path)
        started = time.time()
        try:
            result = await bot.run(
                prompt,
                session_key=(
                    f"sdk:gold-parallel-{context.run_id}-{task['id']}-{context.mode}-"
                    f"{int(started)}-{uuid.uuid4().hex[:8]}"
                ),
            )
            elapsed_ms = int((time.time() - started) * 1000)
            usage = dict(getattr(bot._loop, "_last_usage", {}) or {})

            tracked_tableclaw_tools, extract_tool_timeline = (
                self._eval_helpers or _default_eval_helpers()
            )
            timeline = extract_tool_timeline(result.messages)
            tableclaw_tools = [
                event for event in timeline if event.get("tool") in tracked_tableclaw_tools
            ]
            skill_events = [event for event in timeline if event.get("is_tracked_skill_read")]
            payload: dict[str, Any] = {
                "answer": result.content,
                "usage": usage,
                "elapsed_ms": elapsed_ms,
                "tools_used": result.tools_used,
                "tool_timeline": timeline,
                "retrieval_tool_called": any(
                    event.get("tool") == "tableclaw_retrieve_tables" for event in tableclaw_tools
                ),
                "inspect_tool_called": any(
                    event.get("tool") == "tableclaw_inspect" for event in tableclaw_tools
                ),
                "tableclaw_tools_used": list(
                    dict.fromkeys(event.get("tool") for event in tableclaw_tools if event.get("tool"))
                ),
                "skill_selected": bool(skill_events),
                "selected_skills": list(
                    dict.fromkeys(
                        event.get("skill_read") for event in skill_events if event.get("skill_read")
                    )
                ),
                "framework_trace": {
                    "framework": context.framework,
                    "runner": self.name,
                    "message_count": len(result.messages),
                },
            }
            return ensure_framework_result(payload)
        finally:
            await bot._loop.close_mcp()
