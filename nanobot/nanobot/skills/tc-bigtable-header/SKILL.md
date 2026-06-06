---
name: tc-bigtable-header
description: "Use this skill the moment you encounter a wide spreadsheet (≥50 columns, or a file >300KB, or where row 1 is mostly None except a few period markers). Such tables typically have multi-row merged headers (3 to 5 rows) where each value is held only by the top-left cell of its merge range and every other cell in the range reads as None. Direct read_file truncates badly and column names look ambiguous because the same sub-metric (e.g. '欠费金额（万元）', '同比（%）') repeats once per period. This skill gives the exact recipe for unfolding merged header rows so a downstream lookup like (period, 大类, 子指标) → column index becomes one line of code. Trigger on: '欠费表', '宽表', '多级表头', '合并单元格', '看不到所有列名', '同名列', '怎么定位列', or whenever the user asks something like 'in 202501 the 总系统欠费 欠费金额 of city X'."
---

# tc-bigtable-header — Unfolding Multi-Row Merged Headers

You are about to query a wide spreadsheet whose header is split across multiple physical rows and held by merged cells. **Do not rely on `read_file` for column discovery** — it truncates and gives you Nones for every cell except the merge top-left.

## Mandatory recipe

```python
import openpyxl
wb = openpyxl.load_workbook(PATH, data_only=True)
ws = wb.active

def fill_merged(row_idx):
    """Return a flat list of values for one row, with merged-cell values
    forward-filled across the whole merged range."""
    out = [ws.cell(row_idx, c).value for c in range(1, ws.max_column + 1)]
    for mr in ws.merged_cells.ranges:
        if mr.min_row <= row_idx <= mr.max_row:
            v = ws.cell(mr.min_row, mr.min_col).value
            for c in range(mr.min_col, mr.max_col + 1):
                if 1 <= c <= len(out):
                    out[c - 1] = v
    return out
```

Always run `fill_merged` on **every** header row you care about before doing any column lookup. Row 1 typically holds the period (e.g. `202501`, `202502`, ...). Row 2 holds the metric group (e.g. `总系统欠费`, `分列收`, `分欠费月份`, `其中：已列收`, `其中：未列收`). Row 3 holds the leaf metric (e.g. `欠费金额（万元）`, `同比（%）`, `占收比（%）`, `列收欠费`, `未列收欠费`). Lower rows (4, 5) usually hold the area / unit column names — check rows 4 and 5 explicitly, do not assume row 5 is always the leaf.

Once you have the unfolded `r1`, `r2`, `r3`, finding a column is one line:

```python
def find_col(period, big, sub, r1, r2, r3):
    for c in range(1, len(r1) + 1):
        if r1[c-1] == period and r2[c-1] == big and r3[c-1] == sub:
            return c
    raise ValueError(f"column not found: {(period, big, sub)}")
```

Print at least one verification line after locating columns, e.g. `print('col 202501 总系统欠费 欠费金额(万元):', c)`, so the user can audit your column choice.

After this skill, hand off to **tc-bigtable-aggregate** if the task requires grouping or ranking across area columns (col 1–6 in the typical 区县 layout: row5 names `区域(第1层级-编码)`, `区域(第1层级)`, `区域(第2层级-编码)`, `区域(第2层级)`, `区域(第3层级-编码)`, `区域`).
