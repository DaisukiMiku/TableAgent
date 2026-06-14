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
├── run_eval.py            # unified skill-matrix + uploaded-table workflow runner (./eval.sh)
├── run_gold_parallel_eval.py # parallel 40-case gold eval with LLM judge + F1 metrics
├── summarize_usage.py     # long-running usage log aggregator
├── results/
│   ├── skill_matrix/      # ./eval.sh outputs (12 tasks × skill-on/off)
│   └── uploaded_table_workflow/ # raw-cleaned workflow eval snapshots
└── test_dataset/
    ├── README.md
    ├── manifest.json
    ├── tasks.jsonl        # 12 unified tasks (skill matrix + workflow routing)
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
| **Skill Matrix** | `./eval.sh` | `tableclaw-bailian-dashscope*.json` | `xlsx` + TableClaw table skills | `tasks.jsonl` (12 tasks) | [`docs/实验评测/skill-matrix/xlsx-skill-selection-matrix.md`](../docs/实验评测/skill-matrix/xlsx-skill-selection-matrix.md) |
| **Uploaded Table Workflow** | `./eval.sh --raw-cleaned --limit 10 --modes skill-on` | `tableclaw-bailian-dashscope.json` | Nanobot builtin retrieval tool + table skills | `raw_eval_cleaned.jsonl` (default mixed 10 tasks) | [`docs/实验评测/uploaded-table-workflow/latest-eval-summary.md`](../docs/实验评测/uploaded-table-workflow/latest-eval-summary.md) |
| **Gold Cases** | `./eval.sh --gold-cases --modes skill-on` | `tableclaw-bailian-dashscope.json` | retrieval + inspect + table skills | `gold_cases.jsonl` (40 cases by default) | `docs/实验评测/gold-cases/latest-eval-summary.md` |
| **Parallel Gold Benchmark** | `./eval_gold_parallel.sh --concurrency 4` | `tableclaw-bailian-dashscope.json` + DeepSeek judge | retrieval + inspect + table skills | `gold_cases.jsonl` (40 cases by default; override with `--task-file`) | `eval_test/results/gold_cases/parallel/latest_report.md` |

`run_eval.py` is the single evaluation entrypoint. In the classic skill matrix it compares `skill-on` and `skill-off`; in uploaded-table workflow mode it asks Nanobot to call the builtin `tableclaw_retrieve_tables` tool, inspect candidates with `tableclaw_inspect`, then choose table skills and analysis tools.

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
- default eval selection: all 40 cases via `./eval.sh --gold-cases --modes skill-on`
- subset selection: `./eval.sh --gold-cases --limit 10 --modes skill-on`

Gold-case scoring is intentionally marked as manual/judge-needed for now. The standard answer is preserved in the dataset but is not injected into the model prompt.

For the current benchmark line, use the parallel runner:

```bash
./eval_gold_parallel.sh --concurrency 4
```

It runs all 40 curated cases with the current Nanobot TableClaw workflow, then compares `answer` vs `gold_answer` using:

- DeepSeek `deepseek-v4-pro` as LLM judge via DashScope OpenAI-compatible API.
- Deterministic numeric F1 over extracted numbers, with percent/decimal equivalence.
- Deterministic entity F1 over core province/city/metric terms.

Outputs:

- `eval_test/results/gold_cases/parallel/latest_results.jsonl`
- `eval_test/results/gold_cases/parallel/latest_summary.json`
- `eval_test/results/gold_cases/parallel/latest_report.md`

Benchmark protocol, prompt, judge method, and the 2026-06-10 baseline are documented in:

- `docs/实验评测/gold-cases/gold-benchmark-protocol.md`

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
# Skill matrix (12-task ablation on the city-level cash-collection table)
./eval.sh
./eval.sh --list-tasks
./eval.sh --difficulty hard
./eval.sh --case workflow
./eval.sh --modes skill-on skill-off --task-id tc_hard_003

# Long-running usage roll-up
nanobot/.venv/bin/python eval_test/summarize_usage.py

# Uploaded-table workflow eval: question only -> retrieve from workspace/uploads -> answer
./eval.sh --raw-cleaned --limit 10 --modes skill-on

# Curated gold cases: defaults to all 40 cases
./eval.sh --gold-cases --list-tasks
./eval.sh --gold-cases --modes skill-on
./eval.sh --gold-cases --limit 10 --modes skill-on

# Parallel curated gold benchmark: all 40 cases + LLM judge + F1 metrics
./eval_gold_parallel.sh --concurrency 4

# Reviewed badcase benchmark: same workflow, alternate task file
./eval_gold_parallel.sh --task-file eval_test/test_dataset/bad_cases.jsonl --limit 10 --concurrency 4
```

Primary outputs (regenerated on every run):

- `results/skill_matrix/latest_eval.json`
- `../docs/实验评测/skill-matrix/latest-eval-summary.md`

Runtime usage logs are appended during normal TableClaw conversations:

```bash
nanobot/.venv/bin/python eval_test/summarize_usage.py
```

Log file: `../workspace/usage/usage.jsonl`.

## Uploaded Table Workflow

The current workflow assumes industrial tables are already present under:

```text
workspace/uploads/
workspace/table_index/tables.jsonl
workspace/table_cache/*.schema.json
```

This mirrors the future web product: uploaded files are saved into workspace first; later user questions do not explicitly include a table path. Nanobot receives the question, calls `tableclaw_retrieve_tables`, inspects the best candidates with `tableclaw_inspect`, chooses table skills, and answers.

Run the 10-case workflow eval with:

```bash
./eval.sh --raw-cleaned --limit 10 --modes skill-on \
  --json-output eval_test/results/uploaded_table_workflow/latest_eval.json \
  --md-output docs/实验评测/uploaded-table-workflow/latest-eval-summary.md
```

This line is a workflow orchestration test, not a final accuracy benchmark. It records retrieval-tool calls, skill-read sequence, tool usage, token usage, elapsed time, and answer preview.
