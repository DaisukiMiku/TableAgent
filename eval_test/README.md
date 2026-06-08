# TableClaw Eval Test

This directory contains evaluation datasets and runners for TableClaw on spreadsheet question-answering tasks.

## Layout

```text
eval_test/
├── README.md
├── eval_test.csv          # raw historical eval export, kept as source data
├── clean_eval_csv.py      # cleans eval_test.csv into deduped retrieval/eval candidates
├── run_eval.py            # 12-task skill-matrix runner (./eval.sh)
├── run_retrieval_smoke.py # workspace upload + table retrieval + Nanobot skill workflow smoke runner
├── summarize_usage.py     # long-running usage log aggregator
├── results/
│   └── skill_matrix/      # ./eval.sh outputs (10 tasks × skill-on/off)
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
| **Retrieval Smoke** | `./eval_retrieval.sh` | `tableclaw-bailian-dashscope.json` | retrieved candidates + builtin table skills | `raw_eval_cleaned.jsonl` (default mixed 10 tasks) | [`docs/实验评测/retrieval-smoke.md`](../docs/实验评测/retrieval-smoke.md) |

`run_eval.py` compares `skill-on` and `skill-off`, records tool timelines, detects whether the builtin `xlsx` skill was read, and writes token usage snapshots.

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

Do not put eval datasets in `workspace/`. The workspace is nanobot runtime state: memory, sessions, and user-level skills. Evaluation data should be a project asset so it can be reviewed, versioned, and reused independently.

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
```

Primary outputs (regenerated on every run):

- `results/skill_matrix/latest_eval.json`
- `../docs/实验评测/skill-matrix/latest-eval-summary.md`

Runtime usage logs are appended during normal TableClaw conversations:

```bash
nanobot/.venv/bin/python eval_test/summarize_usage.py
```

Log file: `../workspace/usage/usage.jsonl`.

## Retrieval Smoke

To simulate a user who has uploaded many industrial tables into the agent workspace:

```bash
./eval_retrieval.sh --dry-run --limit 10 --top-k 8
./eval_retrieval.sh --limit 10 --top-k 8
```

The runner copies usable files from `test_table/` into `workspace/uploads/`, builds `workspace/table_index/tables.jsonl`, retrieves candidate tables from the question, and then passes only retrieved candidates to Nanobot. It does not pass gold table paths to the prompt.

This line is a workflow smoke test, not a final accuracy benchmark. It records retrieval candidates, skill-read sequence, tool usage, token usage, elapsed time, and answer preview.
