from __future__ import annotations

import importlib
import inspect
import sys
import time
from collections.abc import Callable
from typing import Any

from .base import FrameworkRunContext, FrameworkRunResult, ensure_framework_result


MISSING_DEPENDENCY_MESSAGE = (
    "Install optional framework dependencies with: "
    "nanobot/.venv/bin/python -m pip install -r eval_test/frameworks/requirements-frameworks.txt"
)


class _TableClawWorkbench:
    def __init__(
        self,
        adapter: Any,
        tool_result_cls: type[Any],
        text_result_content_cls: type[Any],
        tool_timeline: list[dict[str, Any]],
    ) -> None:
        self._adapter = adapter
        self._tool_result_cls = tool_result_cls
        self._text_result_content_cls = text_result_content_cls
        self._tool_timeline = tool_timeline

    async def list_tools(self) -> list[dict[str, Any]]:
        return [schema["function"] for schema in self._adapter.openai_tool_schemas()]

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        cancellation_token: Any | None = None,
        call_id: str | None = None,
    ) -> Any:
        output, event = await self._adapter.call(name, dict(arguments or {}))
        self._tool_timeline.append(event)
        return self._tool_result_cls(
            name=name,
            result=[self._text_result_content_cls(content=output)],
            is_error=not event.get("ok"),
        )

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def reset(self) -> None:
        return None

    async def save_state(self) -> dict[str, Any]:
        return {}

    async def load_state(self, state: dict[str, Any]) -> None:
        return None


class AutoGenRunner:
    name = "autogen"

    def __init__(self, import_module: Callable[[str], Any] = importlib.import_module) -> None:
        self._import_module = import_module

    def _import_optional_module(self, module_name: str) -> Any:
        try:
            return self._import_module(module_name)
        except ModuleNotFoundError as exc:
            missing_name = exc.name
            if missing_name is None and exc.args and isinstance(exc.args[0], str):
                missing_name = exc.args[0]
            requested_top_level = module_name.split(".", maxsplit=1)[0]
            if missing_name in {module_name, requested_top_level}:
                raise RuntimeError(MISSING_DEPENDENCY_MESSAGE) from exc
            raise

    def _load_autogen(self) -> dict[str, Any]:
        agents = self._import_optional_module("autogen_agentchat.agents")
        teams = self._import_optional_module("autogen_agentchat.teams")
        conditions = self._import_optional_module("autogen_agentchat.conditions")
        openai = self._import_optional_module("autogen_ext.models.openai")
        tools = self._import_optional_module("autogen_core.tools")
        return {
            "AssistantAgent": agents.AssistantAgent,
            "RoundRobinGroupChat": teams.RoundRobinGroupChat,
            "MaxMessageTermination": conditions.MaxMessageTermination,
            "OpenAIChatCompletionClient": openai.OpenAIChatCompletionClient,
            "ToolResult": tools.ToolResult,
            "TextResultContent": tools.TextResultContent,
        }

    async def run(
        self,
        task: dict[str, Any],
        prompt: str,
        context: FrameworkRunContext,
    ) -> FrameworkRunResult:
        autogen = self._load_autogen()

        from .tableclaw_tools import TableClawToolAdapter

        adapter = TableClawToolAdapter(workspace=context.workspace)
        tool_timeline: list[dict[str, Any]] = []
        workbench = _TableClawWorkbench(
            adapter=adapter,
            tool_result_cls=autogen["ToolResult"],
            text_result_content_cls=autogen["TextResultContent"],
            tool_timeline=tool_timeline,
        )

        model_client = autogen["OpenAIChatCompletionClient"](
            model=context.model,
            api_key=context.api_key,
            base_url=context.base_url,
        )
        AssistantAgent = autogen["AssistantAgent"]
        RoundRobinGroupChat = autogen["RoundRobinGroupChat"]
        MaxMessageTermination = autogen["MaxMessageTermination"]

        started = time.time()
        try:
            planner = AssistantAgent(
                "planner",
                model_client=model_client,
                system_message=(
                    "Understand the user's table question and plan the minimum TableClaw tool calls "
                    "needed to answer it."
                ),
            )
            analyst = AssistantAgent(
                "analyst",
                model_client=model_client,
                workbench=workbench,
                system_message=(
                    "Use TableClaw tools to locate relevant tables, inspect schemas, extract data, "
                    "and provide evidence for the answer."
                ),
            )
            verifier = AssistantAgent(
                "verifier",
                model_client=model_client,
                system_message=(
                    "Check that the final answer includes table, month, scope, metric, value, and "
                    "completion status. Do not use or mention any gold answer."
                ),
            )
            team = RoundRobinGroupChat(
                [planner, analyst, verifier],
                termination_condition=MaxMessageTermination(max_messages=9),
            )
            result = await team.run(task=prompt)
        finally:
            pending_exc = sys.exc_info()[0] is not None
            close = getattr(model_client, "close", None)
            if callable(close):
                try:
                    close_result = close()
                    if inspect.isawaitable(close_result):
                        await close_result
                except Exception:
                    if not pending_exc:
                        raise
        elapsed_ms = int((time.time() - started) * 1000)

        messages = list(getattr(result, "messages", []) or [])
        answer = str(getattr(messages[-1], "content", "")) if messages else ""
        successful_tools = [
            event["tool"] for event in tool_timeline if event.get("ok") and event.get("tool")
        ]
        tableclaw_tools_used = list(dict.fromkeys(successful_tools))
        payload: dict[str, Any] = {
            "answer": answer,
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
                "message_count": len(messages),
            },
        }
        return ensure_framework_result(payload)
