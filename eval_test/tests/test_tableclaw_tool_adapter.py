from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

NANOBOT_SRC = Path(__file__).resolve().parents[2] / "nanobot"
if str(NANOBOT_SRC) not in sys.path:
    sys.path.insert(0, str(NANOBOT_SRC))

from nanobot.agent.tools.base import Tool, tool_parameters

from frameworks.tableclaw_tools import TableClawToolAdapter


@tool_parameters(
    {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "default": 8},
        },
        "required": ["query"],
    }
)
class FakeRetrieveTool(Tool):
    @property
    def name(self) -> str:
        return "tableclaw_retrieve_tables"

    @property
    def description(self) -> str:
        return "Fake retrieve tool."

    @property
    def read_only(self) -> bool:
        return True

    async def execute(self, **kwargs: Any) -> str:
        return f"query={kwargs['query']};top_k={kwargs.get('top_k')}"


class FakeCastBugTool(FakeRetrieveTool):
    @property
    def name(self) -> str:
        return "tableclaw_cast_bug"

    def cast_params(self, params: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("cast exploded")


class FakeExecuteBugTool(FakeRetrieveTool):
    @property
    def name(self) -> str:
        return "tableclaw_execute_bug"

    async def execute(self, **kwargs: Any) -> str:
        raise RuntimeError("execute exploded")


@pytest.mark.asyncio
async def test_tool_adapter_calls_tool_and_records_timeline() -> None:
    adapter = TableClawToolAdapter(
        workspace="/tmp/workspace",
        tool_classes=[FakeRetrieveTool],
    )

    output, event = await adapter.call(
        "tableclaw_retrieve_tables",
        {"query": "四川", "top_k": "3"},
    )

    assert output == "query=四川;top_k=3"
    assert event["tool"] == "tableclaw_retrieve_tables"
    assert event["args"] == {"query": "四川", "top_k": 3}
    assert event["ok"] is True


def test_default_tool_adapter_includes_tracked_tableclaw_tools() -> None:
    adapter = TableClawToolAdapter(workspace="/tmp/workspace")

    assert {
        "tableclaw_catalog_tables",
        "tableclaw_domain_knowledge",
        "tableclaw_retrieve_tables",
        "tableclaw_inspect",
        "tableclaw_locate_column",
        "tableclaw_extract_series",
        "tableclaw_extract_matrix",
        "tableclaw_time_series",
        "tableclaw_topk",
        "tableclaw_rank",
        "tableclaw_filter",
    }.issubset(set(adapter.tool_names))


@pytest.mark.asyncio
async def test_tool_adapter_returns_validation_error_as_model_visible_text() -> None:
    adapter = TableClawToolAdapter(
        workspace="/tmp/workspace",
        tool_classes=[FakeRetrieveTool],
    )

    output, event = await adapter.call("tableclaw_retrieve_tables", {"top_k": "bad"})

    assert output.startswith("Error: Invalid parameters")
    assert event["ok"] is False
    assert "missing required query" in event["error"]


@pytest.mark.asyncio
async def test_tool_adapter_lets_cast_bugs_escape() -> None:
    adapter = TableClawToolAdapter(
        workspace="/tmp/workspace",
        tool_classes=[FakeCastBugTool],
    )

    with pytest.raises(RuntimeError, match="cast exploded"):
        await adapter.call("tableclaw_cast_bug", {"query": "四川"})


@pytest.mark.asyncio
async def test_tool_adapter_returns_execute_error_as_model_visible_text() -> None:
    adapter = TableClawToolAdapter(
        workspace="/tmp/workspace",
        tool_classes=[FakeExecuteBugTool],
    )

    output, event = await adapter.call("tableclaw_execute_bug", {"query": "四川"})

    assert output.startswith("Error executing tableclaw_execute_bug")
    assert event["ok"] is False
    assert "execute exploded" in event["error"]


def test_tool_adapter_exports_openai_schemas() -> None:
    adapter = TableClawToolAdapter(
        workspace="/tmp/workspace",
        tool_classes=[FakeRetrieveTool],
    )

    schemas = adapter.openai_tool_schemas()

    assert schemas[0]["function"]["name"] == "tableclaw_retrieve_tables"
    assert schemas[0]["function"]["parameters"]["required"] == ["query"]
