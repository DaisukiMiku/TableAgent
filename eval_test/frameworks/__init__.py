"""Framework runners for TableClaw evaluation."""

from __future__ import annotations

from .base import FrameworkRunContext, FrameworkRunResult, FrameworkRunner
from .nanobot_runner import NanobotRunner

SUPPORTED_FRAMEWORKS = (
    "nanobot-current",
    "nanobot-skill-off",
    "openai-agents-sdk",
    "langgraph",
    "autogen",
)


def framework_mode(framework: str, cli_mode: str) -> str:
    if framework == "nanobot-skill-off":
        return "skill-off"
    if framework == "nanobot-current":
        return "skill-on"
    return cli_mode


def create_framework_runner(framework: str) -> FrameworkRunner:
    if framework in {"nanobot-current", "nanobot-skill-off"}:
        return NanobotRunner()
    if framework == "openai-agents-sdk":
        from .openai_agents_runner import OpenAIAgentsRunner

        return OpenAIAgentsRunner()
    if framework == "langgraph":
        from .langgraph_runner import LangGraphRunner

        return LangGraphRunner()
    if framework == "autogen":
        from .autogen_runner import AutoGenRunner

        return AutoGenRunner()
    raise ValueError(f"Unsupported framework: {framework}")

__all__ = [
    "FrameworkRunContext",
    "FrameworkRunResult",
    "FrameworkRunner",
    "SUPPORTED_FRAMEWORKS",
    "create_framework_runner",
    "framework_mode",
]
