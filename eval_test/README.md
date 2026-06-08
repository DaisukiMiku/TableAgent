# TableClaw Eval Test

This directory contains evaluation datasets and runners for TableClaw on spreadsheet question-answering tasks.

## Layout

```text
eval_test/
├── README.md
├── eval_test.csv          # raw historical eval export, kept as source data
├── clean_eval_csv.py      # cleans eval_test.csv into deduped retrieval/eval candidates
├── run_eval.py            # unified skill-matrix + uploaded-table workflow runner (./eval.sh)
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
    └── tables/
        └── 市州数据-营业收现率台账.xlsx           # skill matrix table (29×54, two-row header)
```

## Main Eval Line

| Line | Runner | Config | Skill | Dataset | Report |
| --- | --- | --- | --- | --- | --- |
| **Skill Matrix** | `./eval.sh` | `tableclaw-bailian-dashscope*.json` | `xlsx` + TableClaw table skills | `tasks.jsonl` (12 tasks) | [`docs/实验评测/skill-matrix/xlsx-skill-selection-matrix.md`](../docs/实验评测/skill-matrix/xlsx-skill-selection-matrix.md) |
| **Uploaded Table Workflow** | `./eval.sh --raw-cleaned --limit 10 --modes skill-on` | `tableclaw-bailian-dashscope.json` | Nanobot builtin retrieval tool + table skills | `raw_eval_cleaned.jsonl` (default mixed 10 tasks) | [`docs/实验评测/uploaded-table-workflow/latest-eval-summary.md`](../docs/实验评测/uploaded-table-workflow/latest-eval-summary.md) |

`run_eval.py` is the single evaluation entrypoint. In the classic skill matrix it compares `skill-on` and `skill-off`; in uploaded-table workflow mode it asks Nanobot to call the builtin `tableclaw_retrieve_tables` tool, then lets the model choose candidate tables and table skills.

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
```

This mirrors the future web product: uploaded files are saved into workspace first; later user questions do not explicitly include a table path. Nanobot receives the question, calls `tableclaw_retrieve_tables`, inspects the best candidates, chooses table skills, and answers.

Run the 10-case workflow eval with:

```bash
./eval.sh --raw-cleaned --limit 10 --modes skill-on \
  --json-output eval_test/results/uploaded_table_workflow/latest_eval.json \
  --md-output docs/实验评测/uploaded-table-workflow/latest-eval-summary.md
```

This line is a workflow orchestration test, not a final accuracy benchmark. It records retrieval-tool calls, skill-read sequence, tool usage, token usage, elapsed time, and answer preview.
