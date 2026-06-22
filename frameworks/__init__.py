from __future__ import annotations

from importlib import import_module
import sys

_impl = import_module("eval_test.frameworks")

__path__ = list(_impl.__path__)
__all__ = list(getattr(_impl, "__all__", ()))

for name in __all__:
    globals()[name] = getattr(_impl, name)

for module_name in ("base", "nanobot_runner"):
    sys.modules[f"{__name__}.{module_name}"] = import_module(f"eval_test.frameworks.{module_name}")
