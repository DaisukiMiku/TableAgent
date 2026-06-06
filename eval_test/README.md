# TableClaw Eval Test

This directory contains evaluation datasets and runners for TableClaw on spreadsheet question-answering tasks.

## Layout

```text
eval_test/
├── README.md
├── run_eval.py            # 10-task skill-matrix runner (./eval.sh)
├── summarize_usage.py     # long-running usage log aggregator
├── results/
│   └── skill_matrix/      # ./eval.sh outputs (10 tasks × skill-on/off)
└── test_dataset/
    ├── README.md
    ├── manifest.json
    ├── tasks.jsonl        # 10 unified tasks (skill matrix line)
    └── tables/
        └── 市州数据-营业收现率台账.xlsx           # skill matrix table (29×54, two-row header)
```

## Main Eval Line

| Line | Runner | Config | Skill | Dataset | Report |
| --- | --- | --- | --- | --- | --- |
| **Skill Matrix** | `./eval.sh` | `tableclaw-bailian-dashscope*.json` | `xlsx` (Codex 原文) | `tasks.jsonl` (10 tasks) | [`docs/实验评测/skill-matrix/xlsx-skill-selection-matrix.md`](../docs/实验评测/skill-matrix/xlsx-skill-selection-matrix.md) |

`run_eval.py` compares `skill-on` and `skill-off`, records tool timelines, detects whether the builtin `xlsx` skill was read, and writes token usage snapshots.

## Dataset Boundary

`test_table/` is the raw industrial table pool. `eval_test/test_dataset/` is the cleaned eval subset.

Do not put eval datasets in `workspace/`. The workspace is nanobot runtime state: memory, sessions, and user-level skills. Evaluation data should be a project asset so it can be reviewed, versioned, and reused independently.

## Common Commands

```bash
# Skill matrix (10-task ablation on the city-level cash-collection table)
./eval.sh
./eval.sh --list-tasks
./eval.sh --difficulty hard
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
