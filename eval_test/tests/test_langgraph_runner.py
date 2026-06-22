from __future__ import annotations

import sys
from collections.abc import Callable
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from frameworks.base import FrameworkRunContext
from frameworks.langgraph_runner import LangGraphRunner


def _context() -> FrameworkRunContext:
    return FrameworkRunContext(
        framework="langgraph",
        mode="skill-off",
        run_id="unit-run",
        config_path=None,
        workspace="/tmp/workspace",
        model="deepseek-v4-pro",
        base_url="https://example.invalid/v1",
        api_key="test-key",
    )


def _install_fake_tableclaw_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAdapter:
        def __init__(self, workspace: str) -> None:
            self.workspace = workspace

        def openai_tool_schemas(self) -> list[dict[str, Any]]:
            return []

        async def call(self, name: str, arguments: dict[str, Any]) -> tuple[str, dict[str, Any]]:
            raise AssertionError(f"unexpected tool call: {name} {arguments}")

    fake_tools_module = ModuleType("frameworks.tableclaw_tools")
    fake_tools_module.TableClawToolAdapter = FakeAdapter
    monkeypatch.setitem(sys.modules, "frameworks.tableclaw_tools", fake_tools_module)


def _fake_langgraph_import(
    responses: list[Any],
    *,
    iteration_count_override: int | None = None,
    max_repairs_override: int | None = None,
) -> tuple[Callable[[str], Any], type[Any]]:
    start = "__start__"
    end = "__end__"

    class FakeMessage:
        def __init__(self, content: str, **kwargs: Any) -> None:
            self.content = content
            self.tool_calls = kwargs.get("tool_calls", [])

    class FakeHumanMessage(FakeMessage):
        pass

    class FakeSystemMessage(FakeMessage):
        pass

    class FakeAIMessage(FakeMessage):
        pass

    class FakeToolMessage(FakeMessage):
        pass

    class FakeChatOpenAI:
        instance: "FakeChatOpenAI"

        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs
            self.responses = [
                FakeAIMessage(
                    response.get("content", ""),
                    tool_calls=response.get("tool_calls", []),
                )
                if isinstance(response, dict)
                else FakeAIMessage(response)
                for response in responses
            ]
            self.calls: list[list[Any]] = []
            FakeChatOpenAI.instance = self

        def bind_tools(self, tools: list[Any]) -> "FakeChatOpenAI":
            self.tools = tools
            return self

        async def ainvoke(self, messages: list[Any]) -> FakeAIMessage:
            self.calls.append(list(messages))
            if not self.responses:
                raise AssertionError("no fake model responses left")
            return self.responses.pop(0)

    class FakeStructuredTool:
        @classmethod
        def from_function(cls, **kwargs: Any) -> Any:
            return SimpleNamespace(**kwargs)

    class FakeCompiledGraph:
        def __init__(self, builder: "FakeStateGraph") -> None:
            self.builder = builder

        async def ainvoke(self, initial_state: dict[str, Any]) -> dict[str, Any]:
            state = dict(initial_state)
            if iteration_count_override is not None:
                state["iteration_count"] = iteration_count_override
            if max_repairs_override is not None:
                state["max_repairs"] = max_repairs_override

            current = self.builder.edges[start]
            for _ in range(20):
                state = await self.builder.nodes[current](state)
                if current in self.builder.conditional_edges:
                    route_fn, mapping = self.builder.conditional_edges[current]
                    current = mapping[route_fn(state)]
                else:
                    current = self.builder.edges[current]
                if current == end:
                    return state
            raise AssertionError("fake graph did not terminate")

    class FakeStateGraph:
        def __init__(self, state_type: Any) -> None:
            self.state_type = state_type
            self.nodes: dict[str, Any] = {}
            self.edges: dict[str, str] = {}
            self.conditional_edges: dict[str, tuple[Any, dict[str, str]]] = {}

        def add_node(self, name: str, node: Any) -> None:
            self.nodes[name] = node

        def add_edge(self, source: str, target: str) -> None:
            self.edges[source] = target

        def add_conditional_edges(
            self,
            source: str,
            route_fn: Any,
            mapping: dict[str, str],
        ) -> None:
            self.conditional_edges[source] = (route_fn, mapping)

        def compile(self) -> FakeCompiledGraph:
            return FakeCompiledGraph(self)

    def fake_import(name: str) -> Any:
        modules = {
            "langgraph.graph": SimpleNamespace(StateGraph=FakeStateGraph, START=start, END=end),
            "langchain_core.messages": SimpleNamespace(
                HumanMessage=FakeHumanMessage,
                SystemMessage=FakeSystemMessage,
                AIMessage=FakeAIMessage,
                ToolMessage=FakeToolMessage,
            ),
            "langchain_openai": SimpleNamespace(ChatOpenAI=FakeChatOpenAI),
            "langchain_core.tools": SimpleNamespace(StructuredTool=FakeStructuredTool),
        }
        return modules[name]

    return fake_import, FakeChatOpenAI


