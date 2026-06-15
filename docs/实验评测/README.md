# 实验评测

> 最后更新：2026-06-15

本目录现在只维护 TableClaw 主线 benchmark。早期 `skill-matrix`、uploaded-table smoke、workflow routing demo 已从文档主线清理，避免和当前 gold benchmark 混在一起。

## 当前主线

| 入口 | 用途 |
| --- | --- |
| [gold-cases/](gold-cases/) | 40 条人工 gold cases，当前最重要的端到端 benchmark。 |
| [gold-cases/gold-benchmark-protocol.md](gold-cases/gold-benchmark-protocol.md) | prompt、workflow、judge、指标和输出文件说明。 |
| [gold-cases/runs/](gold-cases/runs/) | 已归档的正式 run 摘要。当前只保留关键里程碑报告，旧细节可从 git 历史恢复。 |
| [gold-cases/latest-parallel-eval-summary.md](gold-cases/latest-parallel-eval-summary.md) | 当前最新主线评测指针；滚动报告默认写入 `eval_test/results/gold_cases/parallel/latest_report.md`。 |
| [gold-cases/runs/2026-06-15-domain-overrides-rank-filter.md](gold-cases/runs/2026-06-15-domain-overrides-rank-filter.md) | 最新归档：gold40 A/B 与 badcase122 A/B/C，记录 rank filter、domain override 和最新回归结果。 |

## 常用命令

```bash
# 列出 40 条 gold cases
./eval_gold_parallel.sh --list-tasks

# 跑完整 40 case，并行数按当前 API 额度调整
./eval_gold_parallel.sh --concurrency 8
./eval_gold_parallel.sh --task-file eval_test/test_dataset/gold_cases.jsonl --concurrency 10

# 跑 122 条 badcase
./eval_gold_parallel.sh --task-file eval_test/test_dataset/bad_cases.jsonl --concurrency 10

# 跑单条或小批 targeted case
./eval_gold_parallel.sh --concurrency 4 --case-index 1

# 查看 token usage 长期统计
nanobot/.venv/bin/python eval_test/summarize_usage.py
```

## 判分口径

- 标准答案不进入 prompt，只在 evaluator 阶段使用。
- LLM judge 当前使用 OpenAI-compatible `deepseek-v4-pro`。
- 当前 judge prompt 版本：`data-correctness-v2-2026-06-14`。
- 图表题暂时只评测底层数据、数值、实体和口径是否正确；图形美观、前端排版、颜色样式不作为当前核心指标。
- `partial` 会单独统计，但不计入 ACC passed。
- 辅助指标包括 numeric F1、entity F1、耗时、token、TableClaw tool 调用轨迹。

## 输出位置

- `eval_test/results/gold_cases/parallel/latest_results.jsonl`
- `eval_test/results/gold_cases/parallel/latest_summary.json`
- `eval_test/results/gold_cases/parallel/runs/<run_id>_results.jsonl`
- `eval_test/results/gold_cases/parallel/runs/<run_id>_summary.json`
- `eval_test/results/gold_cases/parallel/latest_report.md`
- `docs/实验评测/gold-cases/runs/<run_id>.md`（正式归档时手动保存）

## 维护规则

- 每次架构性改动后，优先跑 targeted cases，再跑 full40。
- 每个正式 full40 需要记录 run id、模型、prompt 策略、tool/skill 暴露方式、ACC、耗时、token 和主要结论。
- `latest` 是滚动结果；重要版本必须另存到 `gold-cases/runs/`。
- 不再把一次性展示任务、mentor demo、临时 smoke 作为正式评测线维护。
