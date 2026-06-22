from __future__ import annotations

import importlib
import time
from collections.abc import Callable
from typing import Any

from openai import AsyncOpenAI

from .base import FrameworkRunContext, FrameworkRunResult, ensure_framework_result


MISSING_DEPENDENCY_MESSAGE = (
    "Install optional framework dependencies with: "
    "nanobot/.venv/bin/python -m pip install -r eval_test/frameworks/requirements-frameworks.txt"
)


class OpenAIAgentsRunner:
    name = "openai-agents-sdk"

    def __init__(self, import_module: Callable[[str], Any] = importlib.import_module) -> None:
        self._import_module = import_module

    def _load_agents_sdk(self) -> Any:
        try:
            return self._import_module("agents")
        except ModuleNotFoundError as exc:
            raise RuntimeError(MISSING_DEPENDENCY_MESSAGE) from exc

    async def run(
        self,
        task: dict[str, Any],
        prompt: str,
        context: FrameworkRunContext,
    ) -> FrameworkRunResult:
        agents = self._load_agents_sdk()
        from .tableclaw_tools import TableClawToolAdapter

        adapter = TableClawToolAdapter(workspace=context.workspace)
        tool_timeline: list[dict[str, Any]] = []
        tools: list[Any] = []

        for schema in adapter.openai_tool_schemas():
            fn = schema["function"]

            async def invoke_tool(_ctx: Any, args: str, *, tool_name: str = fn["name"]) -> str:
                output, event = await adapter.call(tool_name, args)
                tool_timeline.append(event)
                return output

            tools.append(
                agents.FunctionTool(
                    name=fn["name"],
                    description=fn["description"],
                    params_json_schema=fn["parameters"],
                    on_invoke_tool=invoke_tool,
                    strict_json_schema=False,
                )
            )

        client = AsyncOpenAI(api_key=context.api_key, base_url=context.base_url)
        model = agents.OpenAIChatCompletionsModel(model=context.model, openai_client=client)
        agent = agents.Agent(
            name="TableClaw Analyst",
            instructions=(
                "你是 TableClaw 表格分析 agent。使用工具定位表、检查 schema、抽取数据，"
                "最后用中文直接回答，并列出使用的表文件名。"
            ),
            model=model,
            tools=tools,
        )

        started = time.time()
        result = await agents.Runner.run(agent, prompt)
        elapsed_ms = int((time.time() - started) * 1000)

        successful_tools = [
            event["tool"] for event in tool_timeline if event.get("ok") and event.get("tool")
        ]
        tableclaw_tools_used = list(dict.fromkeys(successful_tools))
        payload: dict[str, Any] = {
            "answer": str(result.final_output),
            "usage": {},
            "elapsed_ms": elapsed_ms,
            "tools_used": tableclaw_tools_used,
            "tool_timeline": tool_timeline,
            "retrieval_tool_called": "tableclaw_retrieve_tables" in tableclaw_tools_used,
            "inspect_tool_called": "tableclaw_inspect" in tableclaw_tools_used,
            "tableclaw_tools_used": tableclaw_tools_used,
            "skill_selected": False,
            "selected_skills": [],
            "framework_trace": {
                "framework": context.framework,
                "runner": self.name,
                "task_id": task.get("id"),
                "raw_result_type": type(result).__name__,
            },
        }
        return ensure_framework_result(payload)
