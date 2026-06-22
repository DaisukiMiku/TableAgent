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


def test_tool_adapter_exports_openai_schemas() -> None:
    adapter = TableClawToolAdapter(
        workspace="/tmp/workspace",
        tool_classes=[FakeRetrieveTool],
    )

    schemas = adapter.openai_tool_schemas()

    assert schemas[0]["function"]["name"] == "tableclaw_retrieve_tables"
    assert schemas[0]["function"]["parameters"]["required"] == ["query"]
