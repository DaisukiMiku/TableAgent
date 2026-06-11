"""TableClaw tools for uploaded spreadsheet inspection and retrieval."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from nanobot.agent.tools.base import Tool, tool_parameters
from nanobot.agent.tools.schema import (
    ArraySchema,
    BooleanSchema,
    IntegerSchema,
    NumberSchema,
    ObjectSchema,
    StringSchema,
    tool_parameters_schema,
)


QUESTION_TERMS = [
    "欠费", "总欠费", "未列收", "已列收", "一年以上", "小微ICT", "ICT",
    "应收", "应收账款", "应收占收比", "预收", "占收比", "同比", "增幅",
    "营业收现率", "营业现金比率", "长账龄", "保证金", "公有池", "私有池",
    "大额长账", "市州", "区县", "全省", "200亿省", "四川", "成都",
    "绵阳", "自贡", "达州", "乐山", "巴中",
]
TABLE_EXTENSIONS = {".xlsx", ".xls", ".csv", ".tsv"}
SCHEMA_CACHE_VERSION = 1
TABLE_CATALOG_VERSION = 1
MAX_INDEX_SHEETS = 8
MAX_HEADER_SCAN_ROWS = 12
MAX_PROFILE_ROWS = 120
MAX_PROFILE_COLS = 80
DEFAULT_CATALOG_MODEL = "deepseek-v4-pro"
DEFAULT_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


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


def _normalize_match_text(value: Any) -> str:
    text = _cell_text(value).lower()
    return re.sub(r"[\s　,，。；;:：/\\|()（）【】\[\]{}<>《》\"'`._-]+", "", text)


def _contains_loose(haystack: Any, needle: Any) -> bool:
    needle_text = _normalize_match_text(needle)
    if not needle_text:
        return True
    return needle_text in _normalize_match_text(haystack)


def _parse_boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "是", "升序", "asc", "ascending"}


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = _cell_text(value).replace(",", "").replace("，", "")
    if not text:
        return None
    percent = text.endswith("%")
    if percent:
        text = text[:-1]
    try:
        number = float(text)
    except ValueError:
        return None
    return number / 100.0 if percent else number


def _parse_column_reference(reference: Any) -> int | None:
    if reference is None:
        return None
    if isinstance(reference, int):
        return reference if reference > 0 else None
    text = _cell_text(reference)
    if not text:
        return None
    if text.isdigit():
        return int(text)
    if re.fullmatch(r"[A-Za-z]+", text):
        value = 0
        for char in text.upper():
            value = value * 26 + ord(char) - 64
        return value
    return None


def _parse_periods(periods: str | None, start: str | None = None, end: str | None = None) -> list[str]:
    found: set[str] = set()
    raw = " ".join(part for part in [periods, start, end] if part)
    for year, start_month, end_month in re.findall(r"(20\d{2})年?\s*(\d{1,2})\s*[-至到]\s*(\d{1,2})月?", raw):
        for month in range(int(start_month), int(end_month) + 1):
            if 1 <= month <= 12:
                found.add(f"{year}{month:02d}")
    for year, month in re.findall(r"(20\d{2})年?\s*(\d{1,2})月?", raw):
        if 1 <= int(month) <= 12:
            found.add(f"{year}{int(month):02d}")
    for token in re.findall(r"20\d{2}(?:0[1-9]|1[0-2])", raw):
        found.add(token)
    if start and end:
        start_match = re.fullmatch(r"(20\d{2})(0[1-9]|1[0-2])", start)
        end_match = re.fullmatch(r"(20\d{2})(0[1-9]|1[0-2])", end)
        if start_match and end_match:
            current_year, current_month = int(start[:4]), int(start[4:])
            end_year, end_month = int(end[:4]), int(end[4:])
            while (current_year, current_month) <= (end_year, end_month):
                found.add(f"{current_year}{current_month:02d}")
                current_month += 1
                if current_month > 12:
                    current_year += 1
                    current_month = 1
    return sorted(found)


def _json_response(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


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


def _sheet_names(schema: dict[str, Any]) -> list[str]:
    return [sheet.get("sheet") for sheet in schema.get("sheets", []) if sheet.get("sheet")]


def _choose_sheet(schema: dict[str, Any], sheet: str | None = None) -> str | None:
    names = _sheet_names(schema)
    if sheet:
        for name in names:
            if name == sheet or _contains_loose(name, sheet):
                return name
        return sheet
    return names[0] if names else None


def _load_sheet_matrix(path: Path, sheet_name: str | None = None) -> tuple[str, list[list[Any]], int, int]:
    workbook = load_workbook(path, read_only=False, data_only=True)
    try:
        selected = sheet_name if sheet_name in workbook.sheetnames else workbook.sheetnames[0]
        sheet = workbook[selected]
        max_row = sheet.max_row or 0
        max_col = sheet.max_column or 0
        rows: list[list[Any]] = []
        for row in sheet.iter_rows(min_row=1, max_row=max_row, max_col=max_col, values_only=True):
            rows.append(list(row))
        for merged in sheet.merged_cells.ranges:
            min_col, min_row, max_col_m, max_row_m = merged.bounds
            top_value = rows[min_row - 1][min_col - 1] if min_row - 1 < len(rows) and min_col - 1 < len(rows[min_row - 1]) else None
            if top_value in (None, ""):
                continue
            for row_index in range(min_row - 1, min(max_row_m, len(rows))):
                row = rows[row_index]
                for col_index in range(min_col - 1, min(max_col_m, len(row))):
                    if row[col_index] in (None, ""):
                        row[col_index] = top_value
        return selected, rows, max_row, max_col
    finally:
        workbook.close()


def _header_rows_from_matrix(rows: list[list[Any]], max_col: int) -> list[int]:
    candidates = _detect_header_candidates(rows[:MAX_HEADER_SCAN_ROWS], min(max_col, MAX_PROFILE_COLS))
    selected = _select_header_rows(candidates)
    if not selected:
        return [1]
    top = max(selected)
    # Include adjacent early header rows because spreadsheet period/metric headers are often split over 2-3 rows.
    expanded = [
        row_number
        for row_number in range(1, min(top + 1, MAX_HEADER_SCAN_ROWS + 1))
        if any(_cell_text(value) for value in rows[row_number - 1][:max_col])
    ]
    return expanded or selected


def _column_descriptors(rows: list[list[Any]], header_rows: list[int], max_col: int) -> list[dict[str, Any]]:
    descriptors: list[dict[str, Any]] = []
    for col_index in range(1, max_col + 1):
        header_values = []
        for row_number in header_rows:
            value = rows[row_number - 1][col_index - 1] if row_number - 1 < len(rows) and col_index - 1 < len(rows[row_number - 1]) else None
            header_values.append(_cell_text(value))
        header_values = _dedupe_keep_order(header_values, limit=8)
        descriptor = " ".join(header_values)
        descriptors.append(
            {
                "index": col_index,
                "letter": _column_letter(col_index),
                "header_values": header_values,
                "descriptor": descriptor,
                "normalized": _normalize_match_text(descriptor),
            }
        )
    return descriptors


def _locate_column_in_matrix(
    rows: list[list[Any]],
    *,
    max_col: int,
    header_rows: list[int],
    reference: str | int | None = None,
    metric: str | None = None,
    period: str | None = None,
    group: str | None = None,
) -> dict[str, Any] | None:
    parsed = _parse_column_reference(reference)
    descriptors = _column_descriptors(rows, header_rows, max_col)
    if parsed and 1 <= parsed <= max_col:
        item = descriptors[parsed - 1]
        return {**item, "score": 999, "reasons": ["explicit-column"]}

    metric_norm = _normalize_match_text(metric)
    period_norm = _normalize_match_text(period)
    group_norm = _normalize_match_text(group)
    best: dict[str, Any] | None = None
    for item in descriptors:
        text = item["normalized"]
        score = 0
        reasons: list[str] = []
        if metric_norm:
            if metric_norm in text:
                score += 20
                reasons.append(f"metric:{metric}")
            else:
                metric_parts = [part for part in re.split(r"[/,，、\s]+", metric or "") if part]
                part_hits = sum(1 for part in metric_parts if _normalize_match_text(part) in text)
                if part_hits:
                    score += 4 * part_hits
                    reasons.append(f"metric-parts:{part_hits}")
        if period_norm and period_norm in text:
            score += 16
            reasons.append(f"period:{period}")
        if group_norm and group_norm in text:
            score += 6
            reasons.append(f"group:{group}")
        if not metric_norm and not period_norm and not group_norm and reference:
            if _contains_loose(item["descriptor"], reference):
                score += 10
                reasons.append(f"name:{reference}")
        if score and (best is None or score > best["score"]):
            best = {**item, "score": score, "reasons": reasons}
    return best


def _locate_row(
    rows: list[list[Any]],
    *,
    data_start_row: int,
    entity: str | None = None,
    entity_col: str | int | None = None,
    exclude_contains: str | None = None,
) -> list[dict[str, Any]]:
    entity_col_index = _parse_column_reference(entity_col)
    matches: list[dict[str, Any]] = []
    exclude_terms = [term.strip() for term in (exclude_contains or "").split(",") if term.strip()]
    for row_number in range(max(data_start_row, 1), len(rows) + 1):
        row = rows[row_number - 1]
        row_text = " ".join(_cell_text(value) for value in row if _cell_text(value))
        if not row_text:
            continue
        if any(_contains_loose(row_text, term) for term in exclude_terms):
            continue
        if entity:
            if entity_col_index:
                value = row[entity_col_index - 1] if entity_col_index - 1 < len(row) else None
                if not _contains_loose(value, entity):
                    continue
            elif not _contains_loose(row_text, entity):
                continue
        matches.append({"row": row_number, "row_text": row_text[:500]})
    return matches


def _cell_value(rows: list[list[Any]], row: int, col: int) -> Any:
    if row < 1 or col < 1 or row > len(rows):
        return None
    data_row = rows[row - 1]
    if col > len(data_row):
        return None
    return data_row[col - 1]


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


def _catalog_dir(workspace: Path) -> Path:
    return workspace / "table_catalog"


def _catalog_file(workspace: Path) -> Path:
    return _catalog_dir(workspace) / "catalog.jsonl"


def _profile_file_for(workspace: Path, path: Path) -> Path:
    return _catalog_dir(workspace) / "profiles" / f"{_safe_cache_name(path).removesuffix('.schema.json')}.profile.json"


def _description_file_for(workspace: Path, path: Path) -> Path:
    return _catalog_dir(workspace) / "descriptions" / f"{_safe_cache_name(path).removesuffix('.schema.json')}.description.json"


def _clean_view_file_for(workspace: Path, path: Path) -> Path:
    return _catalog_dir(workspace) / "clean_views" / f"{_safe_cache_name(path).removesuffix('.schema.json')}.clean_view.json"


def _json_file_is_fresh(path: Path, source: Path, *, version_key: str, version: int) -> bool:
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    meta = _file_meta(source)
    return (
        payload.get(version_key) == version
        and payload.get("size_bytes") == meta["size_bytes"]
        and payload.get("mtime") == meta["mtime"]
    )


def _infer_column_unit(text: str) -> str | None:
    for unit in ("亿元", "万元", "元", "%", "PP", "pp", "户", "笔", "个"):
        if unit in text:
            return "PP" if unit.lower() == "pp" else unit
    if any(term in text for term in ("占比", "占收比", "同比", "增幅", "增长率", "比例")):
        return "%"
    return None


def _infer_value_type(text: str, inferred_type: str | None = None) -> str:
    normalized = _normalize_match_text(text)
    if any(term in normalized for term in ("排名", "名次", "rank")):
        return "rank"
    if any(term in normalized for term in ("同比", "环比", "增幅", "增量", "增长率")):
        return "change"
    if any(term in normalized for term in ("占比", "占收比", "比例", "率")):
        return "ratio"
    if any(term in normalized for term in ("金额", "总额", "收入", "欠费", "应收", "预收", "成本", "利润")):
        return "amount"
    return inferred_type or "unknown"


def _compact_column_name(column: dict[str, Any]) -> str:
    return " ".join(column.get("header_values", [])).strip() or column.get("letter", "")


def _important_columns(sheet: dict[str, Any], *, limit: int = 80) -> list[dict[str, Any]]:
    columns: list[dict[str, Any]] = []
    for column in sheet.get("columns", [])[:limit]:
        name = _compact_column_name(column)
        if not name:
            continue
        columns.append(
            {
                "index": column.get("index"),
                "letter": column.get("letter"),
                "name": name,
                "unit": _infer_column_unit(name),
                "value_type": _infer_value_type(name, column.get("inferred_type")),
                "inferred_type": column.get("inferred_type"),
                "sample_values": column.get("sample_values", [])[:5],
            }
        )
    return columns


def _likely_entity_columns(sheet: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for column in sheet.get("columns", [])[:40]:
        name = _compact_column_name(column)
        text = _normalize_match_text(name)
        if any(term in text for term in ("单位", "省份", "城市", "市州", "区县", "客户", "供应商", "产品", "名称", "区域")):
            result.append(
                {
                    "index": column.get("index"),
                    "letter": column.get("letter"),
                    "name": name,
                    "sample_values": column.get("sample_values", [])[:8],
                }
            )
    return result[:5]


def _detect_title_rows(sheet: dict[str, Any], header_rows: list[int]) -> list[int]:
    if not header_rows:
        return []
    first_header = min(header_rows)
    return [
        item.get("row")
        for item in sheet.get("header_candidates", [])
        if isinstance(item.get("row"), int) and item["row"] < first_header
    ][:5]


def _build_clean_view(schema: dict[str, Any]) -> dict[str, Any]:
    views: list[dict[str, Any]] = []
    for sheet in schema.get("sheets", []):
        candidates = sheet.get("header_candidates", [])
        header_rows = _select_header_rows(candidates)
        if not header_rows and candidates:
            header_rows = [candidates[0]["row"]]
        if not header_rows:
            header_rows = [1]
        data_start_row = max(header_rows) + 1
        important_columns = _important_columns(sheet)
        entity_columns = _likely_entity_columns(sheet)
        views.append(
            {
                "view_id": f"{schema.get('table_id')}_{sheet.get('sheet')}",
                "sheet": sheet.get("sheet"),
                "title_rows": _detect_title_rows(sheet, header_rows),
                "header_rows": header_rows,
                "data_start_row": data_start_row,
                "data_end_row": sheet.get("max_row"),
                "entity_columns": entity_columns,
                "merged_header_policy": "logical_fill_in_memory_only",
                "normalized_columns": important_columns[:80],
                "notes": [
                    "This is a virtual clean view for planning and analysis.",
                    "The source workbook is not modified.",
                ],
            }
        )
    meta = {
        "catalog_version": TABLE_CATALOG_VERSION,
        "table_id": schema.get("table_id"),
        "filename": schema.get("filename"),
        "path": schema.get("path"),
        "size_bytes": schema.get("size_bytes"),
        "mtime": schema.get("mtime"),
        "views": views,
    }
    return meta


def _build_profile(schema: dict[str, Any], clean_view: dict[str, Any]) -> dict[str, Any]:
    sheet_profiles = []
    for sheet in schema.get("sheets", []):
        sheet_profiles.append(
            {
                "sheet": sheet.get("sheet"),
                "max_row": sheet.get("max_row"),
                "max_column": sheet.get("max_column"),
                "merged_ranges": sheet.get("merged_ranges", [])[:30],
                "header_candidates": sheet.get("header_candidates", [])[:5],
                "entity_columns": _likely_entity_columns(sheet),
                "important_columns": _important_columns(sheet, limit=80),
                "sample_rows": sheet.get("sample_rows", [])[:5],
            }
        )
    return {
        "catalog_version": TABLE_CATALOG_VERSION,
        "table_id": schema.get("table_id"),
        "filename": schema.get("filename"),
        "path": schema.get("path"),
        "suffix": schema.get("suffix"),
        "size_bytes": schema.get("size_bytes"),
        "mtime": schema.get("mtime"),
        "scope_hint": schema.get("scope"),
        "subject_hint": schema.get("subject"),
        "month_hint": schema.get("month"),
        "sheets": sheet_profiles,
        "clean_views": [
            {
                "sheet": view.get("sheet"),
                "header_rows": view.get("header_rows"),
                "data_start_row": view.get("data_start_row"),
                "entity_columns": view.get("entity_columns"),
                "normalized_columns": view.get("normalized_columns", [])[:40],
            }
            for view in clean_view.get("views", [])
        ],
    }


def _fallback_description(profile: dict[str, Any]) -> dict[str, Any]:
    sheet_names = [sheet.get("sheet") for sheet in profile.get("sheets", []) if sheet.get("sheet")]
    columns = [
        column.get("name", "")
        for sheet in profile.get("sheets", [])
        for column in sheet.get("important_columns", [])[:30]
        if column.get("name")
    ]
    metrics = _dedupe_keep_order(columns, limit=30)
    subject = profile.get("subject_hint") if profile.get("subject_hint") != "unknown" else "spreadsheet data"
    month = profile.get("month_hint")
    short = f"{profile.get('filename')} appears to contain {subject}"
    if month:
        short += f" for {month}"
    if metrics:
        short += f"; key columns include {', '.join(metrics[:8])}"
    return {
        "catalog_version": TABLE_CATALOG_VERSION,
        "table_id": profile.get("table_id"),
        "filename": profile.get("filename"),
        "path": profile.get("path"),
        "size_bytes": profile.get("size_bytes"),
        "mtime": profile.get("mtime"),
        "model": "deterministic-fallback",
        "status": "fallback",
        "short_description": short,
        "what_it_records": short,
        "row_grain": "unknown",
        "time_coverage": [month] if month else [],
        "main_entities": [],
        "metric_groups": [],
        "important_metrics": metrics[:30],
        "can_answer": [
            "Questions involving the listed sheets, headers, and sample values may be answerable after inspecting the source table."
        ],
        "not_suitable_for": [],
        "data_quality_notes": [
            "Generated without LLM semantic description.",
            "Use source table inspection for final calculations and evidence.",
        ],
        "ambiguities": [],
        "source_sheets": sheet_names,
    }


def _json_from_llm_text(text: str) -> dict[str, Any]:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text.strip(), flags=re.S)
    if fenced:
        text = fenced.group(1)
    else:
        first = text.find("{")
        last = text.rfind("}")
        if first >= 0 and last > first:
            text = text[first:last + 1]
    return json.loads(text)


def _catalog_description_prompt(profile: dict[str, Any]) -> list[dict[str, str]]:
    compact_profile = {
        "filename": profile.get("filename"),
        "scope_hint": profile.get("scope_hint"),
        "subject_hint": profile.get("subject_hint"),
        "month_hint": profile.get("month_hint"),
        "sheets": [
            {
                "sheet": sheet.get("sheet"),
                "max_row": sheet.get("max_row"),
                "max_column": sheet.get("max_column"),
                "header_candidates": sheet.get("header_candidates", [])[:3],
                "entity_columns": sheet.get("entity_columns", [])[:4],
                "important_columns": sheet.get("important_columns", [])[:50],
                "sample_rows": sheet.get("sample_rows", [])[:3],
            }
            for sheet in profile.get("sheets", [])[:5]
        ],
        "clean_views": profile.get("clean_views", [])[:5],
    }
    user = f"""Create a reusable catalog description for this uploaded spreadsheet.

