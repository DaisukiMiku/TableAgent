from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool
from nanobot.agent.tools.context import ToolContext
from nanobot.agent.tools.tableclaw import (
    TableClawCatalogTablesTool,
    TableClawDomainKnowledgeTool,
    TableClawExtractMatrixTool,
    TableClawExtractSeriesTool,
    TableClawFilterTool,
    TableClawInspectTool,
    TableClawLocateColumnTool,
    TableClawRankTool,
    TableClawRetrieveTablesTool,
    TableClawTimeSeriesTool,
    TableClawTopKTool,
)


DEFAULT_TABLECLAW_TOOL_CLASSES: list[type[Tool]] = [
    TableClawCatalogTablesTool,
    TableClawDomainKnowledgeTool,
    TableClawRetrieveTablesTool,
    TableClawInspectTool,
    TableClawLocateColumnTool,
    TableClawExtractSeriesTool,
    TableClawExtractMatrixTool,
    TableClawTimeSeriesTool,
    TableClawTopKTool,
    TableClawRankTool,
    TableClawFilterTool,
]


class TableClawToolAdapter:
    def __init__(
        self,
        workspace: str,
        tool_classes: list[type[Tool]] | None = None,
    ) -> None:
        self.workspace = str(Path(workspace).expanduser().resolve())
        ctx = ToolContext(config=None, workspace=self.workspace, timezone="Asia/Shanghai")
        self._tools = {
            tool.name: tool
            for tool in (tool_cls.create(ctx) for tool_cls in (tool_classes or DEFAULT_TABLECLAW_TOOL_CLASSES))
        }

    @property
    def tool_names(self) -> list[str]:
        return sorted(self._tools)

    def openai_tool_schemas(self) -> list[dict[str, Any]]:
        return [self._tools[name].to_schema() for name in self.tool_names]

    async def call(self, name: str, arguments: dict[str, Any] | str | None) -> tuple[str, dict[str, Any]]:
        params: Any = {} if arguments is None else arguments
        if isinstance(arguments, str):
            try:
                params = json.loads(arguments)
            except json.JSONDecodeError:
                params = arguments

        if name not in self._tools:
            error = f"Tool {name!r} not found. Available tools: {', '.join(self.tool_names)}"
            return f"Error: {error}", {"tool": name, "args": params, "ok": False, "error": error}

        if not isinstance(params, dict):
            error = f"parameters must be an object, got {type(params).__name__}"
            return f"Error: {error}", {"tool": name, "args": params, "ok": False, "error": error}

        tool = self._tools[name]
        cast_params = tool.cast_params(params)
        errors = tool.validate_params(cast_params)
        if errors:
            error = f"Invalid parameters for tool {name!r}: {'; '.join(errors)}"
            return f"Error: {error}", {"tool": name, "args": cast_params, "ok": False, "error": error}

        try:
            result = await tool.execute(**cast_params)
        except Exception as exc:
            error = f"Error executing {name}: {exc!r}"
            return error, {"tool": name, "args": cast_params, "ok": False, "error": error}

        output = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        return output, {
            "tool": name,
            "args": cast_params,
            "ok": True,
            "output_preview": output[:500],
        }
