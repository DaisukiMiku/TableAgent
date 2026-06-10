# 实验评测

> 最后更新：2026-06-10

本目录维护 TableClaw 当前主线评测：skill-on/off 对照、workflow skill routing、以及最新的 uploaded-table workflow。评测重点是模型是否选择 table skills、选择时机、是否会从 `workspace/uploads/` 召回相关表、工具轨迹、token usage、以及端到端编排是否跑通。

## 子目录

| 子目录 | 实验线 | 用途 |
| --- | --- | --- |
| [`skill-matrix/`](skill-matrix/) | **Skill Matrix（开发主线）** | 12 任务 × skill-on/off 全量评测，验证 builtin table skills 在简单/中等/复杂/workflow 任务上是否提供端到端价值。 |
| [`workflow-routing.md`](workflow-routing.md) | **Workflow Routing** | 2 个新增 workflow task，观察 `table-read` / `table-clean` / `table-validate` / `table-report` 的分阶段选择。 |
| [`uploaded-table-workflow/`](uploaded-table-workflow/) | **Uploaded Table Workflow** | 模拟用户已上传工业表，跑通 `workspace/uploads -> retrieval -> inspect/schema cache -> skill workflow`。 |
| `gold-cases/` | **Gold Cases** | 人工整理的标准问答/图表数据 case；当前 `gold_cases.jsonl` 含 40 条，默认全量。 |

## 怎么选

- **列出任务**：`./eval.sh --list-tasks`。
- **跑全量主线评测**：`./eval.sh`。
- **只跑 hard 任务**：`./eval.sh --difficulty hard`。
- **只跑 workflow 任务**：`./eval.sh --case workflow`。
- **只跑单题**：`./eval.sh --task-id tc_hard_003`。
- **跑 uploaded-table workflow**：`./eval.sh --raw-cleaned --limit 10 --modes skill-on`。
- **列出 gold cases 全 40 条**：`./eval.sh --gold-cases --list-tasks`。
- **跑 gold cases 全 40 条**：`./eval.sh --gold-cases --modes skill-on`。
- **并行跑 gold cases 全 40 条并自动判分**：`./eval_gold_parallel.sh --concurrency 4`。
- **看长期 token 消耗**：`nanobot/.venv/bin/python eval_test/summarize_usage.py`，读 `workspace/usage/usage.jsonl`。

## 维护规则

- skill matrix 主线任务集：`eval_test/test_dataset/tasks.jsonl`。
- uploaded-table workflow 任务源：`eval_test/test_dataset/raw_eval_cleaned.jsonl`，当前先默认抽 10 条，不做全量。
- gold cases 任务源：`eval_test/test_dataset/gold_cases.jsonl`，由 `eval_test/test_dataset/source/测试case抽样.xlsx` 导入；标准答案不进 prompt。
- skill-on 使用 `nanobot/configs/tableclaw-bailian-dashscope.json`。
- skill-off 使用 `nanobot/configs/tableclaw-bailian-dashscope-no-xlsx-skill.json`，通过 `disabledSkills` 禁用 `xlsx` 与 TableClaw 轻量 table skills。
- 评测输出默认写入 `eval_test/results/skill_matrix/latest_eval.json` 和 `docs/实验评测/skill-matrix/latest-eval-summary.md`。
- uploaded-table workflow 的运行态表格、索引和 schema cache 写入 `workspace/uploads/`、`workspace/table_index/`、`workspace/table_cache/`；它们是模拟用户上传状态，不进入 git。

## Gold Benchmark 判分

正式 gold benchmark 入口是 `./eval_gold_parallel.sh --concurrency 4`。它复用当前 Nanobot workflow 生成答案，不把标准答案注入 prompt；完成后再用 DeepSeek `deepseek-v4-pro` 作为 LLM judge，对 `answer` 和 `gold_answer` 做语义比较。

同时记录两类轻量确定性指标：

- numeric F1：从答案和 gold 中抽取数字，兼容百分比和小数表达。
- entity F1：抽取省份、市州、业务指标等核心实体词，做粗粒度覆盖率检查。

输出位置：

- `eval_test/results/gold_cases/parallel/latest_results.jsonl`：每条 case 的 answer/gold/judge/工具轨迹。
- `eval_test/results/gold_cases/parallel/latest_summary.json`：机器可读汇总。
- `docs/实验评测/gold-cases/latest-parallel-eval-summary.md`：人工阅读报告。

当前可复现实验协议和 baseline 结果记录在 [`gold-cases/gold-benchmark-protocol.md`](gold-cases/gold-benchmark-protocol.md)。后续优化 retrieval、schema cache、table tools 或 skills 后，优先复跑同一命令并更新该文档的 baseline/对比结果。
