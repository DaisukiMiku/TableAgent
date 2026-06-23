from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import run_gold_parallel_eval as gold_eval
from run_gold_parallel_eval import write_framework_trace
from frameworks import create_framework_runner, framework_mode
from frameworks.nanobot_runner import NanobotRunner
from frameworks.tablepipeline2_runner import TablePipelineV2Runner


class FakeRunner:
    name = "fake"

    def __init__(self) -> None:
        self.context: Any | None = None

    async def run(
        self,
        task: dict[str, Any],
        prompt: str,
        context: Any,
    ) -> dict[str, Any]:
        self.context = context
        return {
            "answer": "fake answer",
            "usage": {},
            "elapsed_ms": 1,
            "tools_used": [],
            "tool_timeline": [],
            "retrieval_tool_called": False,
            "inspect_tool_called": False,
            "tableclaw_tools_used": [],
            "skill_selected": False,
            "selected_skills": [],
            "framework_trace": {"framework": context.framework},
        }


def test_create_nanobot_current_runner() -> None:
    runner = create_framework_runner("nanobot-current")
    assert isinstance(runner, NanobotRunner)
    assert framework_mode("nanobot-current", "skill-off") == "skill-on"


def test_create_nanobot_skill_off_runner() -> None:
    runner = create_framework_runner("nanobot-skill-off")
    assert isinstance(runner, NanobotRunner)
    assert framework_mode("nanobot-skill-off", "skill-on") == "skill-off"


def test_create_tablepipeline_v2_runner() -> None:
    runner = create_framework_runner("tablepipeline-v2")
    assert isinstance(runner, TablePipelineV2Runner)
    assert framework_mode("tablepipeline-v2", "skill-on") == "skill-on"


def test_build_framework_context_uses_framework_mode() -> None:
    ctx = gold_eval.build_framework_context(
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
    assert ctx.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert ctx.api_key == "test-key"


def test_build_framework_context_accepts_extra() -> None:
    ctx = gold_eval.build_framework_context(
        framework="tablepipeline-v2",
        mode="skill-on",
        run_id="unit-run",
        config_path=None,
        workspace="workspace",
        model="deepseek-v4-pro",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="test-key",
        extra={"tablepipeline2_data_dir": "/tmp/tablepipeline-data"},
    )

    assert ctx.extra == {"tablepipeline2_data_dir": "/tmp/tablepipeline-data"}


def test_cli_config_path_defaults_to_effective_mode_fallback() -> None:
    parser = gold_eval.build_arg_parser()

    default_args = parser.parse_args(["--judge-api-key", "judge-key", "--answer-api-key", "answer-key"])
    explicit_args = parser.parse_args(
        [
            "--judge-api-key",
            "judge-key",
            "--answer-api-key",
            "answer-key",
            "--config-path",
            "custom-config.json",
        ]
    )

    assert default_args.config_path is None
    assert explicit_args.config_path == Path("custom-config.json")


@pytest.mark.asyncio
async def test_run_answer_uses_effective_mode_config_when_config_path_missing() -> None:
    runner = FakeRunner()

    await gold_eval.run_answer(
        {"id": "case_001", "question": "四川是多少？"},
        "skill-on",
        run_id="unit-run",
        config_path=None,
        runner=runner,
        framework="nanobot-skill-off",
        answer_model="deepseek-v4-pro",
        answer_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        answer_api_key="test-key",
        framework_extra={"tablepipeline2_data_dir": "/tmp/tablepipeline-data"},
    )

    assert runner.context is not None
    assert runner.context.mode == "skill-off"
    assert runner.context.config_path == gold_eval.CONFIGS["skill-off"]
    assert runner.context.extra["tablepipeline2_data_dir"] == "/tmp/tablepipeline-data"


def test_write_framework_trace(tmp_path) -> None:
    item = {
        "task_id": "case_001",
        "framework": "nanobot-current",
        "framework_trace": {"steps": [{"name": "solve"}]},
    }

    path = write_framework_trace(tmp_path, "unit-run", item)

    assert path.name == "case_001.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["task_id"] == "case_001"
    assert data["framework_trace"]["steps"] == [{"name": "solve"}]
