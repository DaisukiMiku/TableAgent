# TableClaw Framework Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在实验 worktree 中实现一个可复用的 framework comparison runner，让 `nanobot-current`、`nanobot-skill-off`、OpenAI Agents SDK、LangGraph、AutoGen 可以在同一批 TableClaw 任务上用 `deepseek-v4-pro` 做可比评测。

**Architecture:** 保留现有 `eval_test/run_gold_parallel_eval.py` 的 dataset、prompt、judge、summary 逻辑，只把回答生成路径抽象为 `FrameworkRunner`。TableClaw tools 通过一个统一 adapter 暴露给非 Nanobot runner，所有 runner 返回同一种 `FrameworkRunResult`，让后续报告继续复用现有字段并增加 framework trace。

**Tech Stack:** Python 3.13, pytest, existing Nanobot SDK, OpenAI-compatible DashScope endpoint, OpenAI Agents SDK, LangGraph, AutoGen, existing TableClaw tool classes.

---

## 文件结构

本计划新增和修改这些文件：

- Create: `eval_test/frameworks/__init__.py`
  - Framework runner registry，负责按 `--framework` 创建 runner。
- Create: `eval_test/frameworks/base.py`
  - `FrameworkRunContext`、`FrameworkRunResult`、`FrameworkRunner`、结果 shape 校验。
- Create: `eval_test/frameworks/nanobot_runner.py`
  - 当前 Nanobot 调用路径的独立 runner，实现 baseline。
- Create: `eval_test/frameworks/tableclaw_tools.py`
  - TableClaw tool adapter，统一 schema、参数校验、执行和 timeline 记录。
- Create: `eval_test/frameworks/openai_agents_runner.py`
  - OpenAI Agents SDK single-agent runner。
- Create: `eval_test/frameworks/langgraph_runner.py`
  - LangGraph explicit-state runner。
- Create: `eval_test/frameworks/autogen_runner.py`
  - AutoGen minimal Planner / Analyst / Verifier runner。
- Create: `eval_test/frameworks/requirements-frameworks.txt`
  - 非 Nanobot framework 的可选依赖清单。
- Create: `eval_test/tests/conftest.py`
  - pytest import path setup，让测试可同时导入 `run_gold_parallel_eval.py` 和 `frameworks` package。
- Create: `eval_test/tests/test_framework_base.py`
  - runner result shape 单元测试。
- Create: `eval_test/tests/test_nanobot_runner.py`
  - Nanobot runner 单元测试，使用 fake Nanobot，不调用模型。
- Create: `eval_test/tests/test_tableclaw_tool_adapter.py`
  - tool adapter 单元测试，使用 fake tool，不读取真实表。
- Create: `eval_test/tests/test_run_gold_framework_cli.py`
  - CLI/worker helper 单元测试，使用 fake runner，不调用模型。
- Modify: `eval_test/run_gold_parallel_eval.py`
  - 增加 `--framework`、runner 注入、framework trace 写入、runtime error 字段补齐。
- Modify: `eval_gold_parallel.sh`
  - 去掉 hardcoded API key fallback，保留环境变量要求。
- Modify: `start.sh`
  - 去掉 hardcoded API key fallback，保留环境变量要求。
- Modify: `eval.sh`
  - 去掉 hardcoded API key fallback，保留环境变量要求。
- Modify: `docs/superpowers/specs/2026-06-22-framework-comparison-design.md`
  - 增加中文简短说明，说明后续 spec 默认中文。

实现顺序必须保持：先测试和抽象现有 Nanobot runner，再接 adapter，再接第三方 framework。

---

### Task 1: Runner Base Contract

**Files:**
- Create: `eval_test/frameworks/__init__.py`
- Create: `eval_test/frameworks/base.py`
- Create: `eval_test/tests/conftest.py`
- Create: `eval_test/tests/test_framework_base.py`

- [ ] **Step 1: 写测试 import path setup 和失败测试**

创建 `eval_test/tests/conftest.py`：

```python
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL_TEST = ROOT / "eval_test"
for path in (str(ROOT), str(EVAL_TEST)):
    if path not in sys.path:
        sys.path.insert(0, path)
```

创建 `eval_test/tests/test_framework_base.py`：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
nanobot/.venv/bin/python -m pytest eval_test/tests/test_framework_base.py -q
```

Expected: FAIL，错误包含 `ModuleNotFoundError: No module named 'frameworks'`。

- [ ] **Step 3: 写最小实现**

创建 `eval_test/frameworks/__init__.py`：

```python
"""Framework runners for TableClaw evaluation."""

from __future__ import annotations

from .base import FrameworkRunContext, FrameworkRunResult, FrameworkRunner

__all__ = [
    "FrameworkRunContext",
    "FrameworkRunResult",
    "FrameworkRunner",
]
```

创建 `eval_test/frameworks/base.py`：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
nanobot/.venv/bin/python -m pytest eval_test/tests/test_framework_base.py -q
```

Expected: PASS，输出包含 `3 passed`。

- [ ] **Step 5: 提交**

```bash
git add eval_test/frameworks/__init__.py eval_test/frameworks/base.py eval_test/tests/conftest.py eval_test/tests/test_framework_base.py
git commit -m "Add framework runner contract"
```

---

### Task 2: Nanobot Runner Extraction

**Files:**
- Create: `eval_test/frameworks/nanobot_runner.py`
- Create: `eval_test/tests/test_nanobot_runner.py`

- [ ] **Step 1: 写失败测试**

创建 `eval_test/tests/test_nanobot_runner.py`：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
nanobot/.venv/bin/python -m pytest eval_test/tests/test_nanobot_runner.py -q
```

Expected: FAIL，错误包含 `ModuleNotFoundError: No module named 'frameworks.nanobot_runner'`。

- [ ] **Step 3: 写 Nanobot runner**

创建 `eval_test/frameworks/nanobot_runner.py`：

```python
from __future__ import annotations

import time
import uuid
from typing import Any

from nanobot.nanobot import Nanobot

from run_eval import TRACKED_TABLECLAW_TOOLS, extract_tool_timeline

from .base import FrameworkRunContext, FrameworkRunResult, ensure_framework_result


