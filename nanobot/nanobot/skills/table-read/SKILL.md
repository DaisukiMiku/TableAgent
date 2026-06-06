---
name: "Table Read"
description: "Use this skill when the task needs to inspect spreadsheet structure, identify sheets, dimensions, header levels, merged cells, period/metric columns, unit columns, total rows, or locate the columns needed before analysis."
---

# Table Read

Use this skill at the start of table work when the workbook structure is not yet known or the user asks for schema, fields, periods, metrics, dimensions, or where data lives.

## Workflow

1. Inspect workbook metadata: sheet names, active sheet, row count, column count, merged ranges.
2. Detect header layout before calculating:
   - single-row header
   - multi-row header
   - merged period/group headers
   - blank cells that inherit a merged header value
3. Locate identifier columns such as unit, code, date, product, customer, or account.
4. Locate target metric columns by combining all relevant header rows.
5. Identify total/subtotal rows such as `合计`, `总计`, `小计`, `市州合计`, `Grand Total`.
6. Return the structure summary before doing final numeric analysis when the question is multi-step.

## Preferred Tools

- Use Python with `openpyxl` for `.xlsx`.
- Use `data_only=True` when reading computed cell values.
- Preserve original numeric precision; do not round during calculation.
- If a direct file preview is truncated, switch to a focused Python inspection script instead of reading the whole workbook as text.

## Output Contract

For structure answers, include:

- workbook path and sheet
- rows x columns
- header rows used
- identifier columns
- period/metric mapping
- excluded total/subtotal rows
- any uncertainty or ambiguous header cells
