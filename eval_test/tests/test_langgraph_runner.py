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
