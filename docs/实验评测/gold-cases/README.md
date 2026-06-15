# Gold Cases Benchmark

> 当前主线：40 条人工 gold cases 的 TableClaw workflow benchmark。

## 推荐阅读

| 文档 | 用途 |
| --- | --- |
| [Benchmark Protocol](gold-benchmark-protocol.md) | 主入口。说明 prompt、workflow、judge 方法、指标口径和输出文件。 |
| [Run History](runs/README.md) | 关键版本的 full40 结果、指标和结论。 |
| [Latest Pointer](latest-parallel-eval-summary.md) | 当前最新主线评测指针；正式结果归档在 `runs/`。 |
| [Domain Overrides + Rank Filter](runs/2026-06-15-domain-overrides-rank-filter.md) | 当前最新归档：gold40 A/B 与 badcase122 A/B/C，记录 rank filter、domain override 和最新回归结果。 |
| [Mandatory overrides + judge v2](runs/2026-06-14-mandatory-overrides-judge-v2.md) | 上一轮归档：gold40 A/B 与 badcase122 A/B，记录 judge v2 和 mandatory override 效果。 |
| [DeepSeek after cohort fix @4](runs/2026-06-13-deepseek-v4pro-after-cohort-fix-at4.md) | DeepSeek V4 Pro @4 稳定性里程碑，平均 ACC 82.50%。 |
| [DeepSeek 80% Run](runs/2026-06-12-current-full40-after-horizontal-series.md) | DeepSeek 早期关键里程碑，ACC 80.00%。 |
| [GPT-5.5 Run](runs/2026-06-12-gpt55-current-full40.md) | 强基模参考上限，ACC 82.50%，用于轨迹蒸馏和上限分析。 |

## 当前结论

- TableClaw workflow 已经跑通：用户问题 -> 上传表召回 -> schema/cache/catalog -> skill/tool/code -> answer -> judge。
- 强制模型使用某些工具通常会伤害基模发挥；工具应作为 affordance 暴露，prompt 只给任务目标和必要输出约束。
- 最有效的工具形态是输出接近最终答案的可复制底表，例如 matrix/time-series/horizontal-series，而不是只返回低层 JSON。
- 在接入四川财资 domain pack 并修正 `200亿省` 7 省 cohort 后，DeepSeek V4 Pro full40 @4 平均 ACC 达到 82.50%（77.50% / 82.50% / 87.50% / 82.50%）。
- 最新 `Domain Overrides + Rank Filter` 版本在 badcase122 A/B/C 上达到 88.25% 平均 ACC，单次最高 90.98%；在 gold40 A/B 上达到 78.75% 平均 ACC。
- 这说明 domain pack + 工具层读取领域 cohort 的路线有效：保留通用框架，同时让业务口径以可插拔方式进入工作区。
- 主要短板收敛到 2025-12 `200亿省` 图表族 sparse/reporting fallback、多条件 filter 工具选择、预收排名 reporting 冲突，以及长尾 case 的耗时/token。

## 已保留的正式 Run

| Run | 特点 | ACC |
| --- | --- | ---: |
| Domain Overrides + Rank Filter | rank filter 支持 + 202512 产数 Top3 fallback 加强 + 预收排名 reporting override；gold40 A/B 与 badcase122 A/B/C | gold40 avg 78.75%; badcase122 avg 88.25% |
| Mandatory overrides + judge v2 | `mandatory_overrides` 高优先级 domain fallback + data-correctness judge v2；gold40 A/B 与 badcase122 A/B | gold40 avg 80.00%; badcase122 avg 87.30% |
| DeepSeek after cohort fix @4 | 四川财资 domain pack + `200亿省` 7 省 cohort + `extract_matrix` 自动展开领域 cohort，4 次 full40 稳定性复测 | avg 82.50% |
| DeepSeek current full40 after horizontal series | answer_markdown + 横向序列/台账类底表输出，DeepSeek 早期关键归档 | 80.00% |
| GPT-5.5 current full40 | 强基模上限和轨迹参考，不与 DeepSeek 主线混口径比较 | 82.50% |

早期 v1-v10 的指标摘要保留在 [Run History](runs/README.md)。对应长篇逐题报告已从主线文档中清理，避免文档膨胀；需要时从 git 历史恢复。

## 下一步评测重点

- 继续用 DeepSeek V4 Pro 对 domain pack 迭代做 A/B 或 @4 稳定性复测，避免单次 run 波动误导。
- 处理 `eval_test/300条badcase.xlsx`，建立 badcase -> domain knowledge / tool / prompt 三类反馈闭环。
- 给 gold cases 标注 gold table mapping，用 Recall@k 拆分“召回错表”和“表内读算错误”。
- 对图表题继续坚持“底层数据优先”，前端图形美化后置。