def test_langgraph_runner_name() -> None:
    assert LangGraphRunner().name == "langgraph"


def test_langgraph_runner_missing_dependency_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_import(name: str):
        raise ModuleNotFoundError(name)

    runner = LangGraphRunner(import_module=fake_import)

    with pytest.raises(RuntimeError, match="Install optional framework dependencies"):
        runner._load_langgraph()


@pytest.mark.asyncio
async def test_langgraph_runner_repairs_failed_verification_with_second_model_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_tableclaw_adapter(monkeypatch)
    fake_import, fake_model = _fake_langgraph_import(
        ["缺少必要标记", "使用 sales.csv，已完成分析。"]
    )

    result = await LangGraphRunner(import_module=fake_import).run(
        {"id": "case_001"},
        "用户问题：销售额是多少？",
        _context(),
    )

    assert result["answer"] == "使用 sales.csv，已完成分析。"
    assert len(fake_model.instance.calls) == 2
    assert result["framework_trace"]["repair_count"] == 1
    assert result["framework_trace"]["verification"]["passed"] is True


@pytest.mark.asyncio
async def test_langgraph_runner_capped_failure_keeps_last_model_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_tableclaw_adapter(monkeypatch)
    fake_import, _fake_model = _fake_langgraph_import(
        ["仍然缺少必要标记"],
        max_repairs_override=0,
    )

    result = await LangGraphRunner(import_module=fake_import).run(
        {"id": "case_001"},
        "用户问题：销售额是多少？",
        _context(),
    )

    assert result["answer"] == "仍然缺少必要标记"
    assert "请修正上一个答案" not in result["answer"]
    assert result["framework_trace"]["repair_count"] == 0
    assert result["framework_trace"]["verification"]["passed"] is False
    assert result["framework_trace"]["verification"]["repair_requested"] is False


@pytest.mark.asyncio
async def test_langgraph_runner_does_not_repair_pending_tool_calls_at_solve_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_tableclaw_adapter(monkeypatch)
    fake_import, fake_model = _fake_langgraph_import(
        [
            {
                "content": "准备调用工具",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "name": "tableclaw_retrieve_tables",
                        "args": {"query": "sales"},
                    }
                ],
            }
        ],
        iteration_count_override=7,
    )

    result = await LangGraphRunner(import_module=fake_import).run(
        {"id": "case_001"},
        "用户问题：销售额是多少？",
        _context(),
    )

    assert result["answer"] == "准备调用工具"
    assert "请修正上一个答案" not in result["answer"]
    assert len(fake_model.instance.calls) == 1
    assert result["framework_trace"]["iteration_count"] == 8
    assert result["framework_trace"]["verification"]["passed"] is False
    assert result["framework_trace"]["verification"]["repair_requested"] is False
    assert (
        result["framework_trace"]["verification"]["reason"]
        == "answer has pending tool calls at solve cap"
    )
