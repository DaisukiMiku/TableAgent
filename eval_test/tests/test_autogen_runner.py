from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from frameworks.base import FrameworkRunContext
from frameworks.autogen_runner import AutoGenRunner


def _context() -> FrameworkRunContext:
    return FrameworkRunContext(
        framework="autogen",
        mode="skill-off",
        run_id="unit-run",
        config_path=None,
        workspace="/tmp/workspace",
        model="deepseek-v4-pro",
        base_url="https://example.invalid/v1",
        api_key="test-key",
    )


def test_autogen_runner_name() -> None:
    assert AutoGenRunner().name == "autogen"


def test_autogen_runner_missing_dependency_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_import(name: str):
        raise ModuleNotFoundError(name)

    runner = AutoGenRunner(import_module=fake_import)

    with pytest.raises(RuntimeError, match="Install optional framework dependencies"):
        runner._load_autogen()


@pytest.mark.asyncio
async def test_autogen_runner_uses_workbench_with_tableclaw_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAdapter:
        instances: list["FakeAdapter"] = []

        def __init__(self, workspace: str) -> None:
            self.workspace = workspace
            self.calls: list[tuple[str, dict[str, Any]]] = []
            FakeAdapter.instances.append(self)

        def openai_tool_schemas(self) -> list[dict[str, Any]]:
            return [
                {
                    "type": "function",
                    "function": {
                        "name": "tableclaw_retrieve_tables",
                        "description": "Retrieve relevant tables.",
                        "parameters": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                    },
                }
            ]

        async def call(self, name: str, arguments: dict[str, Any]) -> tuple[str, dict[str, Any]]:
            self.calls.append((name, arguments))
            return "retrieved tables", {"tool": name, "args": arguments, "ok": True}

    fake_tools_module = ModuleType("frameworks.tableclaw_tools")
    fake_tools_module.TableClawToolAdapter = FakeAdapter
    monkeypatch.setitem(sys.modules, "frameworks.tableclaw_tools", fake_tools_module)

    class FakeTextResultContent:
        def __init__(self, content: str) -> None:
            self.content = content

    class FakeToolResult:
        def __init__(self, *, name: str, result: list[Any], is_error: bool) -> None:
            self.name = name
            self.result = result
            self.is_error = is_error

    class FakeModelClient:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs
            self.closed = False

        async def close(self) -> None:
            self.closed = True

    agents: list[Any] = []

    class FakeAssistantAgent:
        def __init__(self, name: str, **kwargs: Any) -> None:
            self.name = name
            self.kwargs = kwargs
            agents.append(self)

    class FakeRoundRobinGroupChat:
        def __init__(self, participants: list[Any], *, termination_condition: Any) -> None:
            self.participants = participants
            self.termination_condition = termination_condition

        async def run(self, *, task: str) -> Any:
            return SimpleNamespace(messages=[SimpleNamespace(content="最终答案")])

    class FakeMaxMessageTermination:
        def __init__(self, *, max_messages: int) -> None:
            self.max_messages = max_messages

    def fake_import(name: str) -> Any:
        modules = {
            "autogen_agentchat.agents": SimpleNamespace(AssistantAgent=FakeAssistantAgent),
            "autogen_agentchat.teams": SimpleNamespace(RoundRobinGroupChat=FakeRoundRobinGroupChat),
            "autogen_agentchat.conditions": SimpleNamespace(MaxMessageTermination=FakeMaxMessageTermination),
            "autogen_ext.models.openai": SimpleNamespace(OpenAIChatCompletionClient=FakeModelClient),
            "autogen_core.tools": SimpleNamespace(
                ToolResult=FakeToolResult,
                TextResultContent=FakeTextResultContent,
            ),
        }
        return modules[name]

    result = await AutoGenRunner(import_module=fake_import).run(
        {"id": "case_001"},
        "用户问题：四川是多少？",
        _context(),
    )

    analyst = next(agent for agent in agents if agent.name == "analyst")
    assert "tools" not in analyst.kwargs
    workbench = analyst.kwargs["workbench"]
    assert await workbench.list_tools() == [
        {
            "name": "tableclaw_retrieve_tables",
            "description": "Retrieve relevant tables.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        }
    ]

    tool_result = await workbench.call_tool(
        "tableclaw_retrieve_tables",
        {"query": "四川"},
    )

    assert result["answer"] == "最终答案"
    assert FakeAdapter.instances[0].calls == [("tableclaw_retrieve_tables", {"query": "四川"})]
    assert isinstance(tool_result, FakeToolResult)
    assert tool_result.name == "tableclaw_retrieve_tables"
    assert tool_result.result[0].content == "retrieved tables"
    assert tool_result.is_error is False


@pytest.mark.asyncio
async def test_autogen_runner_closes_model_client_when_agent_construction_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAdapter:
        def __init__(self, workspace: str) -> None:
            self.workspace = workspace

        def openai_tool_schemas(self) -> list[dict[str, Any]]:
            return []

    fake_tools_module = ModuleType("frameworks.tableclaw_tools")
    fake_tools_module.TableClawToolAdapter = FakeAdapter
    monkeypatch.setitem(sys.modules, "frameworks.tableclaw_tools", fake_tools_module)

    class FakeModelClient:
        instance: "FakeModelClient"

        def __init__(self, **kwargs: Any) -> None:
            self.closed = False
            FakeModelClient.instance = self

        async def close(self) -> None:
            self.closed = True

    class FakeAssistantAgent:
        def __init__(self, name: str, **kwargs: Any) -> None:
            if name == "analyst":
                raise RuntimeError("construction exploded")

    def fake_import(name: str) -> Any:
        modules = {
            "autogen_agentchat.agents": SimpleNamespace(AssistantAgent=FakeAssistantAgent),
            "autogen_agentchat.teams": SimpleNamespace(RoundRobinGroupChat=object),
            "autogen_agentchat.conditions": SimpleNamespace(MaxMessageTermination=object),
            "autogen_ext.models.openai": SimpleNamespace(OpenAIChatCompletionClient=FakeModelClient),
            "autogen_core.tools": SimpleNamespace(ToolResult=object, TextResultContent=object),
        }
        return modules[name]

    with pytest.raises(RuntimeError, match="construction exploded"):
        await AutoGenRunner(import_module=fake_import).run(
            {"id": "case_001"},
            "用户问题：四川是多少？",
            _context(),
        )

    assert FakeModelClient.instance.closed is True


@pytest.mark.asyncio
async def test_autogen_runner_close_does_not_mask_run_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAdapter:
        def __init__(self, workspace: str) -> None:
            self.workspace = workspace

        def openai_tool_schemas(self) -> list[dict[str, Any]]:
            return []

    fake_tools_module = ModuleType("frameworks.tableclaw_tools")
    fake_tools_module.TableClawToolAdapter = FakeAdapter
    monkeypatch.setitem(sys.modules, "frameworks.tableclaw_tools", fake_tools_module)

    class FakeModelClient:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        async def close(self) -> None:
            raise RuntimeError("close exploded")

    class FakeAssistantAgent:
        def __init__(self, name: str, **kwargs: Any) -> None:
            self.name = name

    class FakeRoundRobinGroupChat:
        def __init__(self, participants: list[Any], *, termination_condition: Any) -> None:
            self.participants = participants

        async def run(self, *, task: str) -> Any:
            raise RuntimeError("run exploded")

    class FakeMaxMessageTermination:
        def __init__(self, *, max_messages: int) -> None:
            self.max_messages = max_messages

    def fake_import(name: str) -> Any:
        modules = {
            "autogen_agentchat.agents": SimpleNamespace(AssistantAgent=FakeAssistantAgent),
            "autogen_agentchat.teams": SimpleNamespace(RoundRobinGroupChat=FakeRoundRobinGroupChat),
            "autogen_agentchat.conditions": SimpleNamespace(MaxMessageTermination=FakeMaxMessageTermination),
            "autogen_ext.models.openai": SimpleNamespace(OpenAIChatCompletionClient=FakeModelClient),
            "autogen_core.tools": SimpleNamespace(ToolResult=object, TextResultContent=object),
        }
        return modules[name]

    with pytest.raises(RuntimeError, match="run exploded"):
        await AutoGenRunner(import_module=fake_import).run(
            {"id": "case_001"},
            "用户问题：四川是多少？",
            _context(),
        )