class NanobotRunner:
    name = "nanobot"

    async def run(
        self,
        task: dict[str, Any],
        prompt: str,
        context: FrameworkRunContext,
    ) -> FrameworkRunResult:
        if context.config_path is None:
            raise ValueError("NanobotRunner requires config_path")

        bot = Nanobot.from_config(context.config_path)
        started = time.time()
        result = await bot.run(
            prompt,
            session_key=(
                f"sdk:gold-parallel-{context.run_id}-{task['id']}-{context.mode}-"
                f"{int(started)}-{uuid.uuid4().hex[:8]}"
            ),
        )
        elapsed_ms = int((time.time() - started) * 1000)
        usage = dict(getattr(bot._loop, "_last_usage", {}) or {})
        await bot._loop.close_mcp()

        timeline = extract_tool_timeline(result.messages)
        tableclaw_tools = [
            event for event in timeline if event.get("tool") in TRACKED_TABLECLAW_TOOLS
        ]
        skill_events = [event for event in timeline if event.get("is_tracked_skill_read")]
        payload: dict[str, Any] = {
            "answer": result.content,
            "usage": usage,
            "elapsed_ms": elapsed_ms,
            "tools_used": result.tools_used,
            "tool_timeline": timeline,
            "retrieval_tool_called": any(
                event.get("tool") == "tableclaw_retrieve_tables" for event in tableclaw_tools
            ),
            "inspect_tool_called": any(
                event.get("tool") == "tableclaw_inspect" for event in tableclaw_tools
            ),
            "tableclaw_tools_used": list(
                dict.fromkeys(event.get("tool") for event in tableclaw_tools if event.get("tool"))
            ),
            "skill_selected": bool(skill_events),
            "selected_skills": list(
                dict.fromkeys(event.get("skill_read") for event in skill_events if event.get("skill_read"))
            ),
            "framework_trace": {
                "framework": context.framework,
                "runner": self.name,
                "message_count": len(result.messages),
            },
        }
        return ensure_framework_result(payload)
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
nanobot/.venv/bin/python -m pytest eval_test/tests/test_nanobot_runner.py eval_test/tests/test_framework_base.py -q
```

Expected: PASS，输出包含 `4 passed`。

- [ ] **Step 5: 提交**

```bash
git add eval_test/frameworks/nanobot_runner.py eval_test/tests/test_nanobot_runner.py
git commit -m "Extract nanobot framework runner"
```

---

### Task 3: Evaluator Framework Registry And CLI

**Files:**
- Modify: `eval_test/frameworks/__init__.py`
- Modify: `eval_test/run_gold_parallel_eval.py`
- Create: `eval_test/tests/test_run_gold_framework_cli.py`

- [ ] **Step 1: 写 registry 测试**

创建 `eval_test/tests/test_run_gold_framework_cli.py`：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
nanobot/.venv/bin/python -m pytest eval_test/tests/test_run_gold_framework_cli.py -q
```

Expected: FAIL，错误包含 `cannot import name 'create_framework_runner'` 或 `cannot import name 'build_framework_context'`。

- [ ] **Step 3: 实现 registry**

修改 `eval_test/frameworks/__init__.py` 为：

```python
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
```

- [ ] **Step 4: 修改 evaluator context helper**

在 `eval_test/run_gold_parallel_eval.py` 中增加 imports：

```python
from frameworks import (
    SUPPORTED_FRAMEWORKS,
    FrameworkRunContext,
    FrameworkRunner,
    create_framework_runner,
    framework_mode,
)
```

在 `DEFAULT_BASE_URL` 后增加：

```python
DEFAULT_ANSWER_MODEL = "deepseek-v4-pro"
```

在 `judge_answer()` 前增加：

```python
def build_framework_context(
    *,
    framework: str,
    mode: str,
    run_id: str,
    config_path: Path | None,
    workspace: str,
    model: str,
    base_url: str,
    api_key: str,
) -> FrameworkRunContext:
    return FrameworkRunContext(
        framework=framework,
        mode=framework_mode(framework, mode),
        run_id=run_id,
        config_path=config_path,
        workspace=workspace,
        model=model,
        base_url=base_url,
        api_key=api_key,
    )
```

保留旧 `run_answer()` 函数名，但改成 runner 注入：

```python
async def run_answer(
    task: dict[str, Any],
    mode: str,
    *,
    run_id: str,
    config_path: Path | None = None,
    runner: FrameworkRunner | None = None,
    framework: str = "nanobot-current",
    answer_model: str = DEFAULT_ANSWER_MODEL,
    answer_base_url: str = DEFAULT_BASE_URL,
    answer_api_key: str,
) -> dict[str, Any]:
    active_runner = runner or create_framework_runner(framework)
    prompt = render_prompt(task, mode)
    context = build_framework_context(
        framework=framework,
        mode=mode,
        run_id=run_id,
        config_path=config_path,
        workspace=str(ROOT / "workspace"),
        model=answer_model,
        base_url=answer_base_url,
        api_key=answer_api_key,
    )
    return await active_runner.run(task, prompt, context)
```

在 `evaluate_one()` 参数中增加：

```python
    runner: FrameworkRunner,
    framework: str,
    answer_model: str,
    answer_base_url: str,
    answer_api_key: str,
```

把 `answer_result = await run_answer(...)` 改为：

```python
answer_result = await run_answer(
    task,
    mode,
    run_id=run_id,
    config_path=config_path,
    runner=runner,
    framework=framework,
    answer_model=answer_model,
    answer_base_url=answer_base_url,
    answer_api_key=answer_api_key,
)
```

在返回 item 中增加：

```python
        "framework": framework,
        "framework_trace": answer_result.get("framework_trace", {}),
```

在 runtime error item 中增加：

```python
                    "framework": args.framework,
                    "framework_trace": {
                        "framework": args.framework,
                        "error": repr(exc),
                    },
```

在 argparse 增加：

```python
    parser.add_argument("--framework", choices=SUPPORTED_FRAMEWORKS, default="nanobot-current")
    parser.add_argument("--answer-model", default=DEFAULT_ANSWER_MODEL)
    parser.add_argument("--answer-base-url", default=os.environ.get("DASHSCOPE_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--answer-api-key", default=os.environ.get("DASHSCOPE_API_KEY"))
```

在 `if not args.judge_api_key` 后增加：

```python
    if not args.answer_api_key:
        raise SystemExit("DASHSCOPE_API_KEY is required for answer model calls.")
```

在 worker 外创建 runner：

```python
    runner = create_framework_runner(args.framework)
```

在 `evaluate_one(...)` 调用中传入：

```python
                    runner=runner,
                    framework=args.framework,
                    answer_model=args.answer_model,
                    answer_base_url=args.answer_base_url,
                    answer_api_key=args.answer_api_key,
```

- [ ] **Step 5: 运行 registry 测试**

Run:

```bash
nanobot/.venv/bin/python -m pytest eval_test/tests/test_run_gold_framework_cli.py eval_test/tests/test_nanobot_runner.py eval_test/tests/test_framework_base.py -q
```

