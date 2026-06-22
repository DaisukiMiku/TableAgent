from __future__ import annotations

import importlib
import inspect
import time
from collections.abc import Callable
from typing import Any

from .base import FrameworkRunContext, FrameworkRunResult, ensure_framework_result


MISSING_DEPENDENCY_MESSAGE = (
    "Install optional framework dependencies with: "
    "nanobot/.venv/bin/python -m pip install -r eval_test/frameworks/requirements-frameworks.txt"
)


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
        return {
            "AssistantAgent": agents.AssistantAgent,
            "RoundRobinGroupChat": teams.RoundRobinGroupChat,
            "MaxMessageTermination": conditions.MaxMessageTermination,
            "OpenAIChatCompletionClient": openai.OpenAIChatCompletionClient,
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
        tools: list[Callable[..., Any]] = []
        schemas = {schema["function"]["name"]: schema["function"] for schema in adapter.openai_tool_schemas()}

        def make_tool(tool_name: str, description: str) -> Callable[..., Any]:
            async def invoke_tool(**kwargs: Any) -> str:
                output, event = await adapter.call(tool_name, kwargs)
                tool_timeline.append(event)
                return output

            invoke_tool.__name__ = tool_name
            invoke_tool.__doc__ = description
            return invoke_tool

        for tool_name in adapter.tool_names:
            schema = schemas[tool_name]
            tools.append(make_tool(tool_name, schema["description"]))

        model_client = autogen["OpenAIChatCompletionClient"](
            model=context.model,
            api_key=context.api_key,
            base_url=context.base_url,
        )
        AssistantAgent = autogen["AssistantAgent"]
        RoundRobinGroupChat = autogen["RoundRobinGroupChat"]
        MaxMessageTermination = autogen["MaxMessageTermination"]

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
            tools=tools,
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

        started = time.time()
        try:
            result = await team.run(task=prompt)
        finally:
            close = getattr(model_client, "close", None)
            if callable(close):
                close_result = close()
                if inspect.isawaitable(close_result):
                    await close_result
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
