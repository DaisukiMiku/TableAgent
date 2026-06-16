# 2026-06-16 V3 Final Eight-Way Eval with Gold-Issue Exclusion

## Summary

本次评测使用回退后的 v3 主线代码。先对 5 个已完成 full eval 结果按新评测口径重新汇总，随后追加 1 个 badcase122 run 和 2 个全新 query100 split 做稳定性复核。

新口径会识别明显的 `gold/task issue`，例如：

- 题面要求的指标与 gold answer 明显不一致，例如题面说“应收账款绝对值”，gold 却要求“应收总额同比增幅”。
- 题面缺少年份，但 gold answer 强行假设具体年份。
- query 文本残缺，例如开头就是“月期间...”。

这些 case 会写入 `gold_issue_flags`，并标记 `excluded_from_acc=true`。主 ACC 排除这些数据集问题，同时保留 raw ACC 便于追溯。

此外，本报告同时记录两种准确率：

- `Pre-scored ACC`：排除 gold/task issue，但不应用 deterministic judge adjustment；用于保守核验。
- `Official adjusted ACC`：排除 gold/task issue，并允许单位换算、四舍五入、图表展示等 display-noise 修正；作为当前主指标。

## Aggregate

| Metric | Value |
| --- | ---: |
| Total raw cases | 866 |
| Total scored cases | 813 |
| Excluded gold/task issue cases | 53 |
| Deterministic judge-adjusted cases | 29 |
| Pre-scored ACC | 92.50% |
| Raw ACC after display adjustment | 94.57% |
| Official adjusted ACC | 95.20% |
| Badcase122 official adjusted ACC | 96.55% |
| Query100 official adjusted ACC | 94.19% |

## Runs

| Run | Dataset | Rows | Scored | Excluded | Judge adjusted | Pre-scored ACC | Official adjusted ACC |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `2026-06-16-final-v3-badcase-a` | badcase122 | 122 | 116 | 6 | 5 | 94.83% | 99.14% |
| `2026-06-16-final-v3-badcase-b` | badcase122 | 122 | 116 | 6 | 2 | 93.97% | 95.69% |
| `2026-06-16-final-v3-query-base` | query100 base | 100 | 92 | 8 | 4 | 92.39% | 94.57% |
| `2026-06-16-final-v3-query-seed20260616` | query100 seed 20260616 | 100 | 95 | 5 | 4 | 91.58% | 94.74% |
| `2026-06-16-final-v3-query-seed20260617` | query100 seed 20260617 | 100 | 93 | 7 | 1 | 93.55% | 93.55% |
| `2026-06-16-v3check-badcase-c` | badcase122 | 122 | 116 | 6 | 4 | 92.24% | 94.83% |
| `2026-06-16-v3check-query-seed20260618` | query100 seed 20260618 | 100 | 93 | 7 | 6 | 88.17% | 93.55% |
| `2026-06-16-v3check-query-seed20260619` | query100 seed 20260619 | 100 | 92 | 8 | 3 | 92.39% | 94.57% |

## Grouped Results

| Group | Raw cases | Scored cases | Excluded | Judge adjusted | Pre-scored ACC | Official adjusted ACC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Original five runs | 544 | 512 | 32 | 16 | 93.36% | 95.70% |
| New three-run stability check | 322 | 301 | 21 | 13 | 91.03% | 94.35% |
| All eight runs | 866 | 813 | 53 | 29 | 92.50% | 95.20% |
| Badcase122 only | 366 | 348 | 18 | 11 | 93.68% | 96.55% |
| Query100 only | 500 | 465 | 35 | 18 | 91.61% | 94.19% |

## Local Artifacts

Adjusted reports for the original five runs are generated under `eval_test/results/**/runs/` with suffix:

- `_gold_issue_adjusted_summary.json`
- `_gold_issue_adjusted_report.md`

These machine artifacts are local eval outputs and are not committed by default.

## Conclusion

在剥离明显 gold/task issue 后，当前 v3 主线在 badcase 和 query variant 两类集合上的综合表现已经稳定接近 95%：

- badcase122 三轮 official adjusted ACC 为 96.55%，pre-scored ACC 为 93.68%，说明当前 domain pack + generic tools 对已知业务场景回归稳定。
- query100 五轮 official adjusted ACC 为 94.19%，pre-scored ACC 为 91.61%，说明换 query 后仍有较好的泛化性，但明显低于 badcase，符合“回归集更稳、改写集更难”的预期。
- 八轮总计 official adjusted ACC 为 95.20%，pre-scored ACC 为 92.50%。这说明高分不完全依赖 display-noise 后处理；即使保守口径也在 90%+。
- 后续优化应继续关注 query rewrite 下的时间表达、指标别名、表族选择和 sparse/reporting reconciliation，而不是继续扩大 domain hardcode。