Expected: PASS，输出包含 `7 passed`。

- [ ] **Step 6: 运行 CLI help smoke**

Run:

```bash
nanobot/.venv/bin/python eval_test/run_gold_parallel_eval.py --help | rg -- '--framework|--answer-model'
```

Expected: 输出包含 `--framework` 和 `--answer-model`。

- [ ] **Step 7: 提交**

```bash
git add eval_test/frameworks/__init__.py eval_test/run_gold_parallel_eval.py eval_test/tests/test_run_gold_framework_cli.py
git commit -m "Add framework runner selection to gold evaluator"
```

---

### Task 4: TableClaw Tool Adapter

**Files:**
- Create: `eval_test/frameworks/tableclaw_tools.py`
- Create: `eval_test/tests/test_tableclaw_tool_adapter.py`

- [ ] **Step 1: 写失败测试**

创建 `eval_test/tests/test_tableclaw_tool_adapter.py`：

```python
from __future__ import annotations

from typing import Any

import pytest

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
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
nanobot/.venv/bin/python -m pytest eval_test/tests/test_tableclaw_tool_adapter.py -q
```

Expected: FAIL，错误包含 `ModuleNotFoundError: No module named 'frameworks.tableclaw_tools'`。

- [ ] **Step 3: 写 adapter**

创建 `eval_test/frameworks/tableclaw_tools.py`：

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool
from nanobot.agent.tools.context import ToolContext
from nanobot.agent.tools.tableclaw import (
    TableClawDomainKnowledgeTool,
    TableClawExtractMatrixTool,
    TableClawFilterTool,
    TableClawInspectTool,
    TableClawRankTool,
    TableClawRetrieveTablesTool,
    TableClawTimeSeriesTool,
    TableClawTopKTool,
)

DEFAULT_TABLECLAW_TOOL_CLASSES: list[type[Tool]] = [
    TableClawDomainKnowledgeTool,
    TableClawRetrieveTablesTool,
    TableClawInspectTool,
    TableClawExtractMatrixTool,
    TableClawTimeSeriesTool,
    TableClawTopKTool,
    TableClawRankTool,
    TableClawFilterTool,
]


class TableClawToolAdapter:
    def __init__(
        self,
        *,
        workspace: str | Path,
        tool_classes: list[type[Tool]] | None = None,
    ) -> None:
        self.workspace = str(Path(workspace).resolve())
        ctx = ToolContext(config=None, workspace=self.workspace, timezone="Asia/Shanghai")
        self._tools: dict[str, Tool] = {}
        for tool_cls in tool_classes or DEFAULT_TABLECLAW_TOOL_CLASSES:
            tool = tool_cls.create(ctx)
            self._tools[tool.name] = tool

    @property
    def tool_names(self) -> list[str]:
        return sorted(self._tools)

    def openai_tool_schemas(self) -> list[dict[str, Any]]:
        return [self._tools[name].to_schema() for name in self.tool_names]

    async def call(self, name: str, arguments: dict[str, Any] | str | None) -> tuple[str, dict[str, Any]]:
        if name not in self._tools:
            error = f"Error: Tool '{name}' not found. Available: {', '.join(self.tool_names)}"
            return error, {"tool": name, "args": arguments, "ok": False, "error": error}

        tool = self._tools[name]
        params = self._parse_arguments(arguments)
        if not isinstance(params, dict):
            error = f"parameters must be an object, got {type(params).__name__}"
            return f"Error: {error}", {"tool": name, "args": arguments, "ok": False, "error": error}

        cast_params = tool.cast_params(params)
        errors = tool.validate_params(cast_params)
        if errors:
            error = "; ".join(errors)
            return (
                f"Error: Invalid parameters for tool '{name}': {error}",
                {"tool": name, "args": cast_params, "ok": False, "error": error},
            )

        try:
            raw_result = await tool.execute(**cast_params)
            output = raw_result if isinstance(raw_result, str) else json.dumps(raw_result, ensure_ascii=False)
            return output, {"tool": name, "args": cast_params, "ok": True, "output_preview": output[:500]}
        except Exception as exc:
            error = repr(exc)
            return f"Error executing {name}: {error}", {"tool": name, "args": cast_params, "ok": False, "error": error}

    @staticmethod
    def _parse_arguments(arguments: dict[str, Any] | str | None) -> Any:
        if arguments is None:
            return {}
        if isinstance(arguments, dict):
            return arguments
        try:
            return json.loads(arguments)
        except json.JSONDecodeError:
            return arguments
```

- [ ] **Step 4: 运行 adapter 测试**

Run:

```bash
nanobot/.venv/bin/python -m pytest eval_test/tests/test_tableclaw_tool_adapter.py -q
```

Expected: PASS，输出包含 `3 passed`。

- [ ] **Step 5: 提交**

```bash
git add eval_test/frameworks/tableclaw_tools.py eval_test/tests/test_tableclaw_tool_adapter.py
git commit -m "Add TableClaw tool adapter for framework runners"
```

---

### Task 5: Framework Trace Output

**Files:**
- Modify: `eval_test/run_gold_parallel_eval.py`
- Modify: `eval_test/tests/test_run_gold_framework_cli.py`

- [ ] **Step 1: 写 trace helper 测试**

追加到 `eval_test/tests/test_run_gold_framework_cli.py`：

```python
import json

