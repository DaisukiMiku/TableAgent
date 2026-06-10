"""TableClaw tools for uploaded spreadsheet inspection and retrieval."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from nanobot.agent.tools.base import Tool, tool_parameters
from nanobot.agent.tools.schema import BooleanSchema, IntegerSchema, StringSchema, tool_parameters_schema


QUESTION_TERMS = [
    "欠费", "总欠费", "未列收", "已列收", "一年以上", "小微ICT", "ICT",
    "应收", "应收账款", "应收占收比", "预收", "占收比", "同比", "增幅",
    "营业收现率", "营业现金比率", "长账龄", "保证金", "公有池", "私有池",
    "大额长账", "市州", "区县", "全省", "200亿省", "四川", "成都",
    "绵阳", "自贡", "达州", "乐山", "巴中",
]
TABLE_EXTENSIONS = {".xlsx", ".xls", ".csv", ".tsv"}
SCHEMA_CACHE_VERSION = 1
MAX_INDEX_SHEETS = 8
MAX_HEADER_SCAN_ROWS = 12
MAX_PROFILE_ROWS = 120
MAX_PROFILE_COLS = 80


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return re.sub(r"\s+", " ", text)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_date_like(value: Any) -> bool:
    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        return True
    text = _cell_text(value)
    return bool(re.fullmatch(r"20\d{2}[-/.年]?\s*(0?[1-9]|1[0-2])月?", text))


def _dedupe_keep_order(values: list[str], limit: int = 12) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
        if len(result) >= limit:
            break
    return result


def _safe_cache_name(path: Path) -> str:
    digest = hashlib.sha1(str(path.resolve()).encode("utf-8")).hexdigest()[:16]
    return f"{_stable_id(path)}_{digest}.schema.json"


def _resolve_table_path(workspace: Path, path: str) -> Path:
    raw = Path(path).expanduser()
    if raw.is_absolute():
        return raw.resolve()
    candidates = [
        (workspace / raw).resolve(),
        (workspace / "uploads" / raw).resolve(),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _cache_file_for(workspace: Path, path: Path) -> Path:
    return workspace / "table_cache" / _safe_cache_name(path)


def _file_meta(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "size_bytes": stat.st_size,
        "mtime": int(stat.st_mtime),
    }


def _cache_is_fresh(schema: dict[str, Any], path: Path) -> bool:
    try:
        meta = _file_meta(path)
    except FileNotFoundError:
        return False
    return (
        schema.get("cache_version") == SCHEMA_CACHE_VERSION
        and schema.get("size_bytes") == meta["size_bytes"]
        and schema.get("mtime") == meta["mtime"]
    )


def _sheet_text_blob(sheet_schema: dict[str, Any]) -> str:
    parts: list[str] = [sheet_schema.get("sheet", "")]
    for row in sheet_schema.get("header_candidates", []):
        parts.extend(row.get("values", []))
    for column in sheet_schema.get("columns", []):
        parts.extend(column.get("header_values", []))
        parts.extend(column.get("sample_values", []))
    for row in sheet_schema.get("sample_rows", []):
        parts.extend(row)
    return " ".join(part for part in parts if part)


def _table_text_blob(schema: dict[str, Any]) -> str:
    parts = [schema.get("filename", ""), schema.get("suffix", "")]
    for sheet in schema.get("sheets", []):
        parts.append(_sheet_text_blob(sheet))
    return " ".join(part for part in parts if part)


def _iter_tables(upload_dir: Path) -> list[Path]:
    if not upload_dir.exists():
        return []
    files = []
    for path in upload_dir.iterdir():
        if (
            path.is_file()
            and not path.name.startswith(("~$", "."))
            and path.suffix.lower() in TABLE_EXTENSIONS
        ):
            files.append(path)
    return sorted(files, key=lambda item: item.name)


def _stable_id(path: Path) -> str:
    import hashlib

    return "tbl_" + hashlib.sha1(path.name.encode("utf-8")).hexdigest()[:10]


def _infer_scope(filename: str) -> str:
    if "区县" in filename:
        return "county"
    if "市州" in filename:
        return "city"
    if "全国各省份" in filename or "200亿省" in filename:
        return "province"
    return "unknown"


def _infer_subject(filename: str) -> str:
    subjects = [
        "欠费", "通报应收总额", "应收账款", "营业收现率", "营业现金比率",
        "长账龄", "保证金", "公有池", "私有池", "大额长账",
    ]
    return ",".join(term for term in subjects if term in filename) or "unknown"


def _extract_filename_month(filename: str) -> str | None:
    match = re.search(r"(20\d{2})(0[1-9]|1[0-2])", filename)
    return match.group(0) if match else None


def _classify_columns(
    rows: list[list[Any]],
    header_rows: list[int],
    *,
    max_cols: int,
    max_profile_rows: int = MAX_PROFILE_ROWS,
) -> list[dict[str, Any]]:
    columns: list[dict[str, Any]] = []
    for col_index in range(max_cols):
        header_values: list[str] = []
        for row_number in header_rows:
            if 1 <= row_number <= len(rows):
                header_values.append(_cell_text(rows[row_number - 1][col_index] if col_index < len(rows[row_number - 1]) else None))
        sample_values: list[str] = []
        non_empty = 0
        numeric = 0
        date_like = 0
        for row in rows[max(header_rows or [0]): max_profile_rows]:
            value = row[col_index] if col_index < len(row) else None
            text = _cell_text(value)
            if not text:
                continue
            non_empty += 1
            if _is_number(value):
                numeric += 1
            if _is_date_like(value):
                date_like += 1
            sample_values.append(text)
        column_type = "empty"
        if non_empty:
            if numeric / non_empty >= 0.7:
                column_type = "numeric"
            elif date_like / non_empty >= 0.5:
                column_type = "date"
            else:
                column_type = "text"
        columns.append(
            {
                "index": col_index + 1,
                "letter": _column_letter(col_index + 1),
                "header_values": _dedupe_keep_order(header_values, limit=6),
                "sample_values": _dedupe_keep_order(sample_values, limit=6),
                "non_empty_count": non_empty,
                "numeric_count": numeric,
                "date_like_count": date_like,
                "inferred_type": column_type,
            }
        )
    return columns


def _column_letter(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _detect_header_candidates(rows: list[list[Any]], max_cols: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows[:MAX_HEADER_SCAN_ROWS], start=1):
        values = [_cell_text(value) for value in row[:max_cols]]
        non_empty_values = [value for value in values if value]
        if not non_empty_values:
            continue
        numeric_count = sum(1 for value in row[:max_cols] if _is_number(value) and not _is_date_like(value))
        density = round(len(non_empty_values) / max(max_cols, 1), 3)
        numeric_ratio = round(numeric_count / max(len(non_empty_values), 1), 3)
        score = len(non_empty_values) * (1 - numeric_ratio)
        candidates.append(
            {
                "row": row_number,
                "values": _dedupe_keep_order(non_empty_values, limit=24),
                "non_empty_count": len(non_empty_values),
                "density": density,
                "numeric_ratio": numeric_ratio,
                "score": round(score, 2),
            }
        )
    candidates.sort(key=lambda item: (-item["score"], item["row"]))
    return candidates[:5]


def _select_header_rows(candidates: list[dict[str, Any]]) -> list[int]:
    text_like = [item for item in candidates if item.get("numeric_ratio", 0) < 0.5]
    selected = text_like[:3] or candidates[:2]
    return sorted(item["row"] for item in selected)


def _sample_rows(rows: list[list[Any]], start_row: int, max_cols: int, limit: int = 8) -> list[list[str]]:
    samples: list[list[str]] = []
    for row in rows[max(start_row - 1, 0):]:
        values = [_cell_text(value) for value in row[:max_cols]]
        compact = [value for value in values if value]
        if compact:
            samples.append(compact[:max_cols])
        if len(samples) >= limit:
            break
    return samples


def _inspect_xlsx(path: Path, *, sheet_filter: str | None = None) -> dict[str, Any]:
    workbook = load_workbook(path, read_only=False, data_only=True)
    try:
        sheet_names = [sheet_filter] if sheet_filter else workbook.sheetnames[:MAX_INDEX_SHEETS]
        sheets: list[dict[str, Any]] = []
        for sheet_name in sheet_names:
            if sheet_name not in workbook.sheetnames:
                continue
            sheet = workbook[sheet_name]
            max_row = sheet.max_row or 0
            max_column = min(sheet.max_column or 0, MAX_PROFILE_COLS)
            rows: list[list[Any]] = []
            for row in sheet.iter_rows(
                min_row=1,
                max_row=min(max_row, MAX_PROFILE_ROWS),
                max_col=max_column,
                values_only=True,
            ):
                rows.append(list(row))
            header_candidates = _detect_header_candidates(rows, max_column)
            header_rows = _select_header_rows(header_candidates)
            data_start_row = max(header_rows or [1]) + 1
            merged_ranges = [str(rng) for rng in list(sheet.merged_cells.ranges)[:80]]
            sheets.append(
                {
                    "sheet": sheet_name,
                    "max_row": max_row,
                    "max_column": sheet.max_column or 0,
                    "merged_ranges": merged_ranges,
                    "header_candidates": header_candidates,
                    "columns": _classify_columns(rows, header_rows, max_cols=max_column),
                    "sample_rows": _sample_rows(rows, data_start_row, max_column),
                }
            )
    finally:
        workbook.close()
    return _schema_payload(path, sheets)


def _inspect_csv(path: Path, *, delimiter: str | None = None) -> dict[str, Any]:
    if delimiter is None:
        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    rows: list[list[str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        for row in reader:
            rows.append(row)
            if len(rows) >= MAX_PROFILE_ROWS:
                break
    max_cols = min(max((len(row) for row in rows), default=0), MAX_PROFILE_COLS)
    header_candidates = _detect_header_candidates(rows, max_cols)
    header_rows = _select_header_rows(header_candidates)
    sheets = [
        {
            "sheet": path.stem,
            "max_row": len(rows),
            "max_column": max_cols,
            "merged_ranges": [],
            "header_candidates": header_candidates,
            "columns": _classify_columns(rows, header_rows, max_cols=max_cols),
            "sample_rows": _sample_rows(rows, max(header_rows or [1]) + 1, max_cols),
        }
    ]
    return _schema_payload(path, sheets)


def _schema_payload(path: Path, sheets: list[dict[str, Any]]) -> dict[str, Any]:
    meta = _file_meta(path)
    return {
        "cache_version": SCHEMA_CACHE_VERSION,
        "table_id": _stable_id(path),
        "filename": path.name,
        "path": str(path),
        "suffix": path.suffix.lower(),
        "size_bytes": meta["size_bytes"],
        "mtime": meta["mtime"],
        "scope": _infer_scope(path.name),
        "subject": _infer_subject(path.name),
        "month": _extract_filename_month(path.name),
        "sheets": sheets,
    }


def _inspect_table(path: Path, *, sheet: str | None = None) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        return _inspect_xlsx(path, sheet_filter=sheet)
    if suffix in {".csv", ".tsv"}:
        return _inspect_csv(path)
    raise ValueError(f"Unsupported table file extension: {suffix}")


def _load_or_build_schema(
    workspace: Path,
    path: Path,
    *,
    sheet: str | None = None,
    rebuild_cache: bool = False,
) -> dict[str, Any]:
    cache_file = _cache_file_for(workspace, path)
    if not rebuild_cache and sheet is None and cache_file.exists():
        try:
            schema = json.loads(cache_file.read_text(encoding="utf-8"))
            if _cache_is_fresh(schema, path):
                return {**schema, "cache_file": str(cache_file), "cache_hit": True}
        except json.JSONDecodeError:
            pass
    schema = _inspect_table(path, sheet=sheet)
    if sheet is None:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**schema, "cache_file": str(cache_file), "cache_hit": False}


def _read_preview(path: Path, *, max_sheets: int = 2, max_rows: int = 8, max_cols: int = 12) -> list[dict[str, Any]]:
    if path.suffix.lower() not in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        return []
    previews: list[dict[str, Any]] = []
    try:
        workbook = load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:
        return [{"error": str(exc)}]
    try:
        for sheet_name in workbook.sheetnames[:max_sheets]:
            sheet = workbook[sheet_name]
            rows: list[list[str]] = []
            for row in sheet.iter_rows(
                min_row=1,
                max_row=min(max_rows, sheet.max_row or max_rows),
                max_col=min(max_cols, sheet.max_column or max_cols),
                values_only=True,
            ):
                values = [str(value).strip() for value in row if value not in (None, "")]
                if values:
                    rows.append(values)
            preview_text = " ".join(" ".join(row) for row in rows)
            previews.append(
                {
                    "sheet": sheet_name,
                    "max_row": sheet.max_row,
                    "max_column": sheet.max_column,
                    "preview_text": preview_text[:1600],
                }
            )
    finally:
        workbook.close()
    return previews


def _build_index(upload_dir: Path, index_file: Path, workspace: Path) -> list[dict[str, Any]]:
    index_file.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for path in _iter_tables(upload_dir):
        try:
            schema = _load_or_build_schema(workspace, path)
        except Exception as exc:
            records.append(
                {
                    "table_id": _stable_id(path),
                    "filename": path.name,
                    "path": str(path),
                    "suffix": path.suffix.lower(),
                    "size_bytes": path.stat().st_size,
                    "mtime": int(path.stat().st_mtime),
                    "scope": _infer_scope(path.name),
                    "subject": _infer_subject(path.name),
                    "month": _extract_filename_month(path.name),
                    "schema_cache": None,
                    "sheets": [],
                    "keywords": sorted(set(term for term in QUESTION_TERMS if term in path.name)),
                    "index_error": str(exc),
                }
            )
            continue
        schema_text = _table_text_blob(schema)
        sheet_summaries = []
        for sheet in schema.get("sheets", [])[:MAX_INDEX_SHEETS]:
            preview_text = _sheet_text_blob(sheet)
            sheet_summaries.append(
                {
                    "sheet": sheet.get("sheet"),
                    "max_row": sheet.get("max_row"),
                    "max_column": sheet.get("max_column"),
                    "header_candidates": sheet.get("header_candidates", [])[:3],
                    "columns": [
                        {
                            "index": column.get("index"),
                            "letter": column.get("letter"),
                            "header_values": column.get("header_values", []),
                            "sample_values": column.get("sample_values", [])[:3],
                            "inferred_type": column.get("inferred_type"),
                        }
                        for column in sheet.get("columns", [])[:40]
                    ],
                    "preview_text": preview_text[:1600],
                }
            )
        records.append(
            {
                "table_id": _stable_id(path),
                "filename": path.name,
                "path": str(path),
                "suffix": path.suffix.lower(),
                "size_bytes": path.stat().st_size,
                "mtime": int(path.stat().st_mtime),
                "scope": _infer_scope(path.name),
                "subject": _infer_subject(path.name),
                "month": _extract_filename_month(path.name),
                "schema_cache": schema.get("cache_file"),
                "sheets": sheet_summaries,
                "keywords": sorted(set(term for term in QUESTION_TERMS if term in path.name or term in schema_text)),
            }
        )
    index_file.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    return records


def _load_index(index_file: Path) -> list[dict[str, Any]]:
    if not index_file.exists():
        return []
    return [json.loads(line) for line in index_file.read_text(encoding="utf-8").splitlines() if line.strip()]


def _question_months(question: str) -> list[str]:
    months: set[str] = set()
    for year, start, end in re.findall(r"(20\d{2})年\s*(\d{1,2})\s*[-至到]\s*(\d{1,2})月", question):
        for month in range(int(start), int(end) + 1):
            if 1 <= month <= 12:
                months.add(f"{year}{month:02d}")
    for year, month in re.findall(r"(20\d{2})年\s*(\d{1,2})月", question):
        months.add(f"{year}{int(month):02d}")
    for raw in re.findall(r"20\d{2}(?:0[1-9]|1[0-2])", question):
        months.add(raw)
    return sorted(months)


def _question_terms(question: str) -> list[str]:
    terms = [term for term in QUESTION_TERMS if term.lower() in question.lower()]
    for chunk in re.findall(r"[\u4e00-\u9fff]{2,}", question):
        max_len = min(len(chunk), 10)
        for size in range(max_len, 1, -1):
            for start in range(0, len(chunk) - size + 1):
                token = chunk[start:start + size]
                if len(token) >= 2:
                    terms.append(token)
    for token in re.findall(r"[A-Za-z0-9]+", question):
        if len(token) >= 2 and not token.isdigit():
            terms.append(token)
    return sorted(set(terms), key=lambda item: (-len(item), item))


def _score_record(question: str, record: dict[str, Any]) -> tuple[float, list[str]]:
    filename = record["filename"]
    subject = record.get("subject") or ""
    scope = record.get("scope") or ""
    keywords = set(record.get("keywords") or [])
    preview_text = " ".join(item.get("preview_text", "") for item in record.get("sheets") or [])
    header_text = " ".join(
        " ".join(column.get("header_values", []) + column.get("sample_values", []))
        for sheet in record.get("sheets") or []
        for column in sheet.get("columns", [])
    )
    sheet_text = " ".join(sheet.get("sheet", "") for sheet in record.get("sheets") or [])
    haystack = f"{filename} {subject} {scope} {sheet_text} {' '.join(keywords)} {header_text} {preview_text}"
    terms = _question_terms(question)
    months = _question_months(question)
    score = 0.0
    reasons: list[str] = []

    for term in terms:
        if term in filename:
            score += 8
            reasons.append(f"filename:{term}")
        elif term in subject:
            score += 5
            reasons.append(f"subject:{term}")
        elif term in keywords:
            score += 4
            reasons.append(f"keyword:{term}")
        elif term in preview_text:
            score += 2
            reasons.append(f"preview:{term}")
        elif term in header_text:
            score += 3
            reasons.append(f"schema:{term}")
        elif term in sheet_text:
            score += 3
            reasons.append(f"sheet:{term}")

    if months:
        if record.get("month") in months:
            score += 10
            reasons.append(f"month:{record['month']}")
        elif any(month in haystack for month in months):
            score += 8
            reasons.append("schema-month")
        elif any(month[:4] in filename for month in months):
            score += 2
            reasons.append("year-match")
        elif not record.get("month") and any(term in haystack for term in ("欠费", "应收", "长账龄")):
            score += 8
            reasons.append("year-series-ledger")
    if "欠费" in question and "欠费" in haystack:
        score += 18
        reasons.append("domain:arrears")
    if "小微ICT" in question and ("小微ICT" in haystack or "小微" in haystack or "ICT" in haystack):
        score += 8
        reasons.append("domain:ict")
    if ("应收" in question or "预收" in question or "占收比" in question) and any(
        term in haystack for term in ("应收", "预收", "占收比", "通报应收总额")
    ):
        score += 12
        reasons.append("domain:receivable")
    if "一年以上" in question and any(term in haystack for term in ("一年以上", "长账龄", "欠费")):
        score += 10
        reasons.append("domain:aging")
    if "全省" in question or "200亿省" in question:
        if scope == "province":
            score += 6
            reasons.append("scope:province")
        if "全国各省份" in filename:
            score += 4
            reasons.append("filename:province")
    if "市州" in question and scope == "city":
        score += 6
        reasons.append("scope:city")
    if "区县" in question and scope == "county":
        score += 6
        reasons.append("scope:county")
    if ("画" in question or "图" in question) and any(term in haystack for term in ("欠费", "应收", "营业", "长账龄")):
        score += 1
        reasons.append("chart-compatible")
    return score, reasons[:10]


def _retrieve(question: str, index: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    scored = []
    for record in index:
        score, reasons = _score_record(question, record)
        if score > 0:
            scored.append({**record, "score": round(score, 2), "reasons": reasons})
    scored.sort(key=lambda item: (-item["score"], item["filename"]))
    return scored[:top_k]


@tool_parameters(
    tool_parameters_schema(
        path=StringSchema("Uploaded spreadsheet path. Can be absolute, workspace-relative, or just a filename under workspace/uploads."),
        sheet=StringSchema("Optional sheet name to inspect. Leave empty to inspect the workbook summary.", nullable=True),
        rebuild_cache=BooleanSchema(description="Rebuild schema cache even if the file has not changed.", default=False),
        required=["path"],
    )
)
class TableClawInspectTool(Tool):
    """Inspect an uploaded spreadsheet and cache its schema."""

    def __init__(self, workspace: Path | None = None):
        self._workspace = Path(workspace or ".").resolve()

    @classmethod
    def create(cls, ctx: Any) -> Tool:
        return cls(workspace=Path(ctx.workspace))

    @property
    def name(self) -> str:
        return "tableclaw_inspect"

    @property
    def description(self) -> str:
        return (
            "Inspect a spreadsheet file and return a reusable schema summary: sheets, dimensions, merged ranges, "
            "candidate header rows, column headers, inferred column types, and sample rows. Use this before writing "
            "custom openpyxl/pandas code, especially after tableclaw_retrieve_tables returns candidate paths. "
            "The schema is cached in workspace/table_cache and reused until file size or mtime changes."
        )

    async def execute(self, path: str, sheet: str | None = None, rebuild_cache: bool = False, **_: Any) -> str:
        table_path = _resolve_table_path(self._workspace, path)
        if not table_path.exists():
            return f"Error: table file not found: {table_path}"
        schema = _load_or_build_schema(
            self._workspace,
            table_path,
            sheet=sheet or None,
            rebuild_cache=rebuild_cache,
        )
        compact_schema = {
            "cache_version": schema.get("cache_version"),
            "cache_hit": schema.get("cache_hit"),
            "cache_file": schema.get("cache_file"),
            "table_id": schema.get("table_id"),
            "filename": schema.get("filename"),
            "path": schema.get("path"),
            "suffix": schema.get("suffix"),
            "size_bytes": schema.get("size_bytes"),
            "mtime": schema.get("mtime"),
            "scope": schema.get("scope"),
            "subject": schema.get("subject"),
            "month": schema.get("month"),
            "sheets": [
                {
                    "sheet": item.get("sheet"),
                    "max_row": item.get("max_row"),
                    "max_column": item.get("max_column"),
                    "merged_ranges": item.get("merged_ranges", [])[:20],
                    "header_candidates": item.get("header_candidates", [])[:5],
                    "columns": item.get("columns", [])[:60],
                    "sample_rows": item.get("sample_rows", [])[:8],
                }
                for item in schema.get("sheets", [])
            ],
            "next_step": (
                "Use the sheet/header/column candidates here to choose exact ranges or write a short deterministic "
                "calculation. Avoid read_file on .xlsx binaries."
            ),
        }
        return json.dumps(compact_schema, ensure_ascii=False, indent=2)


@tool_parameters(
    tool_parameters_schema(
        query=StringSchema("Full user question, including dates, metrics, units, and scope."),
        top_k=IntegerSchema(8, description="Maximum uploaded table candidates to return.", minimum=1, maximum=20),
        rebuild_index=BooleanSchema(description="Rebuild the workspace table index from uploads before retrieval.", default=False),
        required=["query"],
    )
)
class TableClawRetrieveTablesTool(Tool):
    """Retrieve uploaded spreadsheet candidates from the TableClaw workspace."""

    def __init__(self, workspace: Path | None = None):
        self._workspace = Path(workspace or ".").resolve()

    @classmethod
    def create(cls, ctx: Any) -> Tool:
        return cls(workspace=Path(ctx.workspace))

    @property
    def name(self) -> str:
        return "tableclaw_retrieve_tables"

    @property
    def description(self) -> str:
        return (
            "Retrieve likely relevant uploaded spreadsheet files from workspace/uploads. "
            "Use this first when the user asks about tables/spreadsheets but does not provide an exact file path, "
            "or when multiple uploaded tables may be relevant. It returns candidate file paths plus scope, subject, "
            "month, sheet/schema previews, scores, and match reasons; it does not read full spreadsheet contents. "
            "After retrieval, call tableclaw_inspect on the most relevant candidate before writing spreadsheet code."
        )

    @property
    def read_only(self) -> bool:
        return True

    async def execute(self, query: str, top_k: int = 8, rebuild_index: bool = False, **_: Any) -> str:
        upload_dir = self._workspace / "uploads"
        index_file = self._workspace / "table_index" / "tables.jsonl"
        if rebuild_index or not index_file.exists():
            index = _build_index(upload_dir, index_file, self._workspace)
        else:
            index = _load_index(index_file) or _build_index(upload_dir, index_file, self._workspace)

        candidates = _retrieve(query, index, top_k=top_k)
        compact_candidates = []
        for rank, item in enumerate(candidates, start=1):
            compact_candidates.append(
                {
                    "rank": rank,
                    "table_id": item["table_id"],
                    "filename": item["filename"],
                    "path": item["path"],
                    "score": item["score"],
                    "scope": item.get("scope"),
                    "subject": item.get("subject"),
                    "month": item.get("month"),
                    "keywords": item.get("keywords"),
                    "reasons": item.get("reasons"),
                    "sheets": [
                        {
                            "sheet": sheet.get("sheet"),
                            "max_row": sheet.get("max_row"),
                            "max_column": sheet.get("max_column"),
                            "header_candidates": sheet.get("header_candidates", [])[:2],
                            "preview_text": sheet.get("preview_text", "")[:360],
                        }
                        for sheet in item.get("sheets", [])[:2]
                    ],
                }
            )
        return json.dumps(
            {
                "query": query,
                "workspace": str(self._workspace),
                "upload_dir": str(upload_dir),
                "index_file": str(index_file),
                "indexed_tables": len(index),
                "top_k": top_k,
                "candidates": compact_candidates,
                "next_step": "Choose relevant candidate path(s), call tableclaw_inspect for schema details, then compute the answer with spreadsheet skills/tools.",
            },
            ensure_ascii=False,
            indent=2,
        )