The description is for table selection, planning, and long conversations. It is NOT final evidence; final answers must still read source cells.

Use only the provided profile. If something is unclear, write "unknown" or add an ambiguity. Return strict JSON only with this schema:
{{
  "short_description": "one concise Chinese sentence",
  "what_it_records": "Chinese explanation of what the table records",
  "row_grain": "what one data row represents, or unknown",
  "time_coverage": ["..."],
  "main_entities": ["..."],
  "metric_groups": ["..."],
  "important_metrics": ["..."],
  "can_answer": ["..."],
  "not_suitable_for": ["..."],
  "data_quality_notes": ["..."],
  "ambiguities": ["..."]
}}

Table profile:
```json
{json.dumps(compact_profile, ensure_ascii=False, indent=2, default=str)}
```"""
    return [
        {
            "role": "system",
            "content": (
                "You are a careful spreadsheet cataloger. Describe uploaded tables for a general-purpose table agent. "
                "Do not invent facts. Prefer Chinese. Return valid JSON only."
            ),
        },
        {"role": "user", "content": user},
    ]


async def _llm_describe_profile(
    profile: dict[str, Any],
    *,
    model: str = DEFAULT_CATALOG_MODEL,
    api_key: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
    base_url = base_url or os.environ.get("DASHSCOPE_BASE_URL") or DEFAULT_DASHSCOPE_BASE_URL
    if not api_key:
        fallback = _fallback_description(profile)
        fallback["status"] = "fallback_missing_api_key"
        return fallback
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        kwargs = {
            "model": model,
            "messages": _catalog_description_prompt(profile),
            "temperature": 0,
            "max_tokens": 1600,
        }
        try:
            response = await client.chat.completions.create(
                **kwargs,
                extra_body={"enable_thinking": False},
            )
        except Exception:
            response = await client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or "{}"
        parsed = _json_from_llm_text(content)
        fallback = _fallback_description(profile)
        return {
            **fallback,
            **{key: parsed.get(key, fallback.get(key)) for key in (
                "short_description",
                "what_it_records",
                "row_grain",
                "time_coverage",
                "main_entities",
                "metric_groups",
                "important_metrics",
                "can_answer",
                "not_suitable_for",
                "data_quality_notes",
                "ambiguities",
            )},
            "model": model,
            "status": "llm",
            "usage": response.usage.model_dump() if response.usage else {},
        }
    except Exception as exc:
        fallback = _fallback_description(profile)
        fallback["status"] = "fallback_llm_error"
        fallback["llm_error"] = repr(exc)
        return fallback


def _catalog_text(description: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "filename",
        "short_description",
        "what_it_records",
        "row_grain",
    ):
        value = description.get(key)
        if value:
            parts.append(str(value))
    for key in (
        "time_coverage",
        "main_entities",
        "metric_groups",
        "important_metrics",
        "can_answer",
        "not_suitable_for",
        "data_quality_notes",
        "ambiguities",
        "source_sheets",
    ):
        value = description.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value if item)
        elif value:
            parts.append(str(value))
    return " ".join(parts)


async def _build_catalog_entry(
    workspace: Path,
    path: Path,
    *,
    rebuild_catalog: bool = False,
    describe_with_llm: bool = True,
    model: str = DEFAULT_CATALOG_MODEL,
) -> dict[str, Any]:
    schema = _load_or_build_schema(workspace, path, rebuild_cache=rebuild_catalog)
    profile_file = _profile_file_for(workspace, path)
    clean_file = _clean_view_file_for(workspace, path)
    description_file = _description_file_for(workspace, path)

    if not rebuild_catalog and _json_file_is_fresh(profile_file, path, version_key="catalog_version", version=TABLE_CATALOG_VERSION):
        profile = json.loads(profile_file.read_text(encoding="utf-8"))
    else:
        clean_view = _build_clean_view(schema)
        profile = _build_profile(schema, clean_view)
        profile_file.parent.mkdir(parents=True, exist_ok=True)
        clean_file.parent.mkdir(parents=True, exist_ok=True)
        profile_file.write_text(json.dumps(profile, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        clean_file.write_text(json.dumps(clean_view, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    if not rebuild_catalog and _json_file_is_fresh(description_file, path, version_key="catalog_version", version=TABLE_CATALOG_VERSION):
        description = json.loads(description_file.read_text(encoding="utf-8"))
    else:
        description = (
            await _llm_describe_profile(profile, model=model)
            if describe_with_llm
            else _fallback_description(profile)
        )
        description_file.parent.mkdir(parents=True, exist_ok=True)
        description_file.write_text(json.dumps(description, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    return {
        "catalog_version": TABLE_CATALOG_VERSION,
        "table_id": schema.get("table_id"),
        "filename": path.name,
        "path": str(path),
        "suffix": path.suffix.lower(),
        "size_bytes": path.stat().st_size,
        "mtime": int(path.stat().st_mtime),
        "scope": schema.get("scope"),
        "subject": schema.get("subject"),
        "month": schema.get("month"),
        "schema_cache": schema.get("cache_file"),
        "profile_path": str(profile_file),
        "clean_view_path": str(clean_file),
        "description_path": str(description_file),
        "description_status": description.get("status"),
        "short_description": description.get("short_description"),
        "what_it_records": description.get("what_it_records"),
        "row_grain": description.get("row_grain"),
        "time_coverage": description.get("time_coverage") or [],
        "main_entities": description.get("main_entities") or [],
        "metric_groups": description.get("metric_groups") or [],
        "important_metrics": description.get("important_metrics") or [],
        "can_answer": description.get("can_answer") or [],
        "not_suitable_for": description.get("not_suitable_for") or [],
        "data_quality_notes": description.get("data_quality_notes") or [],
        "ambiguities": description.get("ambiguities") or [],
        "catalog_text": _catalog_text(description),
    }


async def _build_catalog(
    workspace: Path,
    *,
    rebuild_catalog: bool = False,
    describe_with_llm: bool = True,
    model: str = DEFAULT_CATALOG_MODEL,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    upload_dir = workspace / "uploads"
    entries: list[dict[str, Any]] = []
    for path in _iter_tables(upload_dir)[:limit]:
        try:
            entries.append(
                await _build_catalog_entry(
                    workspace,
                    path,
                    rebuild_catalog=rebuild_catalog,
                    describe_with_llm=describe_with_llm,
                    model=model,
                )
            )
        except Exception as exc:
            entries.append(
                {
                    "catalog_version": TABLE_CATALOG_VERSION,
                    "table_id": _stable_id(path),
                    "filename": path.name,
                    "path": str(path),
                    "suffix": path.suffix.lower(),
                    "size_bytes": path.stat().st_size,
                    "mtime": int(path.stat().st_mtime),
                    "scope": _infer_scope(path.name),
                    "subject": _infer_subject(path.name),
                    "month": _extract_filename_month(path.name),
                    "description_status": "catalog_error",
                    "catalog_error": repr(exc),
                    "catalog_text": path.name,
                }
            )
    catalog_path = _catalog_file(workspace)
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        "\n".join(json.dumps(entry, ensure_ascii=False, default=str) for entry in entries) + ("\n" if entries else ""),
        encoding="utf-8",
    )
    return entries


def _load_catalog(workspace: Path) -> list[dict[str, Any]]:
    catalog_path = _catalog_file(workspace)
    if not catalog_path.exists():
        return []
    return [json.loads(line) for line in catalog_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _catalog_by_path(workspace: Path) -> dict[str, dict[str, Any]]:
    return {entry.get("path"): entry for entry in _load_catalog(workspace) if entry.get("path")}


def _enrich_index_with_catalog(workspace: Path, index: list[dict[str, Any]]) -> list[dict[str, Any]]:
    catalog = _catalog_by_path(workspace)
    if not catalog:
        return index
    enriched: list[dict[str, Any]] = []
    for record in index:
        entry = catalog.get(record.get("path"))
        if not entry:
            enriched.append(record)
            continue
        enriched.append(
            {
                **record,
                "catalog_version": entry.get("catalog_version"),
                "profile_path": entry.get("profile_path"),
                "clean_view_path": entry.get("clean_view_path"),
                "description_path": entry.get("description_path"),
                "description_status": entry.get("description_status"),
                "short_description": entry.get("short_description"),
                "what_it_records": entry.get("what_it_records"),
                "row_grain": entry.get("row_grain"),
                "time_coverage": entry.get("time_coverage") or [],
                "main_entities": entry.get("main_entities") or [],
                "metric_groups": entry.get("metric_groups") or [],
                "important_metrics": entry.get("important_metrics") or [],
                "can_answer": entry.get("can_answer") or [],
                "not_suitable_for": entry.get("not_suitable_for") or [],
                "data_quality_notes": entry.get("data_quality_notes") or [],
                "ambiguities": entry.get("ambiguities") or [],
                "catalog_text": entry.get("catalog_text") or "",
            }
        )
    return enriched


def _question_months(question: str) -> list[str]:
    months: set[str] = set()
    for start_year, start_month, end_year, end_month in re.findall(
        r"(20\d{2})年\s*(\d{1,2})月?\s*[-至到]\s*(20\d{2})年\s*(\d{1,2})月",
        question,
    ):
        current_year, current_month = int(start_year), int(start_month)
        final_year, final_month = int(end_year), int(end_month)
        while (current_year, current_month) <= (final_year, final_month):
            if 1 <= current_month <= 12:
                months.add(f"{current_year}{current_month:02d}")
            current_month += 1
            if current_month > 12:
                current_year += 1
                current_month = 1
    for year, start, end in re.findall(r"(20\d{2})年\s*(\d{1,2})\s*[-至到]\s*(\d{1,2})月", question):
        for month in range(int(start), int(end) + 1):
            if 1 <= month <= 12:
                months.add(f"{year}{month:02d}")
    for year, month in re.findall(r"(20\d{2})年\s*(\d{1,2})月", question):
        months.add(f"{year}{int(month):02d}")
    for raw in re.findall(r"20\d{2}(?:0[1-9]|1[0-2])", question):
        months.add(raw)
    return sorted(months)


def _question_years(question: str) -> list[str]:
    return sorted(set(re.findall(r"20\d{2}", question)))


def _has_any(text: str, terms: tuple[str, ...] | list[str]) -> bool:
    return any(term and term in text for term in terms)


def _parse_retrieval_intent(question: str) -> dict[str, Any]:
    months = _question_months(question)
    years = _question_years(question)
    normalized = _normalize_match_text(question)

    scope = "unknown"
    scope_reason = ""
    if _has_any(question, ("区县", "区/县")):
        scope = "county"
        scope_reason = "query_mentions_county"
    elif _has_any(question, ("市州", "各市州", "地市", "公司")):
        scope = "city"
        scope_reason = "query_mentions_city"
    elif (
        _has_any(question, ("全国", "省份", "各省", "大省"))
        or re.search(r"\d+\s*亿\s*省", question)
        or (re.search(r"[\u4e00-\u9fff]{2,}省", question) and "全省" not in question)
    ):
        scope = "province"
        scope_reason = "query_mentions_province"

    metric_families: list[str] = []
    metric_rules = [
        ("arrears", ("欠费", "未列收", "已列收")),
        ("prepayment", ("预收",)),
        ("aging", ("一年以上", "长账龄", "账龄")),
        ("receivable", ("应收", "应收账款", "占收比", "通报应收总额")),
        ("cash_collection", ("收现", "现金流入", "营业现金比率", "营业收现率")),
        ("guarantee", ("保证金",)),
        ("resource_pool", ("公有池", "私有池")),
    ]
    for family, terms in metric_rules:
        if _has_any(question, terms):
            metric_families.append(family)

    if _has_any(question, ("画", "图", "图表", "柱状图", "组合图", "趋势图", "折线图")):
        task_type = "chart_data"
    elif len(months) >= 3 or _has_any(question, ("逐月", "时间序列", "趋势", "环比", "1-12月")):
        task_type = "multi_month_series"
    elif _has_any(question, ("排名", "排到第几", "最高", "最低", "前三", "前五", "top", "Top")):
        task_type = "ranking"
    elif _has_any(question, ("哪些", "有没有", "满足", "超过", "低于", "筛选", "找出")):
        task_type = "filter"
    else:
        task_type = "single_table"

    period_mode = "none"
    if len(months) == 1:
        period_mode = "single_month"
    elif len(months) > 1:
        period_mode = "multi_month"
    elif years:
        period_mode = "year_only"

    cohort_terms = re.findall(r"\d+\s*亿\s*[\u4e00-\u9fffA-Za-z0-9_]*", question)
    return {
        "months": months,
        "years": years,
        "period_mode": period_mode,
        "scope": scope,
        "scope_reason": scope_reason,
        "metric_families": metric_families,
        "task_type": task_type,
        "cohort_terms": cohort_terms,
        "requires_peer_ranking": _has_any(question, ("排名", "排到第几", "最高", "最低", "前三", "前五")),
        "requires_chart_data": task_type == "chart_data",
        "normalized_query": normalized,
    }


def _record_text_parts(record: dict[str, Any]) -> dict[str, str]:
    preview_text = " ".join(item.get("preview_text", "") for item in record.get("sheets") or [])
    header_text = " ".join(
        " ".join(column.get("header_values", []) + column.get("sample_values", []))
        for sheet in record.get("sheets") or []
        for column in sheet.get("columns", [])
    )
    sheet_text = " ".join(sheet.get("sheet", "") for sheet in record.get("sheets") or [])
    catalog_text = record.get("catalog_text") or " ".join(
        str(part)
        for part in [
            record.get("short_description"),
            record.get("what_it_records"),
            record.get("row_grain"),
            " ".join(record.get("time_coverage") or []),
            " ".join(record.get("main_entities") or []),
            " ".join(record.get("metric_groups") or []),
            " ".join(record.get("important_metrics") or []),
            " ".join(record.get("can_answer") or []),
            " ".join(record.get("not_suitable_for") or []),
            " ".join(record.get("data_quality_notes") or []),
            " ".join(record.get("ambiguities") or []),
        ]
        if part
    )
    filename = record.get("filename", "")
    subject = record.get("subject") or ""
    scope = record.get("scope") or ""
    keywords = " ".join(record.get("keywords") or [])
    return {
        "filename": filename,
        "subject": subject,
        "scope": scope,
        "keywords": keywords,
        "preview": preview_text,
        "headers": header_text,
        "sheets": sheet_text,
        "catalog": catalog_text,
        "all": f"{filename} {subject} {scope} {sheet_text} {keywords} {catalog_text} {header_text} {preview_text}",
    }


def _record_matches_family(family: str, record: dict[str, Any], text: str) -> bool:
    subject = record.get("subject") or ""
    filename = record.get("filename") or ""
    haystack = f"{filename} {subject} {text}"
    family_terms = {
        "arrears": ("欠费", "未列收", "已列收"),
        "prepayment": ("预收",),
        "aging": ("一年以上", "长账龄", "账龄"),
        "receivable": ("应收", "应收账款", "占收比", "通报应收总额"),
        "cash_collection": ("收现", "现金流入", "营业现金比率", "营业收现率"),
        "guarantee": ("保证金",),
        "resource_pool": ("公有池", "私有池"),
    }
    return _has_any(haystack, family_terms.get(family, (family,)))


def _is_ledger_like(record: dict[str, Any], text: str) -> bool:
    return not record.get("month") and _has_any(text, ("台账", "明细", "欠费", "账龄", "逐月", "月份"))


def _constraint_score(intent: dict[str, Any], record: dict[str, Any], text: str) -> tuple[float, list[str], list[str], dict[str, Any]]:
    score = 0.0
    reasons: list[str] = []
    risks: list[str] = []
    fit: dict[str, Any] = {
        "period": "unknown",
        "scope": "unknown",
        "metric_family": [],
        "task_type": intent.get("task_type"),
    }

    months = intent.get("months") or []
    record_month = record.get("month")
    if months:
        if record_month in months:
            score += 34
            reasons.append(f"period:exact:{record_month}")
            fit["period"] = "exact"
        elif any(month in text for month in months):
            score += 24
            reasons.append("period:schema_or_catalog")
            fit["period"] = "mentioned_in_schema"
        elif _is_ledger_like(record, text) and (
            intent.get("period_mode") == "multi_month" or "arrears" in (intent.get("metric_families") or [])
        ):
            score += 20
            reasons.append("period:ledger_can_span_months")
            fit["period"] = "ledger"
        elif record_month:
            same_year = any(record_month[:4] == month[:4] for month in months)
            penalty = 16 if same_year and intent.get("period_mode") == "multi_month" else 36
            score -= penalty
            risks.append(f"period_mismatch:{record_month}")
            fit["period"] = "mismatch"
        else:
            score -= 8
            risks.append("period_unknown")
    elif intent.get("years") and record_month and record_month[:4] in intent["years"]:
        score += 8
        reasons.append(f"period:year:{record_month[:4]}")
        fit["period"] = "year"

    desired_scope = intent.get("scope")
    record_scope = record.get("scope") or "unknown"
    fit["scope"] = record_scope
    if desired_scope and desired_scope != "unknown":
        if record_scope == desired_scope:
            score += 30
            reasons.append(f"scope:exact:{record_scope}")
        elif record_scope == "unknown":
            score -= 6
            risks.append("scope_unknown")
        else:
            score -= 42
            risks.append(f"scope_mismatch:{record_scope}_for_{desired_scope}")
    elif intent.get("cohort_terms") and record_scope == "province":
        score += 18
        reasons.append("scope:cohort_prefers_province")

    matched_families: list[str] = []
    for family in intent.get("metric_families") or []:
        if _record_matches_family(family, record, text):
            matched_families.append(family)
            if family in {"arrears", "prepayment"}:
                score += 30
            elif family in {"receivable", "aging"}:
                score += 22
            else:
                score += 16
            reasons.append(f"metric_family:{family}")
        else:
            penalty = 28 if family in {"arrears", "prepayment"} else 14
            score -= penalty
            risks.append(f"metric_family_missing:{family}")
    fit["metric_family"] = matched_families

    if intent.get("task_type") in {"ranking", "filter", "chart_data"} and record_scope == "province" and intent.get("cohort_terms"):
        score += 18
        reasons.append("cohort:province_table")
    if intent.get("task_type") == "multi_month_series" and (len(months) >= 3 or _is_ledger_like(record, text)):
        score += 10
        reasons.append("task:series_compatible")
    if intent.get("task_type") == "chart_data":
        score += 4
        reasons.append("task:chart_data")

    return score, reasons, risks, fit


def _record_group_key(record: dict[str, Any]) -> str:
    filename = record.get("filename", "")
    stem = Path(filename).stem
    stem = re.sub(r"[_-]?20\d{2}(?:0[1-9]|1[0-2])$", "", stem)
    return stem or filename


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


def _score_record(question: str, record: dict[str, Any], intent: dict[str, Any] | None = None) -> tuple[float, list[str], list[str], dict[str, Any]]:
    intent = intent or _parse_retrieval_intent(question)
    text_parts = _record_text_parts(record)
    filename = text_parts["filename"]
    subject = text_parts["subject"]
    keywords = set(record.get("keywords") or [])
    preview_text = text_parts["preview"]
    header_text = text_parts["headers"]
    sheet_text = text_parts["sheets"]
    catalog_text = text_parts["catalog"]
    haystack = text_parts["all"]
    terms = _question_terms(question)
    constraint, constraint_reasons, risks, fit = _constraint_score(intent, record, haystack)
    filename_score = 0.0
    subject_score = 0.0
    keyword_score = 0.0
    catalog_score = 0.0
    preview_score = 0.0
    schema_score = 0.0
    sheet_score = 0.0
    reasons: list[str] = []

    for term in terms:
        if term in filename:
            filename_score += 8
            reasons.append(f"filename:{term}")
        elif term in subject:
            subject_score += 5
            reasons.append(f"subject:{term}")
        elif term in keywords:
            keyword_score += 4
            reasons.append(f"keyword:{term}")
        elif term in catalog_text:
            catalog_score += 5
            reasons.append(f"catalog:{term}")
        elif term in preview_text:
            preview_score += 2
            reasons.append(f"preview:{term}")
        elif term in header_text:
            schema_score += 3
            reasons.append(f"schema:{term}")
        elif term in sheet_text:
            sheet_score += 3
            reasons.append(f"sheet:{term}")

    score_breakdown = {
        "constraints": round(constraint, 2),
        "filename": min(filename_score, 80),
        "subject": min(subject_score, 20),
        "keyword": min(keyword_score, 24),
        "catalog": min(catalog_score, 28),
        "schema": min(schema_score, 30),
        "preview": min(preview_score, 12),
        "sheet": min(sheet_score, 12),
    }
    score = sum(score_breakdown.values())
    fit["score_breakdown"] = score_breakdown
    combined_reasons = constraint_reasons + reasons
    return score, combined_reasons[:14], risks[:8], fit


def _retrieve(question: str, index: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    intent = _parse_retrieval_intent(question)
    scored = []
    for record in index:
        score, reasons, risks, fit = _score_record(question, record, intent)
        if score > 0:
            scored.append({**record, "score": round(score, 2), "reasons": reasons, "risks": risks, "fit": fit})
    scored.sort(key=lambda item: (-item["score"], item["filename"]))
    return scored[:top_k]


def _retrieve_groups(question: str, index: list[dict[str, Any]], top_k: int = 5) -> list[dict[str, Any]]:
    intent = _parse_retrieval_intent(question)
    months = intent.get("months") or []
    if intent.get("task_type") not in {"multi_month_series", "chart_data"} and len(months) < 3:
        return []
    groups: dict[str, dict[str, Any]] = {}
    for record in index:
        score, reasons, risks, fit = _score_record(question, record, intent)
        if score <= 0:
            continue
        key = _record_group_key(record)
        group = groups.setdefault(
            key,
            {
                "group_key": key,
                "scope": record.get("scope"),
                "subject": record.get("subject"),
                "score": 0.0,
                "months": [],
                "paths": [],
                "filenames": [],
                "reasons": [],
                "risks": [],
            },
        )
        month = record.get("month")
        if month:
            group["months"].append(month)
        group["paths"].append(record.get("path"))
        group["filenames"].append(record.get("filename"))
        group["score"] = max(group["score"], score)
        group["reasons"].extend(reason for reason in reasons if reason not in group["reasons"])
        group["risks"].extend(risk for risk in risks if risk not in group["risks"])

    result: list[dict[str, Any]] = []
    requested = set(months)
    for group in groups.values():
        group_months = sorted(set(group["months"]))
        coverage = len(requested.intersection(group_months)) if requested else len(group_months)
        ledger_series = not group_months and requested and (
            any("period:ledger_can_span_months" in reason for reason in group["reasons"])
            or any("period:schema_or_catalog" in reason for reason in group["reasons"])
        )
        if requested and coverage == 0 and group_months:
            continue
        effective_coverage = len(requested) if ledger_series else coverage
        group["months"] = group_months
        group["coverage"] = {
            "requested_months": len(requested),
            "matched_months": coverage,
            "effective_matched_months": effective_coverage,
            "available_months": len(group_months),
            "ledger_series": bool(ledger_series),
        }
        group["score"] = round(group["score"] + effective_coverage * 6 + min(len(group_months), 12), 2)
        group["paths"] = [path for _, path in sorted(zip(group["filenames"], group["paths"]))]
        group["filenames"] = sorted(group["filenames"])
        group["reasons"] = group["reasons"][:12]
        group["risks"] = group["risks"][:8]
        result.append(group)
    result.sort(key=lambda item: (-item["score"], item["group_key"]))
    return result[:top_k]


@tool_parameters(
    tool_parameters_schema(
        rebuild_catalog=BooleanSchema(description="Rebuild catalog profiles/descriptions even if source files are unchanged.", default=False),
        describe_with_llm=BooleanSchema(description="Use DashScope/OpenAI-compatible LLM to generate semantic table descriptions. Falls back safely if unavailable.", default=True),
        model=StringSchema(f"OpenAI-compatible model for table descriptions. Defaults to {DEFAULT_CATALOG_MODEL}.", nullable=True),
        limit=IntegerSchema(description="Optional maximum number of uploaded tables to catalog.", minimum=1, maximum=500, nullable=True),
    )
)
class TableClawCatalogTablesTool(Tool):
    """Build a reusable catalog for uploaded spreadsheet files."""

    def __init__(self, workspace: Path | None = None):
        self._workspace = Path(workspace or ".").resolve()

    @classmethod
    def create(cls, ctx: Any) -> Tool:
        return cls(workspace=Path(ctx.workspace))

    @property
    def name(self) -> str:
        return "tableclaw_catalog_tables"

    @property
    def description(self) -> str:
        return (
            "Build or refresh the TableClaw table catalog for files in workspace/uploads. "
            "For each table it creates deterministic profile and virtual clean-view JSON, plus a reusable semantic "
            "description of what the table records, row grain, key metrics, can-answer tasks, and data quality notes. "
            "Use after uploads or when table selection is ambiguous; it does not modify source spreadsheets."
        )

    @property
    def read_only(self) -> bool:
        return True

    async def execute(
        self,
        rebuild_catalog: bool = False,
        describe_with_llm: bool = True,
        model: str = DEFAULT_CATALOG_MODEL,
        limit: int | None = None,
        **_: Any,
    ) -> str:
        entries = await _build_catalog(
            self._workspace,
            rebuild_catalog=rebuild_catalog,
            describe_with_llm=describe_with_llm,
            model=model or DEFAULT_CATALOG_MODEL,
            limit=limit,
        )
        compact = [
            {
                "table_id": entry.get("table_id"),
                "filename": entry.get("filename"),
                "scope": entry.get("scope"),
                "subject": entry.get("subject"),
                "month": entry.get("month"),
                "description_status": entry.get("description_status"),
                "short_description": entry.get("short_description"),
                "row_grain": entry.get("row_grain"),
                "important_metrics": (entry.get("important_metrics") or [])[:12],
                "can_answer": (entry.get("can_answer") or [])[:6],
                "description_path": entry.get("description_path"),
                "profile_path": entry.get("profile_path"),
                "clean_view_path": entry.get("clean_view_path"),
                "catalog_error": entry.get("catalog_error"),
            }
            for entry in entries[:50]
        ]
        return _json_response(
            {
                "status": "ok",
                "workspace": str(self._workspace),
                "catalog_file": str(_catalog_file(self._workspace)),
                "uploaded_tables": len(_iter_tables(self._workspace / "uploads")),
                "cataloged_tables": len(entries),
                "shown_tables": len(compact),
                "describe_with_llm": describe_with_llm,
                "model": model,
                "tables": compact,
                "next_step": "Use tableclaw_retrieve_tables; it will include catalog descriptions in table matching when catalog entries exist.",
            }
        )


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
        path=StringSchema("Spreadsheet path. Can be absolute, workspace-relative, or a filename under workspace/uploads."),
        metric=StringSchema("Metric/header text to locate, for example 营业收现率完成 or 应收总额同比增幅.", nullable=True),
        period=StringSchema("Optional period/month header such as 202502 or 2025年2月.", nullable=True),
        group=StringSchema("Optional upper-level/group header text.", nullable=True),
        reference=StringSchema("Optional explicit column reference such as A, C, 3, or a header name.", nullable=True),
        sheet=StringSchema("Optional sheet name.", nullable=True),
        required=["path"],
    )
)
class TableClawLocateColumnTool(Tool):
    """Locate a spreadsheet column by period/metric/group headers."""

    def __init__(self, workspace: Path | None = None):
        self._workspace = Path(workspace or ".").resolve()

    @classmethod
    def create(cls, ctx: Any) -> Tool:
        return cls(workspace=Path(ctx.workspace))

    @property
    def name(self) -> str:
        return "tableclaw_locate_column"

    @property
    def description(self) -> str:
        return (
            "Locate an exact spreadsheet column using multi-row/merged headers. Use after tableclaw_inspect when you need "
            "the column for a metric, period, or explicit reference before computing top-k, filter, or series results."
        )

    @property
    def read_only(self) -> bool:
        return True

    async def execute(
        self,
        path: str,
        metric: str | None = None,
        period: str | None = None,
        group: str | None = None,
        reference: str | None = None,
        sheet: str | None = None,
        **_: Any,
    ) -> str:
        table_path = _resolve_table_path(self._workspace, path)
        if not table_path.exists():
            return f"Error: table file not found: {table_path}"
        schema = _load_or_build_schema(self._workspace, table_path)
        sheet_name = _choose_sheet(schema, sheet)
        selected_sheet, rows, max_row, max_col = _load_sheet_matrix(table_path, sheet_name)
        header_rows = _header_rows_from_matrix(rows, max_col)
        match = _locate_column_in_matrix(
            rows,
            max_col=max_col,
            header_rows=header_rows,
            reference=reference,
            metric=metric,
            period=period,
            group=group,
        )
        return _json_response(
            {
                "path": str(table_path),
                "sheet": selected_sheet,
                "max_row": max_row,
                "max_column": max_col,
                "header_rows": header_rows,
                "query": {"reference": reference, "metric": metric, "period": period, "group": group},
                "match": match,
                "status": "found" if match else "not_found",
            }
        )


def _condition_passes(actual: Any, condition: dict[str, Any]) -> bool:
    op = str(condition.get("op") or condition.get("operator") or "eq").lower()
    expected = condition.get("value")
    actual_text = _cell_text(actual)
    actual_number = _to_float(actual)
    expected_number = _to_float(expected)
    if op in {"contains", "包含"}:
        return _contains_loose(actual_text, expected)
    if op in {"not_contains", "not-contains", "不包含"}:
        return not _contains_loose(actual_text, expected)
    if op in {"eq", "=", "==", "等于"}:
        if expected_number is not None and actual_number is not None:
            return abs(actual_number - expected_number) <= 1e-12
        return _contains_loose(actual_text, expected)
    if op in {"ne", "!=", "不等于"}:
        return not _condition_passes(actual, {**condition, "op": "eq"})
    if actual_number is None:
        return False
    if op in {"gt", ">", "大于"}:
        return expected_number is not None and actual_number > expected_number
    if op in {"gte", ">=", "大于等于", "不少于"}:
        return expected_number is not None and actual_number >= expected_number
    if op in {"lt", "<", "小于", "低于"}:
        return expected_number is not None and actual_number < expected_number
    if op in {"lte", "<=", "小于等于", "不高于"}:
        return expected_number is not None and actual_number <= expected_number
    if op in {"between", "range", "区间"}:
        low = _to_float(condition.get("min"))
        high = _to_float(condition.get("max"))
        return (low is None or actual_number >= low) and (high is None or actual_number <= high)
    return False


def _parse_conditions(conditions: Any) -> list[dict[str, Any]]:
    if isinstance(conditions, str):
        try:
            parsed = json.loads(conditions)
        except json.JSONDecodeError:
            return []
        conditions = parsed
    if isinstance(conditions, dict):
        conditions = [conditions]
    if not isinstance(conditions, list):
        return []
    return [item for item in conditions if isinstance(item, dict)]


@tool_parameters(
    tool_parameters_schema(
        path=StringSchema("Spreadsheet path. Can be absolute, workspace-relative, or a filename under workspace/uploads."),
        value_col=StringSchema("Column reference/name to sort by, such as C, 3, or a header. Optional if metric/period are provided.", nullable=True),
        metric=StringSchema("Metric/header text to sort by if value_col is not explicit.", nullable=True),
        period=StringSchema("Optional period/month header such as 202502 or 2025年2月.", nullable=True),
        sheet=StringSchema("Optional sheet name.", nullable=True),
        k=IntegerSchema(10, description="Number of rows to return.", minimum=1, maximum=100),
        ascending=BooleanSchema(description="Sort ascending. Default false means top/highest first.", default=False),
        entity_col=StringSchema("Optional entity/name column, such as 单位, B, or 2.", nullable=True),
        exclude_contains=StringSchema("Comma-separated row text to exclude, for example 合计,市州合计,total.", nullable=True),
        required=["path"],
    )
)
class TableClawTopKTool(Tool):
    """Return top/bottom rows by a numeric spreadsheet column."""

    def __init__(self, workspace: Path | None = None):
        self._workspace = Path(workspace or ".").resolve()

    @classmethod
    def create(cls, ctx: Any) -> Tool:
        return cls(workspace=Path(ctx.workspace))

    @property
    def name(self) -> str:
        return "tableclaw_topk"

    @property
    def description(self) -> str:
        return (
            "Compute top/bottom-k rows from a spreadsheet after locating the numeric metric column. Use for ranking tasks "
            "instead of writing a custom openpyxl sorting script."
        )

    @property
    def read_only(self) -> bool:
        return True

    async def execute(
        self,
        path: str,
        value_col: str | None = None,
        metric: str | None = None,
        period: str | None = None,
        sheet: str | None = None,
        k: int = 10,
        ascending: bool = False,
        entity_col: str | None = None,
        exclude_contains: str | None = "合计,市州合计,total",
        **_: Any,
    ) -> str:
        table_path = _resolve_table_path(self._workspace, path)
        if not table_path.exists():
            return f"Error: table file not found: {table_path}"
        schema = _load_or_build_schema(self._workspace, table_path)
        sheet_name = _choose_sheet(schema, sheet)
        selected_sheet, rows, max_row, max_col = _load_sheet_matrix(table_path, sheet_name)
        header_rows = _header_rows_from_matrix(rows, max_col)
        data_start_row = max(header_rows or [1]) + 1
        value_match = _locate_column_in_matrix(
            rows,
            max_col=max_col,
            header_rows=header_rows,
            reference=value_col,
            metric=metric,
            period=period,
        )
        if not value_match:
            return _json_response({"status": "value_column_not_found", "path": str(table_path), "sheet": selected_sheet})
        entity_match = _locate_column_in_matrix(
            rows,
            max_col=max_col,
            header_rows=header_rows,
            reference=entity_col,
            metric="单位" if not entity_col else None,
        )
        entity_col_index = (entity_match or {}).get("index") or 2 if max_col >= 2 else 1
        exclude_terms = [term.strip() for term in (exclude_contains or "").split(",") if term.strip()]
        items: list[dict[str, Any]] = []
        value_col_index = int(value_match["index"])
        for row_number in range(data_start_row, len(rows) + 1):
            row = rows[row_number - 1]
            row_text = " ".join(_cell_text(value) for value in row if _cell_text(value))
            if not row_text or any(_contains_loose(row_text, term) for term in exclude_terms):
                continue
            value = _cell_value(rows, row_number, value_col_index)
            number = _to_float(value)
            if number is None:
                continue
            entity = _cell_text(_cell_value(rows, row_number, int(entity_col_index))) or row_text[:80]
            items.append(
                {
                    "row": row_number,
                    "entity": entity,
                    "value": number,
                    "raw_value": _cell_text(value),
                    "row_text": row_text[:500],
                }
            )
        items.sort(key=lambda item: item["value"], reverse=not _parse_boolish(ascending))
        return _json_response(
            {
                "status": "ok",
                "path": str(table_path),
                "sheet": selected_sheet,
                "header_rows": header_rows,
                "data_start_row": data_start_row,
                "value_column": value_match,
                "entity_column": entity_match,
                "ascending": _parse_boolish(ascending),
                "k": k,
                "results": items[: max(1, min(int(k), 100))],
            }
        )


@tool_parameters(
    tool_parameters_schema(
        path=StringSchema("Spreadsheet path. Can be absolute, workspace-relative, or a filename under workspace/uploads."),
        conditions=ArraySchema(
            ObjectSchema(
                col=StringSchema("Explicit column reference/name, optional if metric/period are provided.", nullable=True),
                metric=StringSchema("Metric/header text.", nullable=True),
                period=StringSchema("Optional period/month header.", nullable=True),
                op=StringSchema("Operator: eq, contains, gt, gte, lt, lte, between, ne."),
                value=StringSchema("Comparison value.", nullable=True),
                min=NumberSchema(description="Minimum for between.", nullable=True),
                max=NumberSchema(description="Maximum for between.", nullable=True),
            ),
            description="List of row conditions; all conditions must pass.",
            min_items=1,
            max_items=12,
        ),
        sheet=StringSchema("Optional sheet name.", nullable=True),
        entity_col=StringSchema("Optional entity/name column, such as 单位, B, or 2.", nullable=True),
        exclude_contains=StringSchema("Comma-separated row text to exclude, for example 合计,市州合计,total.", nullable=True),
        limit=IntegerSchema(50, description="Maximum matched rows to return.", minimum=1, maximum=200),
        required=["path", "conditions"],
    )
)
class TableClawFilterTool(Tool):
    """Filter spreadsheet rows with multiple conditions."""

    def __init__(self, workspace: Path | None = None):
        self._workspace = Path(workspace or ".").resolve()

    @classmethod
    def create(cls, ctx: Any) -> Tool:
        return cls(workspace=Path(ctx.workspace))

    @property
    def name(self) -> str:
        return "tableclaw_filter"

    @property
    def description(self) -> str:
        return (
            "Filter spreadsheet rows by multiple conditions, including threshold/range/contains checks. Use for questions "
            "asking which units satisfy criteria or how many rows meet conditions."
        )

    @property
    def read_only(self) -> bool:
        return True

    async def execute(
        self,
        path: str,
        conditions: Any,
        sheet: str | None = None,
        entity_col: str | None = None,
        exclude_contains: str | None = "合计,市州合计,total",
        limit: int = 50,
        **_: Any,
    ) -> str:
        parsed_conditions = _parse_conditions(conditions)
        table_path = _resolve_table_path(self._workspace, path)
        if not table_path.exists():
            return f"Error: table file not found: {table_path}"
        schema = _load_or_build_schema(self._workspace, table_path)
        sheet_name = _choose_sheet(schema, sheet)
        selected_sheet, rows, _max_row, max_col = _load_sheet_matrix(table_path, sheet_name)
        header_rows = _header_rows_from_matrix(rows, max_col)
        data_start_row = max(header_rows or [1]) + 1
        located_conditions: list[dict[str, Any]] = []
        for condition in parsed_conditions:
            match = _locate_column_in_matrix(
                rows,
                max_col=max_col,
                header_rows=header_rows,
                reference=condition.get("col"),
                metric=condition.get("metric"),
                period=condition.get("period"),
            )
            if not match:
                return _json_response({"status": "condition_column_not_found", "condition": condition, "path": str(table_path), "sheet": selected_sheet})
            located_conditions.append({"condition": condition, "column": match})
        entity_match = _locate_column_in_matrix(
            rows,
            max_col=max_col,
            header_rows=header_rows,
            reference=entity_col,
            metric="单位" if not entity_col else None,
        )
        entity_col_index = (entity_match or {}).get("index") or 2 if max_col >= 2 else 1
        exclude_terms = [term.strip() for term in (exclude_contains or "").split(",") if term.strip()]
        matches: list[dict[str, Any]] = []
        for row_number in range(data_start_row, len(rows) + 1):
            row = rows[row_number - 1]
            row_text = " ".join(_cell_text(value) for value in row if _cell_text(value))
            if not row_text or any(_contains_loose(row_text, term) for term in exclude_terms):
                continue
            checks = []
            passed = True
            for item in located_conditions:
                col_index = int(item["column"]["index"])
                actual = _cell_value(rows, row_number, col_index)
                ok = _condition_passes(actual, item["condition"])
                checks.append(
                    {
                        "column": item["column"],
                        "op": item["condition"].get("op") or "eq",
                        "expected": item["condition"].get("value"),
                        "actual": _cell_text(actual),
                        "passed": ok,
                    }
                )
                if not ok:
                    passed = False
                    break
            if not passed:
                continue
            matches.append(
                {
                    "row": row_number,
                    "entity": _cell_text(_cell_value(rows, row_number, int(entity_col_index))) or row_text[:80],
                    "checks": checks,
                    "row_text": row_text[:500],
                }
            )
        return _json_response(
            {
                "status": "ok",
                "path": str(table_path),
                "sheet": selected_sheet,
                "header_rows": header_rows,
                "data_start_row": data_start_row,
                "conditions": located_conditions,
                "entity_column": entity_match,
                "matched_count": len(matches),
                "results": matches[: max(1, min(int(limit), 200))],
            }
        )


@tool_parameters(
    tool_parameters_schema(
        path=StringSchema("Spreadsheet path. Can be absolute, workspace-relative, or a filename under workspace/uploads."),
        entity=StringSchema("Entity/unit/province/city name to extract, for example 四川 or 成都.", nullable=True),
        metric=StringSchema("Metric/header text to extract across periods.", nullable=True),
        periods=StringSchema("Comma-separated periods or range text, for example 202501,202502 or 2025年1-12月.", nullable=True),
        period_start=StringSchema("Optional start period such as 202501.", nullable=True),
        period_end=StringSchema("Optional end period such as 202512.", nullable=True),
        sheet=StringSchema("Optional sheet name.", nullable=True),
        entity_col=StringSchema("Optional entity/name column, such as 单位, B, or 2.", nullable=True),
        exclude_contains=StringSchema("Comma-separated row text to exclude, for example 合计,市州合计,total.", nullable=True),
        required=["path"],
    )
)
class TableClawExtractSeriesTool(Tool):
    """Extract period series values for an entity and metric."""

    def __init__(self, workspace: Path | None = None):
        self._workspace = Path(workspace or ".").resolve()

    @classmethod
    def create(cls, ctx: Any) -> Tool:
        return cls(workspace=Path(ctx.workspace))

    @property
    def name(self) -> str:
        return "tableclaw_extract_series"

    @property
    def description(self) -> str:
        return (
            "Extract a month/period series for an entity and metric from a spreadsheet with multi-row headers. Use for trend "
            "tables and cross-month comparisons instead of manually scanning each column."
        )

    @property
    def read_only(self) -> bool:
        return True

    async def execute(
        self,
        path: str,
        entity: str | None = None,
        metric: str | None = None,
        periods: str | None = None,
        period_start: str | None = None,
        period_end: str | None = None,
        sheet: str | None = None,
        entity_col: str | None = None,
        exclude_contains: str | None = "合计,市州合计,total",
        **_: Any,
    ) -> str:
        table_path = _resolve_table_path(self._workspace, path)
        if not table_path.exists():
            return f"Error: table file not found: {table_path}"
        schema = _load_or_build_schema(self._workspace, table_path)
        sheet_name = _choose_sheet(schema, sheet)
        selected_sheet, rows, _max_row, max_col = _load_sheet_matrix(table_path, sheet_name)
        header_rows = _header_rows_from_matrix(rows, max_col)
        data_start_row = max(header_rows or [1]) + 1
        parsed_periods = _parse_periods(periods, period_start, period_end)
        if not parsed_periods and periods:
            parsed_periods = [part.strip() for part in re.split(r"[,，、\s]+", periods) if part.strip()]
        row_matches = _locate_row(
            rows,
            data_start_row=data_start_row,
            entity=entity,
            entity_col=entity_col,
            exclude_contains=exclude_contains,
        )
        if entity and not row_matches:
            return _json_response({"status": "entity_not_found", "entity": entity, "path": str(table_path), "sheet": selected_sheet})
        target_rows = row_matches[:10] if entity else _locate_row(
            rows,
            data_start_row=data_start_row,
            entity=None,
            entity_col=entity_col,
            exclude_contains=exclude_contains,
        )[:10]
        series: list[dict[str, Any]] = []
        periods_to_scan = parsed_periods or [None]
        located_columns: list[dict[str, Any]] = []
        for period in periods_to_scan:
            column = _locate_column_in_matrix(
                rows,
                max_col=max_col,
                header_rows=header_rows,
                metric=metric,
                period=period,
            )
            if not column:
                series.append({"period": period, "status": "column_not_found"})
                continue
            located_columns.append(column)
            for row_match in target_rows:
                value = _cell_value(rows, int(row_match["row"]), int(column["index"]))
                series.append(
                    {
                        "period": period,
                        "row": row_match["row"],
                        "entity": entity or row_match["row_text"][:80],
                        "column": column,
                        "value": _to_float(value),
                        "raw_value": _cell_text(value),
                    }
                )
        return _json_response(
            {
                "status": "ok",
                "path": str(table_path),
                "sheet": selected_sheet,
                "header_rows": header_rows,
                "data_start_row": data_start_row,
                "entity": entity,
                "metric": metric,
                "periods": parsed_periods,
                "target_rows": target_rows,
                "located_columns": located_columns,
                "series": series,
            }
        )


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

        index = _enrich_index_with_catalog(self._workspace, index)
        intent = _parse_retrieval_intent(query)
        candidates = _retrieve(query, index, top_k=top_k)
        table_groups = _retrieve_groups(query, index, top_k=5)
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
                    "risks": item.get("risks"),
                    "fit": item.get("fit"),
                    "description_status": item.get("description_status"),
                    "short_description": item.get("short_description"),
                    "row_grain": item.get("row_grain"),
                    "important_metrics": (item.get("important_metrics") or [])[:12],
                    "can_answer": (item.get("can_answer") or [])[:6],
                    "description_path": item.get("description_path"),
                    "profile_path": item.get("profile_path"),
                    "clean_view_path": item.get("clean_view_path"),
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
                "catalog_file": str(_catalog_file(self._workspace)),
                "catalog_available": bool(_load_catalog(self._workspace)),
                "indexed_tables": len(index),
                "retrieval_version": "v5-structured-intent",
                "intent": intent,
                "top_k": top_k,
                "candidates": compact_candidates,
                "table_groups": table_groups,
                "next_step": (
                    "Use intent/fit/risks to choose candidate paths. For multi-month or trend tasks, prefer table_groups. "
                    "Catalog descriptions are planning context; validate exact cells with tableclaw_inspect/locate/extract/topk/filter."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
