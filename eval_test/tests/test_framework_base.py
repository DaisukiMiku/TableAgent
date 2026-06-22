from __future__ import annotations

import pytest

from frameworks.base import (
    FrameworkRunContext,
    FrameworkRunResult,
    ensure_framework_result,
)


def test_framework_run_context_defaults() -> None:
    ctx = FrameworkRunContext(
        framework="nanobot-current",
        mode="skill-on",
        run_id="unit-run",
        config_path=None,
        workspace="/tmp/tableclaw-workspace",
        model="deepseek-v4-pro",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="test-key",
    )

    assert ctx.framework == "nanobot-current"
    assert ctx.mode == "skill-on"
    assert ctx.model == "deepseek-v4-pro"
    assert ctx.extra == {}


def test_ensure_framework_result_accepts_complete_result() -> None:
    result: FrameworkRunResult = {
        "answer": "完成",
        "usage": {},
        "elapsed_ms": 12,
        "tools_used": ["tableclaw_retrieve_tables"],
        "tool_timeline": [{"tool": "tableclaw_retrieve_tables"}],
        "retrieval_tool_called": True,
        "inspect_tool_called": False,
        "tableclaw_tools_used": ["tableclaw_retrieve_tables"],
        "skill_selected": False,
        "selected_skills": [],
        "framework_trace": {"framework": "fake"},
    }

    assert ensure_framework_result(result) == result


def test_ensure_framework_result_rejects_missing_required_key() -> None:
    with pytest.raises(ValueError, match="Framework result missing required keys"):
        ensure_framework_result({"answer": "不完整"})
