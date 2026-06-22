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