from run_gold_parallel_eval import write_framework_trace


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
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
nanobot/.venv/bin/python -m pytest eval_test/tests/test_run_gold_framework_cli.py::test_write_framework_trace -q
```

Expected: FAIL，错误包含 `cannot import name 'write_framework_trace'`。

- [ ] **Step 3: 实现 trace helper**

在 `eval_test/run_gold_parallel_eval.py` 的 `write_markdown()` 前增加：

```python
def write_framework_trace(output_dir: Path, run_id: str, item: dict[str, Any]) -> Path:
    framework = str(item.get("framework") or "unknown")
    task_id = str(item.get("task_id") or "unknown_task")
    trace_dir = output_dir / "traces" / run_id / framework
    trace_dir.mkdir(parents=True, exist_ok=True)
    path = trace_dir / f"{task_id}.json"
    payload = {
        "task_id": task_id,
        "framework": framework,
        "question": item.get("question"),
        "answer": item.get("answer"),
        "tool_timeline": item.get("tool_timeline") or [],
        "framework_trace": item.get("framework_trace") or {},
        "elapsed_ms": item.get("elapsed_ms"),
        "usage": item.get("usage") or {},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
```

在 worker 成功/失败 item append 后、写 JSONL 前调用：

```python
                write_framework_trace(output_dir, args.run_id, item)
```

- [ ] **Step 4: 运行 trace 测试**

Run:

```bash
nanobot/.venv/bin/python -m pytest eval_test/tests/test_run_gold_framework_cli.py -q
```

Expected: PASS，输出包含 `4 passed`。

- [ ] **Step 5: 提交**

```bash
git add eval_test/run_gold_parallel_eval.py eval_test/tests/test_run_gold_framework_cli.py
git commit -m "Write per-task framework traces"
```

---

### Task 6: Remove Hardcoded API Key Fallbacks

**Files:**
- Modify: `eval_gold_parallel.sh`
- Modify: `start.sh`
- Modify: `eval.sh`

- [ ] **Step 1: 写检查命令确认当前失败**

Run:

```bash
rg -n 'DASHSCOPE_API_KEY=.*sk-' eval_gold_parallel.sh start.sh eval.sh
```

Expected: 输出命中 3 个脚本中的 hardcoded fallback。

- [ ] **Step 2: 修改 shell 脚本**

把每个脚本里的 fallback：

```bash
export DASHSCOPE_API_KEY="${DASHSCOPE_API_KEY:-sk-...}"
```

替换为：

```bash
if [ -z "${DASHSCOPE_API_KEY:-}" ]; then
  echo "DASHSCOPE_API_KEY is required. Export it before running this script." >&2
  exit 1
fi
export DASHSCOPE_API_KEY
```

- [ ] **Step 3: 运行检查命令确认无密钥 fallback**

Run:

```bash
rg -n 'DASHSCOPE_API_KEY=.*sk-' eval_gold_parallel.sh start.sh eval.sh
```

Expected: exit code 1，无输出。

- [ ] **Step 4: 运行 shell 语法检查**

Run:

```bash
bash -n eval_gold_parallel.sh
bash -n start.sh
bash -n eval.sh
```

Expected: 三条命令均无输出且 exit code 0。

- [ ] **Step 5: 提交**

```bash
git add eval_gold_parallel.sh start.sh eval.sh
git commit -m "Require DashScope API key from environment"
```

---

### Task 7: Optional Framework Dependencies

**Files:**
- Create: `eval_test/frameworks/requirements-frameworks.txt`

- [ ] **Step 1: 创建依赖清单**

创建 `eval_test/frameworks/requirements-frameworks.txt`：

```text
openai-agents>=0.6.0
langgraph>=1.0.0
langchain>=1.0.0
langchain-openai>=1.0.0
autogen-agentchat>=0.7.0
autogen-ext[openai]>=0.7.0
```

- [ ] **Step 2: 验证文件可读**

Run:

```bash
nanobot/.venv/bin/python - <<'PY'
from pathlib import Path
path = Path("eval_test/frameworks/requirements-frameworks.txt")
items = [line.strip() for line in path.read_text().splitlines() if line.strip()]
assert "openai-agents>=0.6.0" in items
assert "langgraph>=1.0.0" in items
assert "autogen-agentchat>=0.7.0" in items
print("framework requirements ok")
PY
```

Expected: 输出 `framework requirements ok`。

- [ ] **Step 3: 提交**

```bash
git add eval_test/frameworks/requirements-frameworks.txt
git commit -m "Document optional framework dependencies"
```

---

### Task 8: OpenAI Agents SDK Runner

**Files:**
- Create: `eval_test/frameworks/openai_agents_runner.py`
- Create: `eval_test/tests/test_openai_agents_runner.py`

- [ ] **Step 1: 写 missing dependency 测试**

创建 `eval_test/tests/test_openai_agents_runner.py`：

```python
from __future__ import annotations

import pytest

from frameworks.openai_agents_runner import OpenAIAgentsRunner


def test_openai_agents_runner_name() -> None:
    assert OpenAIAgentsRunner().name == "openai-agents-sdk"


def test_openai_agents_runner_missing_dependency_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_import(name: str):
        raise ModuleNotFoundError(name)

    runner = OpenAIAgentsRunner(import_module=fake_import)

    with pytest.raises(RuntimeError, match="Install optional framework dependencies"):
        runner._load_agents_sdk()
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
nanobot/.venv/bin/python -m pytest eval_test/tests/test_openai_agents_runner.py -q
```

Expected: FAIL，错误包含 `ModuleNotFoundError: No module named 'frameworks.openai_agents_runner'`。

- [ ] **Step 3: 写 runner skeleton 和 SDK 加载**

创建 `eval_test/frameworks/openai_agents_runner.py`：

```python
from __future__ import annotations

import importlib
import json
import time
from typing import Any, Callable

from openai import AsyncOpenAI

from .base import FrameworkRunContext, FrameworkRunResult, ensure_framework_result
from .tableclaw_tools import TableClawToolAdapter


class OpenAIAgentsRunner:
    name = "openai-agents-sdk"

    def __init__(self, import_module: Callable[[str], Any] = importlib.import_module) -> None:
        self._import_module = import_module

    def _load_agents_sdk(self) -> Any:
        try:
            return self._import_module("agents")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Install optional framework dependencies with: "
                "nanobot/.venv/bin/python -m pip install -r eval_test/frameworks/requirements-frameworks.txt"
            ) from exc

    async def run(
        self,
        task: dict[str, Any],
        prompt: str,
        context: FrameworkRunContext,
    ) -> FrameworkRunResult:
        agents = self._load_agents_sdk()
        adapter = TableClawToolAdapter(workspace=context.workspace)
        tool_timeline: list[dict[str, Any]] = []

        tools = []
        for schema in adapter.openai_tool_schemas():
            fn = schema["function"]

            async def invoke_tool(_ctx: Any, args: str, *, tool_name: str = fn["name"]) -> str:
                output, event = await adapter.call(tool_name, args)
                tool_timeline.append(event)
                return output

            tools.append(
                agents.FunctionTool(
                    name=fn["name"],
                    description=fn["description"],
                    params_json_schema=fn["parameters"],
                    on_invoke_tool=invoke_tool,
                    strict_json_schema=False,
                )
            )

        client = AsyncOpenAI(api_key=context.api_key, base_url=context.base_url)
        model = agents.OpenAIChatCompletionsModel(model=context.model, openai_client=client)
        agent = agents.Agent(
            name="TableClaw Analyst",
            instructions=(
                "你是 TableClaw 表格分析 agent。使用工具定位表、检查 schema、抽取数据，"
                "最后用中文直接回答，并列出使用的表文件名。"
            ),
            model=model,
            tools=tools,
        )
        started = time.time()
        result = await agents.Runner.run(agent, prompt)
        elapsed_ms = int((time.time() - started) * 1000)
        answer = str(result.final_output)
        tools_used = [event["tool"] for event in tool_timeline if event.get("ok")]
        tableclaw_tools_used = list(dict.fromkeys(tools_used))
        payload: dict[str, Any] = {
            "answer": answer,
            "usage": {},
            "elapsed_ms": elapsed_ms,
            "tools_used": tableclaw_tools_used,
            "tool_timeline": tool_timeline,
            "retrieval_tool_called": "tableclaw_retrieve_tables" in tableclaw_tools_used,
            "inspect_tool_called": "tableclaw_inspect" in tableclaw_tools_used,
            "tableclaw_tools_used": tableclaw_tools_used,
            "skill_selected": False,
            "selected_skills": [],
            "framework_trace": {
                "framework": context.framework,
                "runner": self.name,
                "task_id": task.get("id"),
                "raw_result_type": type(result).__name__,
            },
        }
        return ensure_framework_result(payload)
