# 实验评测

> 最后更新：2026-05-29

本目录维护 TableClaw 当前主线评测：12 个表格任务 × skill-on/off，对比 builtin table skills 是否被模型选择、选择时机、答案正确性、token usage 和工具轨迹。

## 子目录

| 子目录 | 实验线 | 用途 |
| --- | --- | --- |
| [`skill-matrix/`](skill-matrix/) | **Skill Matrix（开发主线）** | 12 任务 × skill-on/off 全量评测，验证 builtin table skills 在简单/中等/复杂/workflow 任务上是否提供端到端价值。 |
| [`workflow-routing.md`](workflow-routing.md) | **Workflow Routing** | 2 个新增 workflow task，观察 `table-read` / `table-clean` / `table-validate` / `table-report` 的分阶段选择。 |

## 怎么选

- **列出任务**：`./eval.sh --list-tasks`。
- **跑全量主线评测**：`./eval.sh`。
- **只跑 hard 任务**：`./eval.sh --difficulty hard`。
- **只跑 workflow 任务**：`./eval.sh --case workflow`。
- **只跑单题**：`./eval.sh --task-id tc_hard_003`。
- **看长期 token 消耗**：`nanobot/.venv/bin/python eval_test/summarize_usage.py`，读 `workspace/usage/usage.jsonl`。

## 维护规则

- 主线评测默认只维护一份任务集：`eval_test/test_dataset/tasks.jsonl`。
- skill-on 使用 `nanobot/configs/tableclaw-bailian-dashscope.json`。
- skill-off 使用 `nanobot/configs/tableclaw-bailian-dashscope-no-xlsx-skill.json`，通过 `disabledSkills` 禁用 `xlsx` 与 TableClaw 轻量 table skills。
- 评测输出默认写入 `eval_test/results/skill_matrix/latest_eval.json` 和 `docs/实验评测/skill-matrix/latest-eval-summary.md`。
