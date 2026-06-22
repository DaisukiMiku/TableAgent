from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from frameworks.base import FrameworkRunContext
from frameworks.nanobot_runner import NanobotRunner


class FakeLoop:
    _last_usage = {"total_tokens": 17, "prompt_tokens": 11, "completion_tokens": 6}

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
    def __init__(self) -> None:
        self._loop = FakeLoop()
        self.session_key = ""

    async def run(self, prompt: str, session_key: str) -> FakeResult:
        assert "用户问题" in prompt
        self.session_key = session_key
        return FakeResult()


@pytest.mark.asyncio
async def test_nanobot_runner_returns_standard_result(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_bot = FakeBot()

    class FakeNanobot:
        @staticmethod
        def from_config(config_path: Path) -> FakeBot:
            assert str(config_path).endswith("tableclaw-bailian-dashscope-eval.json")
            return fake_bot

    monkeypatch.setattr("frameworks.nanobot_runner.Nanobot", FakeNanobot)

    runner = NanobotRunner()
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