```

OpenAI Agents SDK 官方文档说明 custom `FunctionTool` 需要 `name`、`description`、`params_json_schema`、`on_invoke_tool`；模型侧使用 Chat Completions model 支持 OpenAI-compatible endpoint。

- [ ] **Step 4: 运行 non-network 测试**

Run:

```bash
nanobot/.venv/bin/python -m pytest eval_test/tests/test_openai_agents_runner.py -q
```

Expected: PASS，输出包含 `2 passed`。

- [ ] **Step 5: 提交**

```bash
git add eval_test/frameworks/openai_agents_runner.py eval_test/tests/test_openai_agents_runner.py
git commit -m "Add OpenAI Agents SDK framework runner"
```

---

### Task 9: LangGraph Runner

**Files:**
- Create: `eval_test/frameworks/langgraph_runner.py`
- Create: `eval_test/tests/test_langgraph_runner.py`

- [ ] **Step 1: 写 missing dependency 测试**

创建 `eval_test/tests/test_langgraph_runner.py`：

```python
from __future__ import annotations

import pytest

from frameworks.langgraph_runner import LangGraphRunner


def test_langgraph_runner_name() -> None:
    assert LangGraphRunner().name == "langgraph"


def test_langgraph_runner_missing_dependency_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_import(name: str):
        raise ModuleNotFoundError(name)

    runner = LangGraphRunner(import_module=fake_import)

    with pytest.raises(RuntimeError, match="Install optional framework dependencies"):
        runner._load_langgraph()
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
nanobot/.venv/bin/python -m pytest eval_test/tests/test_langgraph_runner.py -q
```

Expected: FAIL，错误包含 `ModuleNotFoundError: No module named 'frameworks.langgraph_runner'`。

- [ ] **Step 3: 写 LangGraph runner skeleton**

创建 `eval_test/frameworks/langgraph_runner.py`：

```python
from __future__ import annotations

import importlib
import time
from typing import Any, Callable

from openai import AsyncOpenAI

from .base import FrameworkRunContext, FrameworkRunResult, ensure_framework_result
from .tableclaw_tools import TableClawToolAdapter


class LangGraphRunner:
    name = "langgraph"

    def __init__(self, import_module: Callable[[str], Any] = importlib.import_module) -> None:
        self._import_module = import_module

    def _load_langgraph(self) -> dict[str, Any]:
        try:
            graph = self._import_module("langgraph.graph")
            messages = self._import_module("langchain_core.messages")
            chat_models = self._import_module("langchain_openai")
            tools_mod = self._import_module("langchain_core.tools")
            return {
                "StateGraph": graph.StateGraph,
                "START": graph.START,
                "END": graph.END,
                "HumanMessage": messages.HumanMessage,
                "SystemMessage": messages.SystemMessage,
                "AIMessage": messages.AIMessage,
                "ToolMessage": messages.ToolMessage,
                "ChatOpenAI": chat_models.ChatOpenAI,
                "StructuredTool": tools_mod.StructuredTool,
            }
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Install optional framework dependencies with: "
                "nanobot/.venv/bin/python -m pip install -r eval_test/frameworks/requirements-frameworks.txt"
            ) from exc

    async def run(
        self,
        task: dict[str, Any],
        prompt: str,
        context: FrameworkRunContext,
    ) -> FrameworkRunResult:
        lg = self._load_langgraph()
        adapter = TableClawToolAdapter(workspace=context.workspace)
        tool_timeline: list[dict[str, Any]] = []

        def make_tool(tool_name: str):
            async def call_tool(**kwargs: Any) -> str:
                output, event = await adapter.call(tool_name, kwargs)
                tool_timeline.append(event)
                return output

            return lg["StructuredTool"].from_function(
                coroutine=call_tool,
                name=tool_name,
                description=adapter._tools[tool_name].description,
                args_schema=None,
            )

        tools = [make_tool(name) for name in adapter.tool_names]
        model = lg["ChatOpenAI"](
            model=context.model,
            temperature=0,
            api_key=context.api_key,
            base_url=context.base_url,
        ).bind_tools(tools)

        class GraphState(dict):
            pass

        async def solve_node(state: dict[str, Any]) -> dict[str, Any]:
            messages = state["messages"]
            response = await model.ainvoke(messages)
            return {"messages": [*messages, response], "iteration_count": state["iteration_count"] + 1}

        async def tool_node(state: dict[str, Any]) -> dict[str, Any]:
            last = state["messages"][-1]
            messages = list(state["messages"])
            for tool_call in getattr(last, "tool_calls", []) or []:
                output, event = await adapter.call(tool_call["name"], tool_call.get("args") or {})
                tool_timeline.append(event)
                messages.append(lg["ToolMessage"](content=output, tool_call_id=tool_call["id"]))
            return {"messages": messages, "iteration_count": state["iteration_count"]}

        def route_after_solve(state: dict[str, Any]) -> str:
            last = state["messages"][-1]
            if state["iteration_count"] >= 8:
                return "final"
            if getattr(last, "tool_calls", None):
                return "tools"
            return "final"

        builder = lg["StateGraph"](GraphState)
        builder.add_node("solve", solve_node)
        builder.add_node("tools", tool_node)
        builder.add_edge(lg["START"], "solve")
        builder.add_conditional_edges("solve", route_after_solve, {"tools": "tools", "final": lg["END"]})
        builder.add_edge("tools", "solve")
        graph = builder.compile()

        started = time.time()
        result_state = await graph.ainvoke(
            {
                "messages": [
                    lg["SystemMessage"](
                        content="你是 TableClaw 表格分析 agent。使用工具完成表格定位、抽取和校验。"
                    ),
                    lg["HumanMessage"](content=prompt),
                ],
                "iteration_count": 0,
            }
        )
        elapsed_ms = int((time.time() - started) * 1000)
        answer = str(result_state["messages"][-1].content)
        tools_used = [event["tool"] for event in tool_timeline if event.get("ok")]
        tableclaw_tools_used = list(dict.fromkeys(tools_used))
        payload: dict[str, Any] = {
            "answer": answer,
            "usage": {},
            "elapsed_ms": elapsed_ms,
            "tools_used": tableclaw_tools_used,
            "tool_timeline": tool_timeline,
            "retrieval_tool_called": "tableclaw_retrieve_tables" in tableclaw_tools_used,
            "inspect_tool_called": "tableclaw_inspect" in tableclaw_tools_used,
            "tableclaw_tools_used": tableclaw_tools_used,
            "skill_selected": False,
            "selected_skills": [],
            "framework_trace": {
                "framework": context.framework,
                "runner": self.name,
                "task_id": task.get("id"),
                "message_count": len(result_state["messages"]),
                "iteration_count": result_state.get("iteration_count"),
            },
        }
        return ensure_framework_result(payload)
