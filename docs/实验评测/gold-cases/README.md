# Gold Cases

> 当前主线：40 条人工 gold cases 的 TableClaw workflow benchmark。

## 推荐阅读

| 文档 | 用途 |
| --- | --- |
| [Benchmark Protocol](gold-benchmark-protocol.md) | 主入口。说明 prompt、workflow、judge 方法、指标口径和 2026-06-10 baseline。 |
| [Run History](runs/README.md) | 每一版 40-case benchmark 的版本化记录，含 prompt/workflow 特点与指标对比。 |
| [Latest Parallel Eval Summary](latest-parallel-eval-summary.md) | 最近一次 40-case 并行评测的逐题结果、answer/gold 对比和 judge 原因；该文件会滚动覆盖。 |
| [Smoke Eval Summary](smoke-eval-summary.md) | 历史 smoke。只验证首条 gold case 能跑通，不代表当前 benchmark 结果。 |

## 已保留的正式 Run

| Run | 特点 | ACC |
| --- | --- | ---: |
| [v1-baseline](runs/2026-06-10-v1-baseline-acc40.md) | retrieve + inspect + 按需 skill/code，不强推新增读算工具 | 40.00% |
| [v2-forced-tools](runs/2026-06-10-v2-forced-tools-acc37_5.md) | prompt 显式要求优先使用 locate/topk/filter/extract_series | 37.50% |
| [v3-loose-tools](runs/2026-06-10-v3-loose-tools-acc40.md) | 工具可用但 prompt 不点名、不强制，由模型自主选择 skill/tool/code | 40.00% |

当前结论：workflow 编排已经跑通；工具要作为 affordance 暴露给模型，而不是在 prompt 中变成强制流程。v3 说明宽松工具策略能把 ACC 拉回 baseline，并提升平均分与实体 F1，但 token 和耗时升高。下一步优先控制长尾探索，并增强表格召回/定位。
