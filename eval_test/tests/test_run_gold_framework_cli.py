from __future__ import annotations

from pathlib import Path

from frameworks import create_framework_runner, framework_mode
from frameworks.nanobot_runner import NanobotRunner
from run_gold_parallel_eval import build_framework_context


def test_create_nanobot_current_runner() -> None:
    runner = create_framework_runner("nanobot-current")
    assert isinstance(runner, NanobotRunner)
    assert framework_mode("nanobot-current", "skill-off") == "skill-on"


def test_create_nanobot_skill_off_runner() -> None:
    runner = create_framework_runner("nanobot-skill-off")
    assert isinstance(runner, NanobotRunner)
    assert framework_mode("nanobot-skill-off", "skill-on") == "skill-off"


def test_build_framework_context_uses_framework_mode() -> None:
    ctx = build_framework_context(
        framework="nanobot-skill-off",
        mode="skill-on",
        run_id="unit-run",
        config_path=Path("nanobot/configs/tableclaw-bailian-dashscope-eval.json"),
        workspace="workspace",
        model="deepseek-v4-pro",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="test-key",
    )

    assert ctx.framework == "nanobot-skill-off"
    assert ctx.mode == "skill-off"
    assert ctx.model == "deepseek-v4-pro"
