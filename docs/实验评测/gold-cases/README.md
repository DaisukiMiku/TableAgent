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
| [v4-table-catalog](runs/2026-06-10-v4-table-catalog.md) | 预先生成 161 张表的 catalog/profile/description，retrieve 融合 catalog 描述 | 47.50% |
| [v5-structured-retrieval](runs/2026-06-10-v5-structured-retrieval.md) | 在 catalog 基础上增加结构化意图解析、硬约束打分和同模板表组召回 | 52.50% |

当前结论：workflow 编排已经跑通；工具要作为 affordance 暴露给模型，而不是在 prompt 中变成强制流程。v4 说明 catalog layer 可以提升整体 ACC 和平均分，v5 进一步证明“先解析时间/粒度/指标族/任务类型，再用结构化约束过滤和分组召回”比纯文本相似度更稳。下一步重点不是继续堆 prompt，而是补 per-case budget、gold table mapping / Recall@k、chart_data，以及表内结构理解中的汇总行过滤和 2025 年 12 月缺失值/合并单元格处理。
