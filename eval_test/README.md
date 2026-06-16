# TableClaw Eval Test

This directory contains evaluation datasets and runners for TableClaw on spreadsheet question-answering tasks.

## Layout

```text
eval_test/
├── README.md
├── eval_test.csv          # raw historical eval export, kept as source data
├── clean_eval_csv.py      # cleans eval_test.csv into deduped retrieval/eval candidates
├── import_gold_cases.py   # imports curated xlsx gold cases into gold_cases.jsonl
├── import_bad_cases.py    # imports reviewed badcase xlsx into bad_cases.jsonl
├── run_eval.py            # legacy small eval runner (kept for compatibility)
├── run_gold_parallel_eval.py # current parallel benchmark runner with LLM judge + F1 metrics
├── summarize_usage.py     # long-running usage log aggregator
├── results/
│   ├── gold_cases/        # curated gold40 benchmark outputs
│   ├── bad_cases/         # reviewed badcase benchmark outputs
│   └── query_variants/    # query rewrite generalization outputs
└── test_dataset/
    ├── README.md
    ├── manifest.json
    ├── tasks.jsonl        # legacy 12-task skill/workflow eval set
    ├── raw_eval_cleaned.jsonl  # 165 deduped candidate tasks from eval_test.csv
    ├── raw_eval_cleaned.csv
    ├── raw_eval_cleaning_report.md
    ├── gold_cases.jsonl        # curated gold cases imported from source/测试case抽样.xlsx
    ├── bad_cases.jsonl         # reviewed badcases imported from source/300条badcase.xlsx
    ├── source/
    │   ├── 测试case抽样.xlsx
    │   └── 300条badcase.xlsx
    └── tables/
        └── 市州数据-营业收现率台账.xlsx           # skill matrix table (29×54, two-row header)
```

## Main Eval Line

| Line | Runner | Config | Skill | Dataset | Report |
| --- | --- | --- | --- | --- | --- |
| **Gold40** | `./eval_gold_parallel.sh --task-file eval_test/test_dataset/gold_cases.jsonl --concurrency 8` | `tableclaw-bailian-dashscope-eval.json` + DeepSeek judge | domain skill + TableClaw tools | `gold_cases.jsonl` | `eval_test/results/gold_cases/parallel/latest_report.md` |
| **Badcase122** | `./eval_gold_parallel.sh --task-file eval_test/test_dataset/bad_cases.jsonl --concurrency 10` | same | same | `bad_cases.jsonl` | `eval_test/results/bad_cases/parallel/<run_group>/latest_report.md` |
| **Query100** | `./eval_gold_parallel.sh --task-file eval_test/test_dataset/query_variants_100.jsonl --concurrency 10` | same | same | `query_variants_100*.jsonl` | `eval_test/results/query_variants/parallel/<run_group>/latest_report.md` |
| **Mixed Regression** | `./eval_gold_parallel.sh --task-file eval_test/test_dataset/regression_mixed_*.jsonl --concurrency 10` | same | same | hard + correct_guard subsets | local regression reports |

`run_gold_parallel_eval.py` is the current main evaluation entrypoint. `run_eval.py` and `./eval.sh` are kept for older small ablations and are not the main benchmark line.

## Raw Eval CSV Cleaning

`eval_test.csv` is a raw historical eval export. It contains repeated attempts for the same question, model answers, scores, and review metadata. It is not used directly by `./eval.sh`.

Clean it with:

```bash
python3 eval_test/clean_eval_csv.py
```

Current cleaned output:

- raw rows: 835
- valid rows with question and ground truth: 826
- deduplicated tasks: 165
- chart-generation tasks: 144
- structured table QA tasks: 21

The cleaned chart tasks are retained, but they are marked as `requires_visual_artifact=true`. Their current ground truth is a markdown data table, so the first-stage evaluator should check the underlying data correctness; visual chart quality needs a separate artifact evaluator later.

## Curated Gold Cases

`eval_test/test_dataset/source/测试case抽样.xlsx` is a manually curated gold set with columns `问题` and `标准答案`. It currently contains 40 valid question/answer rows.

Import it with:

```bash
python3 eval_test/import_gold_cases.py
```

Current output:

- `eval_test/test_dataset/gold_cases.jsonl`
- 40 total cases
- default eval selection: all 40 cases via `./eval_gold_parallel.sh --task-file eval_test/test_dataset/gold_cases.jsonl`
- subset selection: `./eval_gold_parallel.sh --case-index 1 --case-index 2`

