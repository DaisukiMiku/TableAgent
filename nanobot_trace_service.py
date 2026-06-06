from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FASTAPI_IMPORT_ERROR: ModuleNotFoundError | None = None

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import HTMLResponse
except ModuleNotFoundError as exc:  # pragma: no cover
    FASTAPI_IMPORT_ERROR = exc
    FastAPI = None  # type: ignore[assignment]
    HTTPException = RuntimeError  # type: ignore[assignment]
    Query = None  # type: ignore[assignment]
    HTMLResponse = str  # type: ignore[assignment]


def resolve_local_path(raw_path: str) -> Path:
    cleaned = raw_path.strip().strip('"').strip("'")
    if not cleaned:
        raise ValueError("jsonl 文件路径不能为空")

    path = Path(cleaned).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"目标不是文件: {path}")

    return path.resolve()


def load_jsonl_records(jsonl_path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    with jsonl_path.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue

            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"第 {line_no} 行不是合法 JSON: {exc.msg}") from exc

            if not isinstance(parsed, dict):
                raise ValueError(f"第 {line_no} 行不是 JSON 对象")

            parsed["_line_no"] = line_no
            records.append(parsed)

    return records


def escape_control_chars(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
        .replace("\f", "\\f")
        .replace("\b", "\\b")
    )


def decode_visible_escapes(text: str) -> str:
    return (
        text.replace("\\r", "\r")
        .replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace("\\f", "\f")
        .replace("\\b", "\b")
    )


def stringify_preview(value: Any, preserve_escape: bool) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return escape_control_chars(value) if preserve_escape else value

    dumped = json.dumps(value, ensure_ascii=False)
    return dumped if preserve_escape else decode_visible_escapes(dumped)


def format_string_value(value: str, preserve_escape: bool) -> str:
    if preserve_escape:
        return json.dumps(value, ensure_ascii=False)
    return '"' + value.replace('"', '\\"') + '"'


def format_json_like(value: Any, preserve_escape: bool, indent: int = 0) -> str:
    current_indent = "  " * indent
    next_indent = "  " * (indent + 1)

    if isinstance(value, dict):
        if not value:
            return "{}"

        items = list(value.items())
        lines = ["{"]
        for index, (key, item_value) in enumerate(items):
            suffix = "," if index < len(items) - 1 else ""
            rendered_key = json.dumps(str(key), ensure_ascii=False)
            rendered_value = format_json_like(item_value, preserve_escape, indent + 1)
            lines.append(f"{next_indent}{rendered_key}: {rendered_value}{suffix}")
        lines.append(f"{current_indent}}}")
        return "\n".join(lines)

    if isinstance(value, list):
        if not value:
            return "[]"

        lines = ["["]
        for index, item_value in enumerate(value):
            suffix = "," if index < len(value) - 1 else ""
            rendered_value = format_json_like(item_value, preserve_escape, indent + 1)
            lines.append(f"{next_indent}{rendered_value}{suffix}")
        lines.append(f"{current_indent}]")
        return "\n".join(lines)

    if isinstance(value, str):
        return format_string_value(value, preserve_escape)

    return json.dumps(value, ensure_ascii=False)


def render_record(record: dict[str, Any], preserve_escape: bool) -> str:
    safe_record = {key: value for key, value in record.items() if key != "_line_no"}
    return format_json_like(safe_record, preserve_escape)


def build_entry(record: dict[str, Any]) -> dict[str, Any]:
    role = record.get("role")
    tool_name = record.get("name")

    if role == "assistant":
        title = "assistant"
    elif role == "tool":
        title = f"tool · {tool_name or 'unknown'}"
    elif role == "user":
        title = "user"
    elif role:
        title = str(role)
    else:
        title = f"no-role · {record.get('_type', 'record')}"

    preview_candidates = [
        record.get("content"),
        record.get("reasoning_content"),
        tool_name,
        record.get("tool_calls"),
        record,
    ]

    preview_escaped = "(empty)"
    preview_unescaped = "(empty)"
    for candidate in preview_candidates:
        escaped = stringify_preview(candidate, preserve_escape=True)
        if escaped:
            preview_escaped = escaped
            preview_unescaped = stringify_preview(candidate, preserve_escape=False)
            break

    return {
        "line_no": record.get("_line_no"),
        "role": role,
        "title": title,
        "preview_escaped": preview_escaped,
        "preview_unescaped": preview_unescaped,
        "display_json_escaped": render_record(record, preserve_escape=True),
        "display_json_unescaped": render_record(record, preserve_escape=False),
    }


