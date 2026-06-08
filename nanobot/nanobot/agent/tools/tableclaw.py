"""TableClaw tools for uploaded spreadsheet retrieval."""
from __future__ import annotations

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


def _build_index(upload_dir: Path, index_file: Path) -> list[dict[str, Any]]:
    index_file.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for path in _iter_tables(upload_dir):
        previews = _read_preview(path)
        preview_text = " ".join(item.get("preview_text", "") for item in previews)
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
                "sheets": previews,
                "keywords": sorted(set(term for term in QUESTION_TERMS if term in path.name or term in preview_text)),
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
    for token in re.findall(r"[A-Za-z0-9]+", question):
        if len(token) >= 2:
            terms.append(token)
    return sorted(set(terms), key=lambda item: (-len(item), item))


def _score_record(question: str, record: dict[str, Any]) -> tuple[float, list[str]]:
    filename = record["filename"]
    subject = record.get("subject") or ""
    scope = record.get("scope") or ""
    keywords = set(record.get("keywords") or [])
    preview_text = " ".join(item.get("preview_text", "") for item in record.get("sheets") or [])
    haystack = f"{filename} {subject} {scope} {' '.join(keywords)} {preview_text}"
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

    if months:
        if record.get("month") in months:
            score += 10
            reasons.append(f"month:{record['month']}")
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
            "month, sheet previews, scores, and match reasons; it does not read full spreadsheet contents."
        )

    @property
    def read_only(self) -> bool:
        return True

    async def execute(self, query: str, top_k: int = 8, rebuild_index: bool = False, **_: Any) -> str:
        upload_dir = self._workspace / "uploads"
        index_file = self._workspace / "table_index" / "tables.jsonl"
        if rebuild_index or not index_file.exists():
            index = _build_index(upload_dir, index_file)
        else:
            index = _load_index(index_file) or _build_index(upload_dir, index_file)

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
                "next_step": "Choose relevant candidate path(s), then inspect sheets and compute the answer with spreadsheet skills/tools.",
            },
            ensure_ascii=False,
            indent=2,
        )