Gold-case scoring is handled by `run_gold_parallel_eval.py`: the standard answer is preserved in the dataset, never injected into the model prompt, and used only by the evaluator.

For the current benchmark line, use the parallel runner:

```bash
./eval_gold_parallel.sh --task-file eval_test/test_dataset/gold_cases.jsonl --concurrency 8
```

It runs all 40 curated cases with the current Nanobot TableClaw workflow, then compares `answer` vs `gold_answer` using:

- DeepSeek `deepseek-v4-pro` as LLM judge via DashScope OpenAI-compatible API.
- Deterministic numeric F1 over extracted numbers, with percent/decimal equivalence.
- Deterministic entity F1 over core province/city/metric terms.

Outputs:

- `eval_test/results/<dataset>/parallel/<run_group>/latest_results.jsonl`
- `eval_test/results/<dataset>/parallel/<run_group>/latest_summary.json`
- `eval_test/results/<dataset>/parallel/<run_group>/latest_report.md`
- `eval_test/results/<dataset>/parallel/<run_group>/runs/<run_id>_results.jsonl`
- `eval_test/results/<dataset>/parallel/<run_group>/runs/<run_id>_summary.json`

Benchmark protocol, prompt, judge method, and latest official result are documented in:

- `docs/实验评测/gold-cases/gold-benchmark-protocol.md`
- `docs/实验评测/gold-cases/latest-parallel-eval-summary.md`

## Reviewed Bad Cases

`eval_test/test_dataset/source/300条badcase.xlsx` is a reviewed badcase workbook with question, standard answer, previous model answer, review conclusion, review reason, latency, and source id columns.

Import it with:

```bash
python3 eval_test/import_bad_cases.py
```

Current output:

- `eval_test/test_dataset/bad_cases.jsonl`
- 122 valid cases from the workbook
- same top-level schema as `gold_cases.jsonl`: `question`, `ground_truth`, `gold_answer`, `task_type`, `facets`, etc.
- previous model answer / model response / review reason are preserved under `badcase`, but are not injected into the model prompt.

Run it through the same parallel workflow:

```bash
./eval_gold_parallel.sh \
  --task-file eval_test/test_dataset/bad_cases.jsonl \
  --limit 10 \
  --concurrency 4 \
  --run-id badcase-smoke
```

## Dataset Boundary

`test_table/` is the raw industrial table pool. `eval_test/test_dataset/` is the cleaned eval subset.

`eval_test/test_dataset/` is the versioned evaluation asset. `workspace/uploads/` is runtime upload state: during workflow eval it simulates tables that a future web UI has already uploaded for the user. Do not rely on `workspace/` for gold answers or dataset definitions.

## Common Commands

```bash
# Parallel gold40 benchmark
./eval_gold_parallel.sh --task-file eval_test/test_dataset/gold_cases.jsonl --concurrency 8

# Reviewed badcase benchmark
./eval_gold_parallel.sh --task-file eval_test/test_dataset/bad_cases.jsonl --concurrency 10

# Query rewrite generalization benchmark
./eval_gold_parallel.sh --task-file eval_test/test_dataset/query_variants_100.jsonl --concurrency 10

# Targeted cases
./eval_gold_parallel.sh --task-file eval_test/test_dataset/bad_cases.jsonl --case-index 1 --case-index 2 --concurrency 2

# Long-running usage roll-up
nanobot/.venv/bin/python eval_test/summarize_usage.py
```

Primary outputs are regenerated under `eval_test/results/<dataset>/parallel/<run_group>/`.

Log file: `../workspace/usage/usage.jsonl`.

## Legacy Small Eval

`./eval.sh` and `run_eval.py` are retained for old 12-task skill/workflow smoke tests, but they are no longer the main benchmark. The current workflow assumes industrial tables are already present under:

```text
workspace/uploads/
workspace/table_index/tables.jsonl
workspace/table_cache/*.schema.json
```

This mirrors the future web product: uploaded files are saved into workspace first; later user questions do not explicitly include a table path. Nanobot receives the question, calls `tableclaw_retrieve_tables`, inspects the best candidates with `tableclaw_inspect`, chooses table skills, and answers.

Legacy smoke example:

```bash
./eval.sh --raw-cleaned --limit 10 --modes skill-on
```

This line is a workflow orchestration test, not a final accuracy benchmark. Do not add legacy smoke outputs back into the main docs unless they are curated into a formal report.
