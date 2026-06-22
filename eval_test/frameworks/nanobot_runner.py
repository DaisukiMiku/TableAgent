from __future__ import annotations

import time
import uuid
from typing import Any

from nanobot.nanobot import Nanobot

from run_eval import TRACKED_TABLECLAW_TOOLS, extract_tool_timeline

from .base import FrameworkRunContext, FrameworkRunResult, ensure_framework_result


class NanobotRunner:
    name = "nanobot"

    async def run(
        self,
        task: dict[str, Any],
        prompt: str,
        context: FrameworkRunContext,
    ) -> FrameworkRunResult:
        if context.config_path is None:
            raise ValueError("NanobotRunner requires config_path")

        bot = Nanobot.from_config(context.config_path)
        started = time.time()
        result = await bot.run(
            prompt,
            session_key=(
                f"sdk:gold-parallel-{context.run_id}-{task['id']}-{context.mode}-"
                f"{int(started)}-{uuid.uuid4().hex[:8]}"
            ),
        )
        elapsed_ms = int((time.time() - started) * 1000)
        usage = dict(getattr(bot._loop, "_last_usage", {}) or {})
        await bot._loop.close_mcp()

        timeline = extract_tool_timeline(result.messages)
        tableclaw_tools = [
            event for event in timeline if event.get("tool") in TRACKED_TABLECLAW_TOOLS
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
                dict.fromkeys(event.get("skill_read") for event in skill_events if event.get("skill_read"))
            ),
            "framework_trace": {
                "framework": context.framework,
                "runner": self.name,
                "message_count": len(result.messages),
            },
        }
        return ensure_framework_result(payload)
