# 实验评测

> 最后更新：2026-05-29

本目录按"实验线"分两个子目录维护，避免不同时期的实验互相串。

## 子目录

| 子目录 | 实验线 | 用途 |
| --- | --- | --- |
| [`mentor-demo/`](mentor-demo/) | **Mentor Demo（短期对外演示）** | 单一复合任务在欠费表上的 skill-on / skill-off 双轨迹对照，配 2 个针对宽表难点的 tc-bigtable-* skill。给 mentor 看 "agent 在不同步骤命中不同小 skill" 的画面。 |
| [`skill-matrix/`](skill-matrix/) | **Skill Matrix（开发主线）** | 10 任务 × skill-on/off 全量评测，验证 builtin xlsx skill（codex 原文）在简单/中等/复杂任务上是否提供端到端价值。仍是产品长期路线的一部分。 |

## 怎么选

- **要给 mentor 演示**：看 [`mentor-demo/pipeline.md`](mentor-demo/pipeline.md)，跑 `./demo.sh`。
- **看产品级 skill 价值评估**：看 [`skill-matrix/xlsx-skill-selection-matrix.md`](skill-matrix/xlsx-skill-selection-matrix.md)，跑 `./eval.sh`。
- **要看长期 token 消耗**：跑 `nanobot/.venv/bin/python eval_test/summarize_usage.py`，读 `workspace/usage/usage.jsonl`。

## 维护规则

- mentor-demo 和 skill-matrix 各自独立的 SKILL 集合：
  - mentor-demo 用 `tc-bigtable-header` + `tc-bigtable-aggregate`
  - skill-matrix 用 `xlsx`（codex 原文）
- 两条线的 disabledSkills 配置在 `nanobot/configs/` 各自分开维护。
- 每次 `./demo.sh` 跑完会向 `eval_test/results/mentor_demo/runs/<时间戳>/` 写一份归档，永远不覆盖历史。
