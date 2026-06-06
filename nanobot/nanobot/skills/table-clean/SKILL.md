---
name: "Table Clean"
description: "Use this skill when the task needs to normalize spreadsheet data before analysis, handle blank rows, merged headers, total/subtotal exclusion, type conversion, duplicate detection, missing values, or stable analysis-ready records."
---

# Table Clean

Use this skill after table structure is known and before ranking, filtering, aggregation, report generation, or validation.

## Cleaning Rules

1. Never silently include total/subtotal rows in unit-level analysis.
2. Expand merged headers logically in memory; do not edit the source file unless the user asks.
3. Drop fully blank trailing rows and columns.
4. Keep source row numbers and source column indexes in intermediate records so results can be traced.
5. Convert numeric cells carefully:
   - preserve `int`/`float` precision
   - treat `None`, empty strings, `-`, and `N/A` as missing
   - report non-numeric values found in numeric metrics
6. If duplicate unit/key rows appear, report them before aggregating.

## Output Contract

When cleaning affects the result, state:

- rows included
- rows excluded and why
- missing value count
- duplicate key count
- type conversion issues
- cleaned record count
