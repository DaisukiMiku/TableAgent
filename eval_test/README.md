# TableClaw Eval Test

This directory contains evaluation datasets and runners for TableClaw on spreadsheet question-answering tasks.

## Layout

```text
eval_test/
├── README.md
├── run_eval.py            # 10-task skill-matrix runner (./eval.sh)
├── run_demo.py            # mentor demo runner (./demo.sh)
├── summarize_usage.py     # long-running usage log aggregator
├── results/
│   ├── skill_matrix/      # ./eval.sh outputs (10 tasks × skill-on/off)
│   └── mentor_demo/
│       ├── run.json       # latest run, regenerated each call
│       ├── timeline_*.json
│       └── runs/<ts>/     # timestamped archive of every run (kept locally)
└── test_dataset/
    ├── README.md
    ├── manifest.json
    ├── tasks.jsonl        # 10 unified tasks (skill matrix line)
    ├── demo_tasks.jsonl   # 1 composite task for mentor demo
    └── tables/
        ├── 区县数据-欠费数据.xlsx                # mentor demo table (228×318, 5-row merged header)
        └── 市州数据-营业收现率台账.xlsx           # skill matrix table (29×54, two-row header)
```

## Two Eval Lines

| Line | Runner | Config | Skill | Dataset | Report |
| --- | --- | --- | --- | --- | --- |
| **Mentor Demo** | `./demo.sh` | `tableclaw-demo-skill-{on,off}.json` | `tc-bigtable-header` + `tc-bigtable-aggregate` | `demo_tasks.jsonl` (1 task) | [`docs/实验评测/mentor-demo/pipeline.md`](../docs/实验评测/mentor-demo/pipeline.md) |
| **Skill Matrix** | `./eval.sh` | `tableclaw-bailian-dashscope*.json` | `xlsx` (codex 原文) | `tasks.jsonl` (10 tasks) | [`docs/实验评测/skill-matrix/xlsx-skill-selection-matrix.md`](../docs/实验评测/skill-matrix/xlsx-skill-selection-matrix.md) |

These two lines have different skills, configs, datasets, and reports. They share `summarize_usage.py` for runtime token statistics.

## Dataset Boundary

`test_table/` is the raw industrial table pool. `eval_test/test_dataset/` is the cleaned eval subset.

Do not put eval datasets in `workspace/`. The workspace is nanobot runtime state: memory, sessions, and user-level skills. Evaluation data should be a project asset so it can be reviewed, versioned, and reused independently.

## Common Commands

```bash
# Mentor demo (composite task on the wide arrears table)
./demo.sh
./demo.sh --modes skill-on

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
- `results/mentor_demo/run.json` + per-mode `timeline_*.json`
- `../docs/实验评测/mentor-demo/pipeline.md`

Each `./demo.sh` call also writes a frozen snapshot to `results/mentor_demo/runs/<timestamp>/`, so previous trajectories are preserved.

Runtime usage logs are appended during normal TableClaw conversations:

```bash
nanobot/.venv/bin/python eval_test/summarize_usage.py
```

Log file: `../workspace/usage/usage.jsonl`.
