# Test Dataset

Unified spreadsheet QA eval dataset for TableClaw.

## Source Table

- Original source: `test_table/市州数据-营业收现率台账.xlsx`
- Dataset copy: `tables/市州数据-营业收现率台账.xlsx`
- Sheet: `Sheet1`
- Shape: 29 rows x 54 columns
- Structure: columns A-B identify the unit, then each month has two metrics:
  - `营业收现率完成`
  - `经营活动现金流入完成`

## Tasks

Tasks live in `tasks.jsonl`, one JSON object per line.

The current dataset has 12 tasks across three difficulty levels:

- `simple`: direct lookup, threshold filtering, basic count.
- `medium`: top/bottom ranking, cross-period change, threshold ranking.
- `hard`: multi-period set comparison, conjunction filtering, aggregation.
- `workflow`: staged tasks that ask the agent to read structure, clean scope, validate evidence, and produce a report.

These tasks verify table reading, two-level header interpretation, filtering, ranking, numeric precision, total-row exclusion, cross-period calculation, and aggregation.

The `case` field is used by eval scripts for focused runs:

- `simple`: lightweight skill-selection comparison.
- `medium`: ordinary spreadsheet QA.
- `complex`: harder skill-selection comparison.
- `workflow`: multi-stage skill-routing comparison.
