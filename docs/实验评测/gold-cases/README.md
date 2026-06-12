# Gold Cases

> 当前主线：40 条人工 gold cases 的 TableClaw workflow benchmark。

## 推荐阅读

| 文档 | 用途 |
| --- | --- |
| [Benchmark Protocol](gold-benchmark-protocol.md) | 主入口。说明 prompt、workflow、judge 方法、指标口径和 2026-06-10 baseline。 |
| [Run History](runs/README.md) | 每一版 40-case benchmark 的版本化记录，含 prompt/workflow 特点与指标对比。 |
| [Case001 TableClaw vs TeleClaw 轨迹对比](runs/2026-06-11-case001-tableclaw-teleclaw-comparison.md) | 记录当前 TableClaw 与当前 TeleClaw 在 case001 上的执行轨迹、耗时、token 消耗和差异。 |
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
| [v6-rank-tool-full40](runs/2026-06-11-v6-rank-tool-full40.md) | 新增 `tableclaw_rank`，将百分比归一化、实体排名、cohort 排名沉淀为确定性工具；case001 修复，但 full40 出现回归 | 45.00% |
| [v7-rank-official-header-path](runs/2026-06-11-v7-rank-official-header-path-full40.md) | rank tool 优先官方排名列、增强 header path 和百分比归一化 | 57.50% |
| [v8-topk-companion-multientity](runs/2026-06-11-v8-topk-companion-multientity-full40.md) | topk companion columns 和多实体输出增强，ranking 强但 chart 回落 | 45.00% |
| [v9h-answer-markdown](runs/2026-06-11-v9h-full40-after-answer-markdown.md) | matrix/time-series 工具输出可直接复制的 answer_markdown/chart table | 67.50% |
| [v10-general-fixes](runs/2026-06-12-v10-full40-general-fixes.md) | 汇总行排除、half-up rounding、占比排名口径和图表/跨期 prompt 约束 | 60.00% |

当前结论：workflow 编排已经跑通；工具要作为 affordance 暴露给模型，而不是在 prompt 中变成强制流程。v9h 是目前最佳 full40（67.50%），关键收益来自 matrix/time-series 工具直接产出可复制的 answer_markdown，减少模型二次改写。v10 的通用修补让 chart_generation 升到 63.64%，但 overall ACC 回落到 60.00%，说明一次性叠加 prompt/工具口径会带来跨类回归。下一步重点不是继续堆 prompt，而是做小步 A/B、per-case budget、gold table mapping / Recall@k、chart/filter 专项，以及对 2025 年 12 月 sparse 表和欠费台账的结构化处理。
