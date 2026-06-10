# Gold Cases

> 当前主线：40 条人工 gold cases 的 TableClaw workflow benchmark。

## 推荐阅读

| 文档 | 用途 |
| --- | --- |
| [Benchmark Protocol](gold-benchmark-protocol.md) | 主入口。说明 prompt、workflow、judge 方法、指标口径和 2026-06-10 baseline。 |
| [Latest Parallel Eval Summary](latest-parallel-eval-summary.md) | 最近一次 40-case 并行评测的逐题结果、answer/gold 对比和 judge 原因。 |
| [Smoke Eval Summary](smoke-eval-summary.md) | 历史 smoke。只验证首条 gold case 能跑通，不代表当前 benchmark 结果。 |

## 当前 Baseline

运行命令：

```bash
./eval_gold_parallel.sh --concurrency 8
```

结果摘要：

| Metric | Value |
| --- | ---: |
| Cases | 40 |
| LLM judge ACC | 40.00% |
| Correct / Partial / Incorrect | 16 / 7 / 17 |
| Retrieval call rate | 100.00% |
| Inspect call rate | 100.00% |
| Skill selection rate | 90.00% |
| Total answer tokens | 14,187,768 |

当前结论：workflow 编排已经跑通，但 chart/trend/filter 类任务的表格 grounding、列定位、范围选择和口径判断仍是主要短板。
