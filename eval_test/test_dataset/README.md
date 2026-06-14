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

## Raw Eval Candidates

`raw_eval_cleaned.jsonl` and `raw_eval_cleaned.csv` are generated from `../eval_test.csv` by:

```bash
python3 eval_test/clean_eval_csv.py
```

They are not part of the current 12-task smoke eval. They are candidate tasks for the next retrieval benchmark:

- 835 raw rows.
- 826 rows have non-empty question and ground truth.
- 165 deduplicated tasks after grouping exact question + ground truth.
- 144 tasks require chart/visual output; their current ground truth is only the underlying markdown data table.
- `retrieval_eval_ready=false` until each task is mapped to a real source workbook/table.

Next step: map cleaned questions to source tables, copy those tables into `workspace/uploads/` to simulate user uploads, build a table index, then evaluate question -> table retrieval -> answer workflow.

## Curated Gold And Bad Cases

`gold_cases.jsonl` is imported from `source/测试case抽样.xlsx`:

```bash
python3 eval_test/import_gold_cases.py
```

It currently contains 40 manually curated gold cases.

`bad_cases.jsonl` is imported from `source/300条badcase.xlsx`:

```bash
python3 eval_test/import_bad_cases.py
```

It currently contains 122 reviewed bad cases. The top-level schema matches `gold_cases.jsonl`, so the same runner can evaluate it by switching task file:

```bash
./eval_gold_parallel.sh --task-file eval_test/test_dataset/bad_cases.jsonl --limit 10 --concurrency 4
```

The `badcase` field preserves previous model answer, model response, review conclusion, review reason, latency, and source id for diagnosis. These fields are metadata only and are not injected into the model prompt.
