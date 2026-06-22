from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from frameworks.base import FrameworkRunContext
from frameworks.nanobot_runner import NanobotRunner


class FakeLoop:
    _last_usage = {"total_tokens": 17, "prompt_tokens": 11, "completion_tokens": 6}

    def __init__(self) -> None:
        self.closed = False

    async def close_mcp(self) -> None:
        self.closed = True


class FakeResult:
    content = "最终答案：四川 1.23"
    tools_used = ["tableclaw_retrieve_tables", "read_file"]
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "function": {
                        "name": "tableclaw_retrieve_tables",
                        "arguments": '{"query":"四川"}',
                    }
                },
                {
                    "function": {
                        "name": "read_file",
                        "arguments": '{"path":"workspace/skills/table-read/SKILL.md"}',
                    }
                },
            ],
        }
    ]


class FakeBot:
    def __init__(self, *, raises: bool = False) -> None:
        self._loop = FakeLoop()
        self.raises = raises
        self.session_key = ""

    async def run(self, prompt: str, session_key: str) -> FakeResult:
        assert "用户问题" in prompt
        self.session_key = session_key
        if self.raises:
            raise RuntimeError("boom")
        return FakeResult()


def fake_extract_tool_timeline(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    for step, tool_call in enumerate(messages[0]["tool_calls"], start=1):
        function = tool_call["function"]
        args = function["arguments"]
        skill_read = "table-read" if "workspace/skills/table-read/SKILL.md" in args else None
        timeline.append(
            {
                "step": step,
                "tool": function["name"],
                "skill_read": skill_read,
                "is_tracked_skill_read": skill_read is not None,
            }
        )
    return timeline


FAKE_EVAL_HELPERS = (("tableclaw_retrieve_tables", "tableclaw_inspect"), fake_extract_tool_timeline)


@pytest.mark.asyncio
async def test_nanobot_runner_returns_standard_result() -> None:
    fake_bot = FakeBot()

    def fake_factory(config_path: Path) -> FakeBot:
        assert str(config_path).endswith("tableclaw-bailian-dashscope-eval.json")
        return fake_bot

    runner = NanobotRunner(nanobot_factory=fake_factory, eval_helpers=FAKE_EVAL_HELPERS)
    ctx = FrameworkRunContext(
        framework="nanobot-current",
        mode="skill-on",
        run_id="unit-run",
        config_path=Path("nanobot/configs/tableclaw-bailian-dashscope-eval.json"),
        workspace="workspace",
        model="deepseek-v4-pro",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="test-key",
    )

    result = await runner.run(
        {"id": "case_001", "question": "四川是多少？"},
        "用户问题：四川是多少？",
        ctx,
    )

    assert result["answer"] == "最终答案：四川 1.23"
    assert result["usage"]["total_tokens"] == 17
    assert result["retrieval_tool_called"] is True
    assert result["inspect_tool_called"] is False
    assert result["tableclaw_tools_used"] == ["tableclaw_retrieve_tables"]
    assert result["selected_skills"] == ["table-read"]
    assert result["framework_trace"]["framework"] == "nanobot-current"
    assert "sdk:gold-parallel-unit-run-case_001-skill-on" in fake_bot.session_key
    assert fake_bot._loop.closed is True


@pytest.mark.asyncio
async def test_nanobot_runner_closes_mcp_when_run_raises() -> None:
    fake_bot = FakeBot(raises=True)
    runner = NanobotRunner(
        nanobot_factory=lambda _config_path: fake_bot,
        eval_helpers=FAKE_EVAL_HELPERS,
    )
    ctx = FrameworkRunContext(
        framework="nanobot-current",
        mode="skill-on",
        run_id="unit-run",
        config_path=Path("nanobot/configs/tableclaw-bailian-dashscope-eval.json"),
        workspace="workspace",
        model="deepseek-v4-pro",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="test-key",
    )

    with pytest.raises(RuntimeError, match="boom"):
        await runner.run(
            {"id": "case_001", "question": "四川是多少？"},
            "用户问题：四川是多少？",
            ctx,
        )

    assert fake_bot._loop.closed is True


def test_nanobot_runner_imports_from_repo_root() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from frameworks import FrameworkRunContext; "
                "import frameworks.nanobot_runner; "
                "import eval_test.frameworks.nanobot_runner"
            ),
        ],
        check=False,
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
