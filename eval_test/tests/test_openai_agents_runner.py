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
