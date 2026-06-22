# 实验评测

> 最后更新：2026-06-22

本目录现在维护两条评测线：

- 业务 domain benchmark：四川财资 gold/badcase/query 主线，评估 domain pack + 通用工具的准确率和稳定性。
- 通用 table task benchmark：非四川财资的真实 workbook/artifact 任务，评估通用 spreadsheet skill、工具调用、输出文件和可验证工作流。

早期 `skill-matrix`、uploaded-table smoke、workflow routing demo 已从文档主线清理，避免和当前正式 benchmark 混在一起。

## 当前主线

| 入口 | 用途 |
| --- | --- |
| [gold-cases/](gold-cases/) | gold40、badcase122、query100 主线 benchmark。 |
| [gold-cases/gold-benchmark-protocol.md](gold-cases/gold-benchmark-protocol.md) | prompt、workflow、judge、指标和输出文件说明。 |
| [gold-cases/runs/](gold-cases/runs/) | 已归档的正式 run 摘要。当前只保留关键里程碑报告，旧细节可从 git 历史恢复。 |
| [gold-cases/latest-parallel-eval-summary.md](gold-cases/latest-parallel-eval-summary.md) | 当前最新主线评测指针。 |
| [gold-cases/runs/2026-06-16-v3-final-gold-issue-adjusted.md](gold-cases/runs/2026-06-16-v3-final-gold-issue-adjusted.md) | 最新正式归档：badcase122 x3 + query100 x5，gold/task issue adjusted ACC 95.20%。 |

## 通用 Table Task

| 入口 | 用途 |
| --- | --- |
| [generic-table-tasks/](generic-table-tasks/) | 第二阶段通用表格上下游任务评测入口。 |
| [generic-table-tasks/hermes-anthropic-xlsx-20260622.md](generic-table-tasks/hermes-anthropic-xlsx-20260622.md) | Hermes 长表清洗、同行对标、预测模型 run；包含 xlsx 产物、JPG 预览、日志、tool trace、token/耗时。 |

## 小集合回归

小集合只用于快速开发迭代，不作为最终成绩。它必须同时包含两类 case：

- `hard`：历史 incorrect / partial / runtime_error，用于验证本轮修复是否命中。
- `correct_guard`：历史 correct 的分层抽样，用于验证本轮修复是否破坏原本稳定的能力。

当前 mixed regression 文件：

| 文件 | 构成 | 用途 |
| --- | --- | --- |
| `eval_test/test_dataset/regression_mixed_badcase_v1.jsonl` | 36 条：20 hard + 16 correct_guard | badcase122 的快速回归，覆盖 ranking/table/chart/trend。 |
| `eval_test/test_dataset/regression_mixed_query_v1.jsonl` | 32 条：16 hard + 16 correct_guard | query variant 的快速回归，重点看改写 query 后是否泛化。 |

每个 mixed 文件旁边都有 `.manifest.json`，记录来源结果、随机种子、case bucket 和 task type 分布。

## 常用命令

```bash
# 列出 40 条 gold cases
./eval_gold_parallel.sh --list-tasks

# 跑完整 40 case，并行数按当前 API 额度调整
./eval_gold_parallel.sh --concurrency 8
./eval_gold_parallel.sh --task-file eval_test/test_dataset/gold_cases.jsonl --concurrency 10

# 跑 122 条 badcase
./eval_gold_parallel.sh --task-file eval_test/test_dataset/bad_cases.jsonl --concurrency 10

# 跑 mixed 小集合回归：修错题时同时看 correct guard 是否退化
./eval_gold_parallel.sh --task-file eval_test/test_dataset/regression_mixed_badcase_v1.jsonl --concurrency 10
./eval_gold_parallel.sh --task-file eval_test/test_dataset/regression_mixed_query_v1.jsonl --concurrency 10

# 重新构造 mixed 小集合（按历史结果抽 hard + correct_guard）
python3 eval_test/build_regression_subset.py \
  --source eval_test/test_dataset/bad_cases.jsonl \
  --results eval_test/results/bad_cases/parallel/final-v3-a/runs/2026-06-16-final-v3-badcase-a_results.jsonl \
  --results eval_test/results/bad_cases/parallel/final-v3-b/runs/2026-06-16-final-v3-badcase-b_results.jsonl \
  --output eval_test/test_dataset/regression_mixed_badcase_v1.jsonl \
  --max-failed 20 \
  --random-correct 16

# 跑单条或小批 targeted case
./eval_gold_parallel.sh --concurrency 4 --case-index 1

# 查看 token usage 长期统计
nanobot/.venv/bin/python eval_test/summarize_usage.py
```

## 判分口径

- 标准答案不进入 prompt，只在 evaluator 阶段使用。
- LLM judge 当前使用 OpenAI-compatible `deepseek-v4-pro`。
- 当前 judge prompt 版本：`data-correctness-v5-2026-06-16`。
- 图表题暂时只评测底层数据、数值、实体和口径是否正确；图形美观、前端排版、颜色样式不作为当前核心指标。
- 如果题面与 gold answer 明显冲突，或题面缺少年份但 gold 强行假设具体年份，runner 会写入 `gold_issue_flags` 并标记 `excluded_from_acc=true`；主 ACC 排除这些 gold/task issue，同时保留 raw ACC 便于追溯。
- `partial` 会单独统计，但不计入 ACC passed。
- 辅助指标包括 numeric F1、entity F1、耗时、token、TableClaw tool 调用轨迹。

## 输出位置

- `eval_test/results/<dataset>/parallel/<run_group>/latest_results.jsonl`
- `eval_test/results/<dataset>/parallel/<run_group>/latest_summary.json`
- `eval_test/results/<dataset>/parallel/<run_group>/runs/<run_id>_results.jsonl`
- `eval_test/results/<dataset>/parallel/<run_group>/runs/<run_id>_summary.json`
- `eval_test/results/<dataset>/parallel/<run_group>/latest_report.md`
- `docs/实验评测/gold-cases/runs/<run_id>.md`（正式归档时手动保存）

## 维护规则

- 每次架构性改动后，优先跑 targeted / mixed cases，再跑 badcase122 和 query100。
- 每个正式 run 需要记录 run id、模型、prompt 策略、tool/skill 暴露方式、raw ACC、gold/task issue adjusted ACC、耗时、token 和主要结论。
- `latest` 是滚动结果；重要版本必须另存到 `gold-cases/runs/`。
- 不再把一次性展示任务、mentor demo、临时 smoke 作为正式评测线维护。