```

LangGraph 官方 quickstart 用 `StateGraph`、`START`、`END`、node、conditional edge 组织状态图；本 runner 首轮只实现 solve/tool loop，显式 verifier 在 Task 11 加。

- [ ] **Step 4: 运行 non-network 测试**

Run:

```bash
nanobot/.venv/bin/python -m pytest eval_test/tests/test_langgraph_runner.py -q
```

Expected: PASS，输出包含 `2 passed`。

- [ ] **Step 5: 提交**

```bash
git add eval_test/frameworks/langgraph_runner.py eval_test/tests/test_langgraph_runner.py
git commit -m "Add LangGraph framework runner"
```

---

### Task 10: AutoGen Runner

**Files:**
- Create: `eval_test/frameworks/autogen_runner.py`
- Create: `eval_test/tests/test_autogen_runner.py`

- [ ] **Step 1: 写 missing dependency 测试**

创建 `eval_test/tests/test_autogen_runner.py`：

```python
from __future__ import annotations

import pytest

from frameworks.autogen_runner import AutoGenRunner


def test_autogen_runner_name() -> None:
    assert AutoGenRunner().name == "autogen"


def test_autogen_runner_missing_dependency_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_import(name: str):
        raise ModuleNotFoundError(name)

    runner = AutoGenRunner(import_module=fake_import)

    with pytest.raises(RuntimeError, match="Install optional framework dependencies"):
        runner._load_autogen()
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
nanobot/.venv/bin/python -m pytest eval_test/tests/test_autogen_runner.py -q
```

Expected: FAIL，错误包含 `ModuleNotFoundError: No module named 'frameworks.autogen_runner'`。

- [ ] **Step 3: 写 AutoGen runner skeleton**

创建 `eval_test/frameworks/autogen_runner.py`：

```python
from __future__ import annotations

import importlib
import time
from typing import Any, Callable

from .base import FrameworkRunContext, FrameworkRunResult, ensure_framework_result
from .tableclaw_tools import TableClawToolAdapter


class AutoGenRunner:
    name = "autogen"

    def __init__(self, import_module: Callable[[str], Any] = importlib.import_module) -> None:
        self._import_module = import_module

    def _load_autogen(self) -> dict[str, Any]:
        try:
            agentchat_agents = self._import_module("autogen_agentchat.agents")
            agentchat_teams = self._import_module("autogen_agentchat.teams")
            agentchat_conditions = self._import_module("autogen_agentchat.conditions")
            openai_ext = self._import_module("autogen_ext.models.openai")
            return {
                "AssistantAgent": agentchat_agents.AssistantAgent,
                "RoundRobinGroupChat": agentchat_teams.RoundRobinGroupChat,
                "MaxMessageTermination": agentchat_conditions.MaxMessageTermination,
                "OpenAIChatCompletionClient": openai_ext.OpenAIChatCompletionClient,
            }
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Install optional framework dependencies with: "
                "nanobot/.venv/bin/python -m pip install -r eval_test/frameworks/requirements-frameworks.txt"
            ) from exc

    async def run(
        self,
        task: dict[str, Any],
        prompt: str,
        context: FrameworkRunContext,
    ) -> FrameworkRunResult:
        ag = self._load_autogen()
        adapter = TableClawToolAdapter(workspace=context.workspace)
        tool_timeline: list[dict[str, Any]] = []

        def make_tool(tool_name: str):
            async def call_tool(**kwargs: Any) -> str:
                output, event = await adapter.call(tool_name, kwargs)
                tool_timeline.append(event)
                return output

            call_tool.__name__ = tool_name
            call_tool.__doc__ = adapter._tools[tool_name].description
            return call_tool

        tools = [make_tool(name) for name in adapter.tool_names]
        model_client = ag["OpenAIChatCompletionClient"](
            model=context.model,
            api_key=context.api_key,
            base_url=context.base_url,
        )
        planner = ag["AssistantAgent"](
            "planner",
            model_client=model_client,
            system_message="你负责理解问题，决定需要哪些表格工具和验证重点。",
        )
        analyst = ag["AssistantAgent"](
            "analyst",
            model_client=model_client,
            tools=tools,
            system_message="你负责调用 TableClaw 工具，抽取数据，并给出候选答案。",
        )
        verifier = ag["AssistantAgent"](
            "verifier",
            model_client=model_client,
            system_message="你负责检查答案是否包含表、月份、范围、指标、数值和完成状态。不要使用 gold answer。",
        )
        team = ag["RoundRobinGroupChat"](
            [planner, analyst, verifier],
            termination_condition=ag["MaxMessageTermination"](max_messages=9),
        )

        started = time.time()
        result = await team.run(task=prompt)
        elapsed_ms = int((time.time() - started) * 1000)
        messages = list(getattr(result, "messages", []) or [])
        answer = str(getattr(messages[-1], "content", "")) if messages else ""
        tools_used = [event["tool"] for event in tool_timeline if event.get("ok")]
        tableclaw_tools_used = list(dict.fromkeys(tools_used))
        payload: dict[str, Any] = {
            "answer": answer,
            "usage": {},
            "elapsed_ms": elapsed_ms,
            "tools_used": tableclaw_tools_used,
            "tool_timeline": tool_timeline,
            "retrieval_tool_called": "tableclaw_retrieve_tables" in tableclaw_tools_used,
            "inspect_tool_called": "tableclaw_inspect" in tableclaw_tools_used,
            "tableclaw_tools_used": tableclaw_tools_used,
            "skill_selected": False,
            "selected_skills": [],
            "framework_trace": {
                "framework": context.framework,
                "runner": self.name,
                "task_id": task.get("id"),
                "message_count": len(messages),
            },
        }
        close = getattr(model_client, "close", None)
        if close:
            await close()
        return ensure_framework_result(payload)
