from __future__ import annotations

import importlib
import time
from collections.abc import Callable
from typing import Any, TypedDict

from .base import FrameworkRunContext, FrameworkRunResult, ensure_framework_result


MISSING_DEPENDENCY_MESSAGE = (
    "Install optional framework dependencies with: "
    "nanobot/.venv/bin/python -m pip install -r eval_test/frameworks/requirements-frameworks.txt"
)


def route_after_verify(state: dict[str, Any]) -> str:
    verification = state.get("verification") or {}
    if verification.get("passed"):
        return "final"
    if int(state.get("repair_count") or 0) >= int(state.get("max_repairs") or 0):
        return "final"
    return "solve"


class LangGraphState(TypedDict):
    messages: list[Any]
    iteration_count: int
    verification: dict[str, Any]
    repair_count: int
    max_repairs: int


class LangGraphRunner:
    name = "langgraph"

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

    def _load_langgraph(self) -> dict[str, Any]:
        graph = self._import_optional_module("langgraph.graph")
        messages = self._import_optional_module("langchain_core.messages")
        openai = self._import_optional_module("langchain_openai")
        tools = self._import_optional_module("langchain_core.tools")
        return {
            "StateGraph": graph.StateGraph,
            "START": graph.START,
            "END": graph.END,
            "HumanMessage": messages.HumanMessage,
            "SystemMessage": messages.SystemMessage,
            "AIMessage": messages.AIMessage,
            "ToolMessage": messages.ToolMessage,
            "ChatOpenAI": openai.ChatOpenAI,
            "StructuredTool": tools.StructuredTool,
        }

    async def run(
        self,
        task: dict[str, Any],
        prompt: str,
        context: FrameworkRunContext,
    ) -> FrameworkRunResult:
        langgraph = self._load_langgraph()

        from .tableclaw_tools import TableClawToolAdapter

        adapter = TableClawToolAdapter(workspace=context.workspace)
        tool_timeline: list[dict[str, Any]] = []
        structured_tools: list[Any] = []
        StructuredTool = langgraph["StructuredTool"]

        for schema in adapter.openai_tool_schemas():
            fn = schema["function"]

            async def invoke_tool(*, tool_name: str = fn["name"], **kwargs: Any) -> str:
                output, event = await adapter.call(tool_name, kwargs)
                tool_timeline.append(event)
                return output

            structured_tools.append(
                StructuredTool.from_function(
                    coroutine=invoke_tool,
                    name=fn["name"],
                    description=fn["description"],
                    args_schema=fn["parameters"],
                )
            )

        model = langgraph["ChatOpenAI"](
            model=context.model,
            temperature=0,
            api_key=context.api_key,
            base_url=context.base_url,
        ).bind_tools(structured_tools)

        SystemMessage = langgraph["SystemMessage"]
        HumanMessage = langgraph["HumanMessage"]
        ToolMessage = langgraph["ToolMessage"]
        StateGraph = langgraph["StateGraph"]
        START = langgraph["START"]
        END = langgraph["END"]

        async def solve_node(state: LangGraphState) -> LangGraphState:
            response = await model.ainvoke(state["messages"])
            return {
                "messages": [*state["messages"], response],
                "iteration_count": state["iteration_count"] + 1,
                "verification": state.get("verification") or {},
                "repair_count": state.get("repair_count", 0),
                "max_repairs": state.get("max_repairs", 1),
            }

        async def tool_node(state: LangGraphState) -> LangGraphState:
            messages = list(state["messages"])
            last = messages[-1]
            for tool_call in getattr(last, "tool_calls", []) or []:
                output, event = await adapter.call(
                    tool_call["name"],
                    tool_call.get("args") or {},
                )
                tool_timeline.append(event)
                messages.append(
                    ToolMessage(
                        content=output,
                        tool_call_id=str(tool_call.get("id") or tool_call["name"]),
                    )
                )
            return {
                "messages": messages,
                "iteration_count": state["iteration_count"],
                "verification": state.get("verification") or {},
                "repair_count": state.get("repair_count", 0),
                "max_repairs": state.get("max_repairs", 1),
            }

        def route_after_solve(state: LangGraphState) -> str:
            if state["iteration_count"] >= 8:
                return "final"
            last = state["messages"][-1]
            if getattr(last, "tool_calls", []) or []:
                return "tools"
            return "final"

        async def verify_node(state: dict[str, Any]) -> dict[str, Any]:
            messages = list(state["messages"])
            last = messages[-1]
            content = str(getattr(last, "content", ""))
            passed = all(marker in content for marker in ("使用", "完成"))
            verification = {
                "passed": passed,
                "reason": (
                    "answer includes source/completion markers"
                    if passed
                    else "answer lacks source/completion markers"
                ),
            }
            repair_count = int(state.get("repair_count") or 0)
            if not passed:
                repair_count += 1
                messages.append(
                    HumanMessage(
                        content="请修正上一个答案：必须说明使用了哪些上传表，并说明是否成功完成。"
                    )
                )
            return {
                "messages": messages,
                "verification": verification,
                "repair_count": repair_count,
                "iteration_count": state["iteration_count"],
                "max_repairs": state.get("max_repairs", 1),
            }

        graph_builder = StateGraph(LangGraphState)
        graph_builder.add_node("solve", solve_node)
        graph_builder.add_node("tools", tool_node)
        graph_builder.add_node("verify", verify_node)
        graph_builder.add_edge(START, "solve")
        graph_builder.add_conditional_edges(
            "solve",
            route_after_solve,
            {"tools": "tools", "final": "verify"},
        )
        graph_builder.add_edge("tools", "solve")
        graph_builder.add_conditional_edges(
            "verify",
            route_after_verify,
            {"solve": "solve", "final": END},
        )
        graph = graph_builder.compile()

        initial_state: LangGraphState = {
            "messages": [
                SystemMessage(
                    content=(
                        "你是 TableClaw 表格分析 agent。使用工具定位表、检查 schema、抽取数据，"
                        "最后用中文直接回答，并列出使用的表文件名。"
                    )
                ),
                HumanMessage(content=prompt),
            ],
            "iteration_count": 0,
            "verification": {},
            "repair_count": 0,
            "max_repairs": 1,
        }

        started = time.time()
        result_state = await graph.ainvoke(initial_state)
        elapsed_ms = int((time.time() - started) * 1000)

        successful_tools = [
            event["tool"] for event in tool_timeline if event.get("ok") and event.get("tool")
        ]
        tableclaw_tools_used = list(dict.fromkeys(successful_tools))
        payload: dict[str, Any] = {
            "answer": str(result_state["messages"][-1].content),
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
                "message_count": len(result_state["messages"]),
                "iteration_count": result_state["iteration_count"],
                "verification": result_state.get("verification") or {},
                "repair_count": result_state.get("repair_count") or 0,
            },
        }
        return ensure_framework_result(payload)
