from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, TypedDict


class FrameworkRunResult(TypedDict):
    answer: str
    usage: dict[str, Any]
    elapsed_ms: int
    tools_used: list[str]
    tool_timeline: list[dict[str, Any]]
    retrieval_tool_called: bool
    inspect_tool_called: bool
    tableclaw_tools_used: list[str]
    skill_selected: bool
    selected_skills: list[str]
    framework_trace: dict[str, Any]


@dataclass(frozen=True)
class FrameworkRunContext:
    framework: str
    mode: str
    run_id: str
    config_path: Path | None
    workspace: str
    model: str
    base_url: str
    api_key: str
    extra: dict[str, Any] = field(default_factory=dict)


class FrameworkRunner(Protocol):
    name: str

    async def run(
        self,
        task: dict[str, Any],
        prompt: str,
        context: FrameworkRunContext,
    ) -> FrameworkRunResult:
        ...


REQUIRED_FRAMEWORK_RESULT_KEYS = (
    "answer",
    "usage",
    "elapsed_ms",
    "tools_used",
    "tool_timeline",
    "retrieval_tool_called",
    "inspect_tool_called",
    "tableclaw_tools_used",
    "skill_selected",
    "selected_skills",
    "framework_trace",
)


def ensure_framework_result(result: dict[str, Any]) -> FrameworkRunResult:
    missing = [key for key in REQUIRED_FRAMEWORK_RESULT_KEYS if key not in result]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Framework result missing required keys: {joined}")
    return result  # type: ignore[return-value]