```

- [ ] **Step 4: 运行 non-network 测试**

Run:

```bash
nanobot/.venv/bin/python -m pytest eval_test/tests/test_autogen_runner.py -q
```

Expected: PASS，输出包含 `2 passed`。

- [ ] **Step 5: 提交**

```bash
git add eval_test/frameworks/autogen_runner.py eval_test/tests/test_autogen_runner.py
git commit -m "Add AutoGen framework runner"
```

---

### Task 11: LangGraph Verifier Loop

**Files:**
- Modify: `eval_test/frameworks/langgraph_runner.py`
- Create: `eval_test/tests/test_langgraph_state_helpers.py`

- [ ] **Step 1: 写 verifier routing 测试**

创建 `eval_test/tests/test_langgraph_state_helpers.py`：

```python
from __future__ import annotations

from frameworks.langgraph_runner import route_after_verify


def test_route_after_verify_final_when_passed() -> None:
    state = {"verification": {"passed": True}, "repair_count": 0, "max_repairs": 1}
    assert route_after_verify(state) == "final"


def test_route_after_verify_repairs_once() -> None:
    state = {"verification": {"passed": False}, "repair_count": 0, "max_repairs": 1}
    assert route_after_verify(state) == "solve"


def test_route_after_verify_stops_at_cap() -> None:
    state = {"verification": {"passed": False}, "repair_count": 1, "max_repairs": 1}
    assert route_after_verify(state) == "final"
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
nanobot/.venv/bin/python -m pytest eval_test/tests/test_langgraph_state_helpers.py -q
```

Expected: FAIL，错误包含 `cannot import name 'route_after_verify'`。

- [ ] **Step 3: 增加 helper 和 verifier node**

在 `eval_test/frameworks/langgraph_runner.py` 顶层增加：

```python
def route_after_verify(state: dict[str, Any]) -> str:
    verification = state.get("verification") or {}
    if verification.get("passed"):
        return "final"
    if int(state.get("repair_count") or 0) >= int(state.get("max_repairs") or 0):
        return "final"
    return "solve"
```

在 `run()` 内增加 verifier node：

```python
        async def verify_node(state: dict[str, Any]) -> dict[str, Any]:
            last = state["messages"][-1]
            content = str(getattr(last, "content", ""))
            passed = all(marker in content for marker in ("使用", "完成"))
            verification = {
                "passed": passed,
                "reason": "answer includes source/completion markers" if passed else "answer lacks source/completion markers",
            }
            repair_count = int(state.get("repair_count") or 0)
            if not passed:
                repair_count += 1
                state["messages"].append(
                    lg["HumanMessage"](
                        content=(
                            "请修正上一个答案：必须说明使用了哪些上传表，并说明是否成功完成。"
                        )
                    )
                )
            return {
                "messages": state["messages"],
                "verification": verification,
                "repair_count": repair_count,
                "iteration_count": state["iteration_count"],
            }
```

把 graph edge 从 `solve -> END` 改为 `solve -> verify -> conditional`：

```python
        builder.add_conditional_edges("solve", route_after_solve, {"tools": "tools", "final": "verify"})
        builder.add_conditional_edges("verify", route_after_verify, {"solve": "solve", "final": lg["END"]})
```

初始 state 增加：

```python
                "verification": {},
                "repair_count": 0,
                "max_repairs": 1,
```

`framework_trace` 增加：

```python
                "verification": result_state.get("verification") or {},
                "repair_count": result_state.get("repair_count") or 0,
```

- [ ] **Step 4: 运行 helper 测试**

Run:

```bash
nanobot/.venv/bin/python -m pytest eval_test/tests/test_langgraph_state_helpers.py eval_test/tests/test_langgraph_runner.py -q
```

Expected: PASS，输出包含 `5 passed`。

- [ ] **Step 5: 提交**

```bash
git add eval_test/frameworks/langgraph_runner.py eval_test/tests/test_langgraph_state_helpers.py
git commit -m "Add LangGraph verifier repair routing"
```

---

### Task 12: Framework Comparison Smoke Commands And Documentation

**Files:**
- Create: `docs/实验评测/gold-cases/runs/2026-06-22-framework-comparison-smoke-plan.md`
- Modify: `docs/superpowers/specs/2026-06-22-framework-comparison-design.md`

- [ ] **Step 1: 写中文 smoke run 说明**

创建 `docs/实验评测/gold-cases/runs/2026-06-22-framework-comparison-smoke-plan.md`：

```markdown
# 2026-06-22 Framework Comparison Smoke Plan

> 本文件记录首轮 framework comparison 的运行口径。正式结果文件在跑完 smoke 后另行归档。

## 固定口径

- Answer model: `deepseek-v4-pro`
- Judge model: `deepseek-v4-pro`
- Provider: DashScope OpenAI-compatible API
- Dataset smoke: `eval_test/test_dataset/bad_cases.jsonl --limit 10`
- Workspace: `workspace/`
- Domain pack: `domain_packs/sichuan-finance`
- Prompt: `eval_test/run_eval.py::render_prompt`
- Judge: `data-correctness-v5-2026-06-16`

## Baseline smoke

```bash
./eval_gold_parallel.sh \
  --framework nanobot-current \
  --task-file eval_test/test_dataset/bad_cases.jsonl \
  --limit 10 \
  --concurrency 2 \
  --run-id framework-smoke-nanobot-current
```

```bash
./eval_gold_parallel.sh \
  --framework nanobot-skill-off \
  --task-file eval_test/test_dataset/bad_cases.jsonl \
  --limit 10 \
  --concurrency 2 \
  --run-id framework-smoke-nanobot-skill-off
```

## Optional framework smoke

安装可选依赖后再运行：

```bash
nanobot/.venv/bin/python -m pip install -r eval_test/frameworks/requirements-frameworks.txt
```

```bash
./eval_gold_parallel.sh \
  --framework openai-agents-sdk \
  --task-file eval_test/test_dataset/bad_cases.jsonl \
  --limit 10 \
  --concurrency 1 \
  --run-id framework-smoke-openai-agents
```

```bash
./eval_gold_parallel.sh \
  --framework langgraph \
  --task-file eval_test/test_dataset/bad_cases.jsonl \
  --limit 10 \
  --concurrency 1 \
  --run-id framework-smoke-langgraph
```

