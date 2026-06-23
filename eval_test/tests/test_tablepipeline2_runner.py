from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from frameworks.base import FrameworkRunContext
from frameworks.tablepipeline2_runner import TablePipelineV2Runner


class FakeTablePipelineV2:
    def __init__(
        self,
        data_dir: str,
        qq_knowledge_path: str,
        callback_uuid: str,
        **kwargs: Any,
    ) -> None:
        self.data_dir = data_dir
        self.qq_knowledge_path = qq_knowledge_path
        self.callback_uuid = callback_uuid
        self.kwargs = kwargs

    async def generate_pipeline_response(self, question: str) -> tuple[str, list[str], list[dict[str, Any]]]:
        return (
            f"最终答案：{question}",
            [question],
            [{"retrieve_final_result": ["全国各省份数据-通报应收总额_202505.csv"]}],
        )


class FakePipelineModule:
    TablePipeline = FakeTablePipelineV2


def test_tablepipeline_v2_runner_name() -> None:
    assert TablePipelineV2Runner().name == "tablepipeline-v2"


@pytest.mark.asyncio
async def test_tablepipeline_v2_runner_uses_v2_final_answer(tmp_path: Path) -> None:
    root = tmp_path / "tablepipeline-2"
    data_dir = tmp_path / "preprocessed"
    qq_knowledge = root / "指标知识库0123.xlsx"
    root.mkdir()
    data_dir.mkdir()
    qq_knowledge.write_bytes(b"fake")

    def fake_import(name: str) -> Any:
        assert name == "pipeline"
        return FakePipelineModule

    runner = TablePipelineV2Runner(
        import_module=fake_import,
        root=root,
        data_dir=data_dir,
        qq_knowledge_path=qq_knowledge,
    )
    ctx = _context(tmp_path)

    result = await runner.run({"id": "case_001", "question": "四川是多少？"}, "prompt", ctx)

    assert result["answer"] == "最终答案：四川是多少？"
    assert result["retrieval_tool_called"] is True
    assert result["framework_trace"]["runner"] == "tablepipeline-v2"
    assert result["framework_trace"]["query_list"] == ["四川是多少？"]


@pytest.mark.asyncio
async def test_tablepipeline_v2_runner_requires_existing_data_dir(tmp_path: Path) -> None:
    root = tmp_path / "tablepipeline-2"
    root.mkdir()
    (root / "指标知识库0123.xlsx").write_bytes(b"fake")
    runner = TablePipelineV2Runner(root=root, data_dir=tmp_path / "missing")

    with pytest.raises(RuntimeError, match="tablepipeline-2 data dir not found"):
        await runner.run({"id": "case_001", "question": "四川是多少？"}, "prompt", _context(tmp_path))


def _context(tmp_path: Path) -> FrameworkRunContext:
    return FrameworkRunContext(
        framework="tablepipeline-v2",
        mode="skill-on",
        run_id="unit-run",
        config_path=None,
        workspace=str(tmp_path / "workspace"),
        model="deepseek-v4-pro",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="test-key",
    )
