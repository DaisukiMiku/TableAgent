# Gold Cases Benchmark

> 当前主线：40 条人工 gold cases 的 TableClaw workflow benchmark。

## 推荐阅读

| 文档 | 用途 |
| --- | --- |
| [Benchmark Protocol](gold-benchmark-protocol.md) | 主入口。说明 prompt、workflow、judge 方法、指标口径和输出文件。 |
| [Run History](runs/README.md) | 关键版本的 full40 结果、指标和结论。 |
| [Latest Summary](latest-parallel-eval-summary.md) | 最近一次运行的滚动报告，会被覆盖，不作为唯一历史记录。 |
| [DeepSeek 80% Run](runs/2026-06-12-current-full40-after-horizontal-series.md) | 当前已归档 DeepSeek 最高 full40，ACC 80.00%。 |
| [GPT-5.5 Run](runs/2026-06-12-gpt55-current-full40.md) | 强基模参考上限，ACC 82.50%，用于轨迹蒸馏和上限分析。 |

## 当前结论

- TableClaw workflow 已经跑通：用户问题 -> 上传表召回 -> schema/cache/catalog -> skill/tool/code -> answer -> judge。
- 强制模型使用某些工具通常会伤害基模发挥；工具应作为 affordance 暴露，prompt 只给任务目标和必要输出约束。
- 最有效的工具形态是输出接近最终答案的可复制底表，例如 matrix/time-series/horizontal-series，而不是只返回低层 JSON。
- DeepSeek 主线历史最高为 80.00% ACC；GPT-5.5 可到 82.50%，说明现有工具层仍有可迁移价值。
- 主要短板仍是 2025-12 sparse 表、固定/隐含业务 cohort、多条件 filter、欠费台账多 sheet/多级表头，以及表族选择不稳。

## 已保留的正式 Run

| Run | 特点 | ACC |
| --- | --- | ---: |
| DeepSeek current full40 after horizontal series | answer_markdown + 横向序列/台账类底表输出，当前 DeepSeek 最高归档 | 80.00% |
| GPT-5.5 current full40 | 强基模上限和轨迹参考，不与 DeepSeek 主线混口径比较 | 82.50% |

早期 v1-v10 的指标摘要保留在 [Run History](runs/README.md)。对应长篇逐题报告已从主线文档中清理，避免文档膨胀；需要时从 git 历史恢复。

## 下一步评测重点

- 用 DeepSeek 重新跑 domain pack 后的 targeted set 和 full40，确认四川财资知识层的真实收益。
- 处理 `eval_test/300条badcase.xlsx`，建立 badcase -> domain knowledge / tool / prompt 三类反馈闭环。
- 给 gold cases 标注 gold table mapping，用 Recall@k 拆分“召回错表”和“表内读算错误”。
- 对图表题继续坚持“底层数据优先”，前端图形美化后置。