```bash
./eval_gold_parallel.sh \
  --framework autogen \
  --task-file eval_test/test_dataset/bad_cases.jsonl \
  --limit 10 \
  --concurrency 1 \
  --run-id framework-smoke-autogen
```

## 判断规则

- 如果 LangGraph 在 hard cases 上更稳，说明显式 state / verifier loop 值得吸收。
- 如果 OpenAI Agents SDK 接近 LangGraph，说明轻量 runtime 不是主要瓶颈。
- 如果 AutoGen 明显更稳但成本高，优先把 verifier step 移植回 TableClaw，而不是直接换多 agent runtime。
- 如果所有框架失败在同一类 case，先归因到 tool/domain/eval/data。
```

- [ ] **Step 2: 给 design spec 增加中文说明**

在 `docs/superpowers/specs/2026-06-22-framework-comparison-design.md` 顶部 `Status` 后增加：

```markdown
> 说明：后续 TableClaw 内部 spec 和 plan 默认使用中文；只有对外英文读者或上游框架引用需要英文时再切换。
```

- [ ] **Step 3: 运行 Markdown 文件检查**

Run:

```bash
test -f docs/实验评测/gold-cases/runs/2026-06-22-framework-comparison-smoke-plan.md
test -f docs/superpowers/specs/2026-06-22-framework-comparison-design.md
rg -n 'deepseek-v4-pro|framework-smoke-langgraph|默认使用中文' docs/实验评测/gold-cases/runs/2026-06-22-framework-comparison-smoke-plan.md docs/superpowers/specs/2026-06-22-framework-comparison-design.md
```

Expected: `rg` 输出包含 `deepseek-v4-pro`、`framework-smoke-langgraph`、`默认使用中文`。

- [ ] **Step 4: 提交**

```bash
git add docs/实验评测/gold-cases/runs/2026-06-22-framework-comparison-smoke-plan.md docs/superpowers/specs/2026-06-22-framework-comparison-design.md
git commit -m "Document framework comparison smoke plan"
```

---

### Task 13: Full Non-Network Test Pass

**Files:**
- No code file changes expected.

- [ ] **Step 1: 运行全部新增单元测试**

Run:

```bash
nanobot/.venv/bin/python -m pytest eval_test/tests -q
```

Expected: PASS，输出至少包含这些测试文件的通过计数：

```text
test_framework_base.py
test_nanobot_runner.py
test_tableclaw_tool_adapter.py
test_run_gold_framework_cli.py
test_openai_agents_runner.py
test_langgraph_runner.py
test_autogen_runner.py
test_langgraph_state_helpers.py
```

- [ ] **Step 2: 运行 CLI help smoke**

Run:

```bash
nanobot/.venv/bin/python eval_test/run_gold_parallel_eval.py --help | rg -- '--framework|--answer-model|--answer-base-url'
```

Expected: 输出包含：

```text
--framework
--answer-model
--answer-base-url
```

- [ ] **Step 3: 确认 no-secret scan**

Run:

```bash
rg -n 'DASHSCOPE_API_KEY=.*sk-|sk-[A-Za-z0-9]{20,}' eval_gold_parallel.sh start.sh eval.sh eval_test docs
```

Expected: exit code 1，无输出。

- [ ] **Step 4: 确认 worktree 干净**

Run:

```bash
git status --short
```

Expected: 无输出。

- [ ] **Step 5: 推送实验分支**

```bash
git push
```

Expected: 输出包含 `codex/framework-comparison -> codex/framework-comparison` 或 `Everything up-to-date`。

---

### Task 14: First Real Nanobot Smoke Run

**Files:**
- Generated files under `eval_test/results/` are ignored by git.
- Human summary can be added later after results are reviewed.

- [ ] **Step 1: 确认环境变量**

Run:

```bash
test -n "${DASHSCOPE_API_KEY:-}" && echo "DASHSCOPE_API_KEY present"
```

Expected: 输出 `DASHSCOPE_API_KEY present`。

- [ ] **Step 2: 同步 domain pack**

Run:

```bash
scripts/sync_domain_pack.sh domain_packs/sichuan-finance workspace
```

Expected: 输出显示 domain knowledge / skill 已同步，exit code 0。

- [ ] **Step 3: 跑 2 条 Nanobot current smoke**

Run:

```bash
./eval_gold_parallel.sh \
  --framework nanobot-current \
  --task-file eval_test/test_dataset/bad_cases.jsonl \
  --limit 2 \
  --concurrency 1 \
  --run-id framework-smoke-nanobot-current-2
```

Expected:

```text
[1/2] running ...
[2/2] running ...
Markdown report: ...
```

`latest_summary.json` 中 `summary.framework` 应为 `nanobot-current`。

- [ ] **Step 4: 跑 2 条 Nanobot skill-off smoke**

Run:

```bash
./eval_gold_parallel.sh \
  --framework nanobot-skill-off \
  --task-file eval_test/test_dataset/bad_cases.jsonl \
  --limit 2 \
  --concurrency 1 \
  --run-id framework-smoke-nanobot-skill-off-2
```

Expected: 运行完成，`latest_summary.json` 中 `summary.framework` 应为 `nanobot-skill-off`。

- [ ] **Step 5: 归档观察**

如果两个 smoke 都能完成，创建 `docs/实验评测/gold-cases/runs/2026-06-22-framework-comparison-smoke-nanobot.md`，内容：

```markdown
# 2026-06-22 Framework Comparison Nanobot Smoke

## Scope

- Frameworks: `nanobot-current`, `nanobot-skill-off`
- Dataset: `eval_test/test_dataset/bad_cases.jsonl`
- Limit: 2 per framework
- Model: `deepseek-v4-pro`

## Result

记录两个 run 的 ACC、runtime error、elapsed、token、trace 路径。

## Observation

记录 runner 抽象是否保持了现有 Nanobot 行为，以及下一步是否可以安装可选 framework 依赖。
```

把实际指标填入该文件后提交：

```bash
git add docs/实验评测/gold-cases/runs/2026-06-22-framework-comparison-smoke-nanobot.md
git commit -m "Archive nanobot framework smoke result"
git push
```

## 参考文档

- OpenAI Agents SDK custom `FunctionTool` 需要 `name`、`description`、`params_json_schema`、`on_invoke_tool`；见官方 Tools 文档。
- OpenAI Agents SDK model 文档说明可使用 Chat Completions model 和 OpenAI-compatible provider 入口。
- LangGraph quickstart 使用 `StateGraph`、`START`、`END`、node、conditional edge 建图。
- AutoGen runner 按 AgentChat quickstart 的 AssistantAgent / team 模式接入，实际安装后用 smoke 测试校准 API 差异。
