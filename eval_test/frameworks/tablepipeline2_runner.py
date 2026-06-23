from __future__ import annotations

import importlib
import os
import sys
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .base import FrameworkRunContext, FrameworkRunResult, ensure_framework_result


LOCAL_MODULE_PREFIXES = (
    "pipeline",
    "utils",
    "markdown_qa",
    "markdown_report",
    "tool_manager",
    "common",
)


class TablePipelineV2Runner:
    name = "tablepipeline-v2"

    def __init__(
        self,
        import_module: Callable[[str], Any] = importlib.import_module,
        root: Path | None = None,
        data_dir: Path | None = None,
        qq_knowledge_path: Path | None = None,
    ) -> None:
        self._import_module = import_module
        self._root = root
        self._data_dir = data_dir
        self._qq_knowledge_path = qq_knowledge_path

    def _resolve_root(self, context: FrameworkRunContext) -> Path:
        configured = (
            self._root
            or _path_from_extra(context, "tablepipeline2_root")
            or _path_from_env("TABLEPIPELINE2_ROOT")
        )
        if configured:
            return configured.resolve()

        workspace_parent = Path(context.workspace).resolve().parent
        candidates = [
            Path.cwd() / "tablepipeline-2",
            workspace_parent / "tablepipeline-2",
            workspace_parent.parent.parent / "tablepipeline-2",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()
        return candidates[0].resolve()

    def _resolve_data_dir(self, context: FrameworkRunContext, root: Path) -> Path:
        configured = (
            self._data_dir
            or _path_from_extra(context, "tablepipeline2_data_dir")
            or _path_from_env("TABLEPIPELINE2_DATA_DIR")
        )
        if configured:
            return configured.resolve()
        return root / "data"

    def _resolve_qq_knowledge_path(self, context: FrameworkRunContext, root: Path) -> Path:
        configured = (
            self._qq_knowledge_path
            or _path_from_extra(context, "tablepipeline2_qq_knowledge_path")
            or _path_from_env("TABLEPIPELINE2_QQ_KNOWLEDGE_PATH")
            or _path_from_env("QQ_KNOWLEDGE_PATH")
        )
        if configured:
            return configured.resolve()
        for name in ("指标知识库0123.xlsx", "指标知识库0512.xlsx", "指标知识库1219.xlsx"):
            candidate = root / name
            if candidate.exists():
                return candidate.resolve()
        return (root / "指标知识库0123.xlsx").resolve()

    def _load_pipeline_class(self, root: Path, context: FrameworkRunContext) -> Any:
        if not root.exists():
            raise RuntimeError(
                "tablepipeline-2 root not found. Set TABLEPIPELINE2_ROOT or "
                "pass --tablepipeline2-root."
            )

        _set_tablepipeline2_model_env(context)
        _clear_local_modules(root)
        root_str = str(root)
        if root_str in sys.path:
            sys.path.remove(root_str)
        sys.path.insert(0, root_str)

        with _temporary_cwd(root):
            module = self._import_module("pipeline")
        return module.TablePipeline

    async def run(
        self,
        task: dict[str, Any],
        prompt: str,
        context: FrameworkRunContext,
    ) -> FrameworkRunResult:
        root = self._resolve_root(context)
        data_dir = self._resolve_data_dir(context, root)
        qq_knowledge_path = self._resolve_qq_knowledge_path(context, root)

        if not data_dir.exists():
            raise RuntimeError(
                "tablepipeline-2 data dir not found. It must contain v2 preprocessed "
                "CSV/JSON table descriptions. Set TABLEPIPELINE2_DATA_DIR or pass "
                "--tablepipeline2-data-dir."
            )
        if not qq_knowledge_path.exists():
            raise RuntimeError(
                "tablepipeline-2 QQ knowledge file not found. Set "
                "TABLEPIPELINE2_QQ_KNOWLEDGE_PATH or pass --tablepipeline2-qq-knowledge-path."
            )

        table_pipeline_cls = self._load_pipeline_class(root, context)

        started = time.time()
        with _temporary_cwd(root):
            pipeline = table_pipeline_cls(
                str(data_dir),
                str(qq_knowledge_path),
                str(uuid.uuid4()),
                use_experience=_bool_from_extra(context, "tablepipeline2_use_experience", False),
            )
            raw_result = await pipeline.generate_pipeline_response(task["question"])

        elapsed_ms = int((time.time() - started) * 1000)
        answer, query_list, subquery_results = _unpack_pipeline_result(raw_result)
        retrieved_tables = _retrieved_tables(subquery_results)

        payload: dict[str, Any] = {
            "answer": answer,
            "usage": {},
            "elapsed_ms": elapsed_ms,
            "tools_used": ["tablepipeline_v2_pipeline"],
            "tool_timeline": [
                {
                    "tool": "tablepipeline_v2_pipeline",
                    "ok": True,
                    "data_dir": str(data_dir),
                    "qq_knowledge_path": str(qq_knowledge_path),
                    "retrieved_tables": retrieved_tables,
                }
            ],
            "retrieval_tool_called": bool(retrieved_tables),
            "inspect_tool_called": False,
            "tableclaw_tools_used": [],
            "skill_selected": False,
            "selected_skills": [],
            "framework_trace": {
                "framework": context.framework,
                "runner": self.name,
                "task_id": task.get("id"),
                "root": str(root),
                "data_dir": str(data_dir),
                "qq_knowledge_path": str(qq_knowledge_path),
                "query_list": query_list,
                "subquery_results": subquery_results,
                "note": (
                    "Self-developed TablePipeline v2 baseline. It uses its own "
                    "intent recognition, query rewriting, retrieval, Python agent loop, "
                    "and summarizer rather than TableClaw tools."
                ),
            },
        }
        return ensure_framework_result(payload)


def _set_tablepipeline2_model_env(context: FrameworkRunContext) -> None:
    # Force all internal LLM roles onto the benchmark answer model for a clean口径.
    values = {
        "model": context.model,
        "api_key": context.api_key,
        "api_url": context.base_url,
        "query_decompose_model": context.model,
        "query_decompose_api_url": context.base_url,
        "code_model": context.model,
        "code_api_url": context.base_url,
        "summarize_model": context.model,
        "summarize_api_url": context.base_url,
    }
    for key, value in values.items():
        os.environ[key] = value


def _clear_local_modules(root: Path) -> None:
    root_str = str(root)
    for name, module in list(sys.modules.items()):
        top_level = name.split(".", 1)[0]
        if top_level not in LOCAL_MODULE_PREFIXES:
            continue
        module_file = getattr(module, "__file__", "")
        if not module_file or root_str not in str(module_file):
            sys.modules.pop(name, None)


@contextmanager
def _temporary_cwd(path: Path) -> Iterator[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _path_from_env(name: str) -> Path | None:
    value = os.environ.get(name)
    return Path(value).expanduser() if value else None


def _path_from_extra(context: FrameworkRunContext, key: str) -> Path | None:
    value = context.extra.get(key)
    return Path(str(value)).expanduser() if value else None


def _bool_from_extra(context: FrameworkRunContext, key: str, default: bool) -> bool:
    value = context.extra.get(key)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _unpack_pipeline_result(raw_result: Any) -> tuple[str, list[Any], Any]:
    if isinstance(raw_result, tuple | list):
        answer = str(raw_result[0]) if raw_result else ""
        query_list = list(raw_result[1]) if len(raw_result) >= 2 and isinstance(raw_result[1], list) else []
        subquery_results = raw_result[2] if len(raw_result) >= 3 else []
        return answer, query_list, subquery_results
    return str(raw_result), [], []


def _retrieved_tables(subquery_results: Any) -> list[str]:
    tables: list[str] = []
    if not isinstance(subquery_results, list):
        return tables
    for item in subquery_results:
        if not isinstance(item, dict):
            continue
        retrieved = item.get("retrieve_final_result") or []
        if isinstance(retrieved, str):
            retrieved = [retrieved]
        for table in retrieved:
            if table:
                tables.append(str(table))
    return list(dict.fromkeys(tables))
