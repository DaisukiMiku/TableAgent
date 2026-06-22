from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

import pytest

from frameworks.base import FrameworkRunContext
from frameworks.openai_agents_runner import OpenAIAgentsRunner


def test_openai_agents_runner_name() -> None:
    assert OpenAIAgentsRunner().name == "openai-agents-sdk"


def test_openai_agents_runner_missing_dependency_message() -> None:
    def fake_import(name: str):
        raise ModuleNotFoundError("agents", name="agents")

    runner = OpenAIAgentsRunner(import_module=fake_import)

    with pytest.raises(RuntimeError, match="Install optional framework dependencies"):
        runner._load_agents_sdk()


def test_openai_agents_runner_preserves_sdk_internal_import_errors() -> None:
    def fake_import(name: str):
        raise ModuleNotFoundError("missing_subdep", name="missing_subdep")

    runner = OpenAIAgentsRunner(import_module=fake_import)

    with pytest.raises(ModuleNotFoundError) as exc_info:
        runner._load_agents_sdk()

    assert exc_info.value.name == "missing_subdep"


@pytest.mark.asyncio
async def test_openai_agents_runner_disables_sdk_tracing(
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

    class FakeAgents:
        tracing_disabled = False

        @staticmethod
        def set_tracing_disabled(disabled: bool) -> None:
            FakeAgents.tracing_disabled = disabled

        class OpenAIChatCompletionsModel:
            def __init__(self, **kwargs: Any) -> None:
                self.kwargs = kwargs

        class Agent:
            def __init__(self, **kwargs: Any) -> None:
                self.kwargs = kwargs

        class Runner:
            @staticmethod
            async def run(agent: Any, prompt: str) -> Any:
                assert FakeAgents.tracing_disabled is True
                return type("FakeResult", (), {"final_output": "最终答案"})()

    def fake_import(name: str) -> Any:
        assert name == "agents"
        return FakeAgents

    runner = OpenAIAgentsRunner(import_module=fake_import)
    ctx = FrameworkRunContext(
        framework="openai-agents-sdk",
        mode="skill-off",
        run_id="unit-run",
        config_path=None,
        workspace="/tmp/workspace",
        model="deepseek-v4-pro",
        base_url="https://example.invalid/v1",
        api_key="test-key",
    )

    result = await runner.run({"id": "case_001"}, "用户问题：四川是多少？", ctx)

    assert result["answer"] == "最终答案"