def make_step(step_type: str, role: str | None) -> dict[str, Any]:
    return {
        "step_type": step_type,
        "role": role,
        "entries": [],
        "tool_count": 0,
    }


def build_trace_steps(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    current_assistant_step: dict[str, Any] | None = None

    for record in records:
        role = record.get("role")
        entry = build_entry(record)

        if role == "assistant":
            current_assistant_step = make_step("assistant_bundle", role)
            current_assistant_step["entries"].append(entry)
            steps.append(current_assistant_step)
            continue

        if role == "tool":
            if current_assistant_step is not None:
                current_assistant_step["entries"].append(entry)
                current_assistant_step["tool_count"] += 1
            else:
                orphan_tool_step = make_step("tool_only", role)
                orphan_tool_step["entries"].append(entry)
                steps.append(orphan_tool_step)
            continue

        current_assistant_step = None

        if role == "user":
            step = make_step("user", role)
        elif role is None:
            step = make_step("no_role", None)
        else:
            step = make_step("other_role", role)

        step["entries"].append(entry)
        steps.append(step)

    total_steps = len(steps)
    for index, step in enumerate(steps, start=1):
        step["index"] = index
        step["record_count"] = len(step["entries"])
        step["progress_percent"] = round(index / total_steps * 100, 2) if total_steps else 0

        first_entry = step["entries"][0]
        if step["step_type"] == "assistant_bundle":
            label = f"{index}. assistant"
            if step["tool_count"]:
                label += f" + {step['tool_count']} tool"
        elif step["step_type"] == "user":
            label = f"{index}. user"
        elif step["step_type"] == "no_role":
            label = f"{index}. no role"
        elif step["step_type"] == "tool_only":
            label = f"{index}. tool only"
        else:
            label = f"{index}. {first_entry['title']}"

        step["label"] = label
        step["preview_escaped"] = first_entry["preview_escaped"]
        step["preview_unescaped"] = first_entry["preview_unescaped"]

    return steps


def parse_trace_file(raw_path: str) -> dict[str, Any]:
    jsonl_path = resolve_local_path(raw_path)
    records = load_jsonl_records(jsonl_path)
    steps = build_trace_steps(records)

    return {
        "path": str(jsonl_path),
        "total_records": len(records),
        "total_steps": len(steps),
        "steps": steps,
    }


PAGE_HTML = """<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Nanobot 轨迹查看器</title>
  <style>
    :root {
      --bg: #000000;
      --panel: #ffffff;
      --panel-light: #f3f4f6;
      --line: #111111;
      --text: #111111;
      --muted: #4b5563;
      --user: #2563eb;
      --assistant: #059669;
      --meta: #d97706;
      --tool: #7c3aed;
      --error: #dc2626;
      --white: #ffffff;
      --black: #000000;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--white);
      font-family: Consolas, \"Microsoft YaHei\", monospace;
    }
    .page {
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px;
    }
    h1, h2 { margin-top: 0; }
    .panel {
      background: var(--panel);
      color: var(--text);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      margin-bottom: 18px;
    }
    form {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
    }
    input[type=\"text\"] {
      width: 100%;
      background: var(--white);
      color: var(--text);
      border: 2px solid var(--line);
      border-radius: 10px;
      padding: 12px 14px;
      font-size: 14px;
    }
    button {
      border: 0;
      border-radius: 10px;
      padding: 12px 18px;
      font-size: 14px;
      cursor: pointer;
      color: var(--white);
      background: var(--assistant);
    }
    button:hover { opacity: 0.92; }
    .hint, .stats, .empty, .error, .subtle {
      color: var(--muted);
      font-size: 13px;
    }
    .error {
      color: #7f1d1d;
      background: #fee2e2;
      border: 1px solid #ef4444;
      padding: 12px;
      border-radius: 10px;
      display: none;
      white-space: pre-wrap;
      margin-top: 12px;
    }
    .stats {
      display: flex;
      gap: 18px;
      flex-wrap: wrap;
      margin-top: 10px;
    }
    .toolbar {
      display: grid;
      gap: 14px;
    }
    .toolbar-top {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
      align-items: center;
    }
    .toggle-row {
      display: flex;
      gap: 18px;
      align-items: center;
      flex-wrap: wrap;
    }
    .toggle {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      user-select: none;
    }
    .toggle input {
      width: 16px;
      height: 16px;
    }
    .slider-wrap {
      display: grid;
      gap: 10px;
    }
    .slider-header {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
    }
    .slider-actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .mini-btn {
      padding: 8px 12px;
      font-size: 12px;
      background: var(--black);
      color: var(--white);
    }
    .mini-btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
    input[type=\"range\"] {
      width: 100%;
      accent-color: var(--black);
      cursor: pointer;
    }
    .step-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 6px 10px;
      background: var(--panel-light);
      color: var(--text);
      font-size: 12px;
    }
    .legend {
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
    }
    .legend-item {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: var(--muted);
    }
    .legend-dot {
      width: 10px;
      height: 10px;
      border-radius: 999px;
    }
    .card {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--panel);
      color: var(--text);
      padding: 16px;
    }
    .card.user { border-left: 6px solid var(--user); }
    .card.assistant_bundle { border-left: 6px solid var(--assistant); }
    .card.no_role, .card.other_role { border-left: 6px solid var(--meta); }
    .card.tool_only { border-left: 6px solid var(--tool); }
    .card-header {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }
    .card-title {
      font-size: 18px;
      font-weight: 700;
    }
    .card-meta {
      color: var(--muted);
      font-size: 12px;
    }
    .card-preview {
      color: var(--text);
      background: #f5f5f5;
      border: 1px solid #d4d4d4;
      border-radius: 10px;
      padding: 10px 12px;
      margin-bottom: 12px;
      white-space: pre-wrap;
      word-break: break-word;
    }
    details {
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #fafafa;
      margin-top: 10px;
      overflow: hidden;
    }
    summary {
      cursor: pointer;
      padding: 10px 12px;
      background: #ececec;
      font-weight: 700;
    }
    pre {
      margin: 0;
      padding: 12px;
      white-space: pre-wrap;
      word-break: break-word;
      color: var(--text);
      font-size: 13px;
      line-height: 1.5;
    }
    .floating-nav {
      position: fixed;
      right: 20px;
      bottom: 20px;
      z-index: 999;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .floating-nav button {
      min-width: 108px;
      box-shadow: 0 8px 20px rgba(0, 0, 0, 0.35);
      border: 2px solid var(--white);
      background: var(--black);
      color: var(--white);
    }
    .floating-nav button:hover {
      background: #1f1f1f;
    }
    .floating-nav button:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }
  </style>
</head>
<body>
  <div class=\"page\">
    <h1>Nanobot 轨迹查看器</h1>

    <div class=\"panel\">
      <form id=\"trace-form\">
        <input id=\"path-input\" type=\"text\" placeholder=\"输入本地 jsonl 路径，例如 E:\\teleai\\...\\cli_direct.jsonl\" />
        <button type=\"submit\">解析并展示</button>
      </form>
      <p class=\"hint\">分组规则：user / 无 role 单独一段；tool 自动跟随前一个 assistant。</p>
      <div id=\"error-box\" class=\"error\"></div>
      <div id=\"stats\" class=\"stats\"></div>
    </div>

    <div class=\"panel\">
      <h2>进度条</h2>
      <div class=\"toolbar\">
        <div class=\"toolbar-top\">
          <div class=\"toggle-row\">
            <label class=\"toggle\">
              <input id=\"escape-toggle\" type=\"checkbox\" checked />
              <span>保留字符串转义</span>
            </label>
            <span class=\"subtle\">取消勾选后，\\n / \\t 等会按真实换行、Tab 展示。</span>
          </div>
          <div class=\"legend\">
            <span class=\"legend-item\"><span class=\"legend-dot\" style=\"background:#2563eb;\"></span>user</span>
            <span class=\"legend-item\"><span class=\"legend-dot\" style=\"background:#059669;\"></span>assistant + tool</span>
            <span class=\"legend-item\"><span class=\"legend-dot\" style=\"background:#7c3aed;\"></span>tool only</span>
            <span class=\"legend-item\"><span class=\"legend-dot\" style=\"background:#d97706;\"></span>no role / other</span>
          </div>
        </div>
        <div id=\"slider-wrap\" class=\"slider-wrap\">
          <div class=\"empty\">请先输入 jsonl 路径。</div>
        </div>
      </div>
    </div>

    <div class=\"panel\">
      <h2>当前分段</h2>
      <div id=\"current-step-card\">
        <div class=\"empty\">暂无数据。</div>
      </div>
    </div>
  </div>

  <div class=\"floating-nav\">
    <button id=\"floating-prev-btn\" type=\"button\">上一段</button>
    <button id=\"floating-next-btn\" type=\"button\">下一段</button>
  </div>

  <script>
    const form = document.getElementById('trace-form');
    const pathInput = document.getElementById('path-input');
    const statsNode = document.getElementById('stats');
    const sliderWrapNode = document.getElementById('slider-wrap');
    const currentStepCardNode = document.getElementById('current-step-card');
    const errorBox = document.getElementById('error-box');
    const escapeToggle = document.getElementById('escape-toggle');
    const floatingPrevBtn = document.getElementById('floating-prev-btn');
    const floatingNextBtn = document.getElementById('floating-next-btn');

    let currentTrace = null;
    let currentStepIndex = 0;

    function escapeHtml(text) {
      return String(text)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;');
    }

    function getPreview(step) {
      return escapeToggle.checked ? step.preview_escaped : step.preview_unescaped;
    }

    function getDisplay(entry) {
      return escapeToggle.checked ? entry.display_json_escaped : entry.display_json_unescaped;
    }

    function renderStats(data) {
      statsNode.innerHTML = `
        <span>文件：${escapeHtml(data.path)}</span>
        <span>原始记录：${data.total_records}</span>
        <span>展示分段：${data.total_steps}</span>
      `;
    }

    function updateSliderState() {
      if (!currentTrace || !currentTrace.steps.length) return;

      const current = currentTrace.steps[currentStepIndex];
      const slider = document.getElementById('step-slider');
      const currentLabel = document.getElementById('current-step-label');
      const currentIndex = document.getElementById('current-step-index');
      const prevBtn = document.getElementById('prev-step-btn');
      const nextBtn = document.getElementById('next-step-btn');

      if (slider) slider.value = String(currentStepIndex);
      if (currentLabel) currentLabel.textContent = current.label;
      if (currentIndex) currentIndex.textContent = `${current.index}/${currentTrace.total_steps}`;
      if (prevBtn) prevBtn.disabled = currentStepIndex <= 0;
      if (nextBtn) nextBtn.disabled = currentStepIndex >= currentTrace.steps.length - 1;
      if (floatingPrevBtn) floatingPrevBtn.disabled = currentStepIndex <= 0;
      if (floatingNextBtn) floatingNextBtn.disabled = currentStepIndex >= currentTrace.steps.length - 1;
    }

    function moveStep(offset) {
      if (!currentTrace || !currentTrace.steps.length) return;
      const nextIndex = currentStepIndex + offset;
      if (nextIndex < 0 || nextIndex >= currentTrace.steps.length) return;
      currentStepIndex = nextIndex;
      renderCurrentStep();
      updateSliderState();
      syncUrlState();
    }

    function renderSlider(data) {
      if (!data.steps.length) {
        sliderWrapNode.innerHTML = '<div class="empty">没有可展示的记录。</div>';
        return;
      }

      const current = data.steps[currentStepIndex];
      sliderWrapNode.innerHTML = `
        <div class="slider-header">
          <div class="step-pill">
            <span>当前</span>
            <strong id="current-step-label">${escapeHtml(current.label)}</strong>
            <span id="current-step-index">${current.index}/${data.total_steps}</span>
          </div>
          <div class="slider-actions">
            <button id="prev-step-btn" class="mini-btn" type="button">上一段</button>
            <button id="next-step-btn" class="mini-btn" type="button">下一段</button>
          </div>
        </div>
        <input id="step-slider" type="range" min="0" max="${data.steps.length - 1}" step="1" value="${currentStepIndex}" />
        <div class="subtle">拖动进度条切换分段；当前只展示一组分段详情。</div>
      `;

      const slider = document.getElementById('step-slider');
      const prevBtn = document.getElementById('prev-step-btn');
      const nextBtn = document.getElementById('next-step-btn');

      slider.addEventListener('input', (event) => {
        currentStepIndex = Number(event.target.value);
        renderCurrentStep();
        updateSliderState();
        syncUrlState();
      });

      prevBtn.addEventListener('click', () => moveStep(-1));
      nextBtn.addEventListener('click', () => moveStep(1));

      updateSliderState();
    }

    function renderCurrentStep() {
      if (!currentTrace || !currentTrace.steps.length) {
        currentStepCardNode.innerHTML = '<div class="empty">没有可展示的记录。</div>';
        return;
      }

      const step = currentTrace.steps[currentStepIndex];
      currentStepCardNode.innerHTML = `
        <div class="card ${escapeHtml(step.step_type)}">
          <div class="card-header">
            <div>
              <div class="card-title">${escapeHtml(step.label)}</div>
              <div class="card-meta">record_count=${step.record_count} | progress=${step.progress_percent}%</div>
            </div>
            <div class="card-meta">tool_count=${step.tool_count || 0}</div>
          </div>
          <div class="card-preview">${escapeHtml(getPreview(step))}</div>
          ${step.entries.map((entry, entryIndex) => `
            <details ${entryIndex === 0 ? 'open' : ''}>
              <summary>line ${entry.line_no} · ${escapeHtml(entry.title)}</summary>
              <pre>${escapeHtml(getDisplay(entry))}</pre>
            </details>
          `).join('')}
        </div>
      `;
    }

    function syncUrlState() {
      const url = new URL(window.location.href);
      if (pathInput.value.trim()) {
        url.searchParams.set('path', pathInput.value.trim());
      }
      url.searchParams.set('step', String(currentStepIndex + 1));
      url.searchParams.set('keep_escape', escapeToggle.checked ? '1' : '0');
      window.history.replaceState({}, '', url);
    }

    async function loadTrace(path) {
      errorBox.style.display = 'none';
      errorBox.textContent = '';

      if (!path.trim()) {
        errorBox.style.display = 'block';
        errorBox.textContent = '请输入本地 jsonl 路径。';
        return;
      }

      const response = await fetch(`/api/trace?path=${encodeURIComponent(path)}`);
      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.detail || '解析失败');
      }

      currentTrace = payload;
      const requestedStep = Number(new URL(window.location.href).searchParams.get('step') || '1');
      currentStepIndex = Number.isFinite(requestedStep)
        ? Math.min(Math.max(requestedStep - 1, 0), Math.max(payload.steps.length - 1, 0))
        : 0;

      renderStats(payload);
      renderCurrentStep();
      renderSlider(payload);
      syncUrlState();
    }

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      try {
        currentStepIndex = 0;
        await loadTrace(pathInput.value);
      } catch (error) {
        errorBox.style.display = 'block';
        errorBox.textContent = error.message;
      }
    });

    escapeToggle.addEventListener('change', () => {
      if (!currentTrace) return;
      renderCurrentStep();
      updateSliderState();
      syncUrlState();
    });

    floatingPrevBtn.addEventListener('click', () => moveStep(-1));
    floatingNextBtn.addEventListener('click', () => moveStep(1));

    const url = new URL(window.location.href);
    const initialPath = url.searchParams.get('path') || '';
    const keepEscape = url.searchParams.get('keep_escape');
    if (keepEscape === '0') {
      escapeToggle.checked = false;
    }
    if (initialPath) {
      pathInput.value = initialPath;
      loadTrace(initialPath).catch(error => {
        errorBox.style.display = 'block';
        errorBox.textContent = error.message;
      });
    } else {
      updateSliderState();
    }
  </script>
</body>
</html>
"""


def create_app() -> FastAPI:
    if FASTAPI_IMPORT_ERROR is not None:
        raise RuntimeError("当前环境缺少 fastapi，请先安装：pip install fastapi uvicorn") from FASTAPI_IMPORT_ERROR

    app = FastAPI(title="Nanobot Trace Viewer", version="1.2.0")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return PAGE_HTML

    @app.get("/api/trace")
    async def get_trace(path: str = Query(..., description="本地 jsonl 文件路径")) -> dict[str, Any]:
        try:
            return parse_trace_file(path)
        except (FileNotFoundError, IsADirectoryError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"读取文件失败: {exc}") from exc

    return app


app = create_app() if FASTAPI_IMPORT_ERROR is None else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Nanobot 轨迹 FastAPI 查看器")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--path", help="默认加载的本地 jsonl 路径")
    args = parser.parse_args()

    if FASTAPI_IMPORT_ERROR is not None:
        raise RuntimeError("缺少 fastapi，请先执行: pip install fastapi uvicorn") from FASTAPI_IMPORT_ERROR

    import uvicorn

    target_app = create_app()

    if args.path:
        preview = parse_trace_file(args.path)
        print(f"默认文件可读取: {preview['path']}")
        print(f"原始记录: {preview['total_records']}，展示分段: {preview['total_steps']}")
        print(f"打开页面: http://{args.host}:{args.port}/?path={args.path}")
    else:
        print(f"打开页面: http://{args.host}:{args.port}/")

    uvicorn.run(target_app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
