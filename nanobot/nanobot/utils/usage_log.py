"""Persist per-turn model usage records for TableClaw/Nanobot runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from filelock import FileLock


def _jsonable(value: Any) -> Any:
    """Convert provider-returned objects into JSON-friendly data."""
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def append_usage_record(workspace: Path, record: dict[str, Any]) -> Path:
    """Append one usage record to workspace/usage/usage.jsonl.

    The file is intentionally JSONL so long-running or concurrent CLI sessions
    can append cheaply and downstream analysis can stream it.
    """
    usage_dir = workspace / "usage"
    usage_dir.mkdir(parents=True, exist_ok=True)
    path = usage_dir / "usage.jsonl"

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **_jsonable(record),
    }

    lock = FileLock(str(path) + ".lock")
    with lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return path
