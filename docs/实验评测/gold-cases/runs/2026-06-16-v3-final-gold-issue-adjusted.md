# 2026-06-16 V3 Final Five-Way Eval with Gold-Issue Exclusion

## Summary

本次评测使用回退后的 v3 主线代码，不重新跑模型，只对已经完成的 5 个 full eval 结果按新评测口径重新汇总。

新口径会识别明显的 `gold/task issue`，例如：

- 题面要求的指标与 gold answer 明显不一致，例如题面说“应收账款绝对值”，gold 却要求“应收总额同比增幅”。
- 题面缺少年份，但 gold answer 强行假设具体年份。
- query 文本残缺，例如开头就是“月期间...”。

这些 case 会写入 `gold_issue_flags`，并标记 `excluded_from_acc=true`。主 ACC 排除这些数据集问题，同时保留 raw ACC 便于追溯。

## Aggregate

| Metric | Value |
| --- | ---: |
| Total raw cases | 544 |
| Total scored cases | 512 |
| Excluded gold/task issue cases | 32 |
| Raw ACC | 95.22% |
| Gold-issue-adjusted ACC | 95.70% |
| Badcase122 adjusted average ACC | 97.41% |
| Query100 adjusted average ACC | 94.28% |

## Runs

| Run | Dataset | Raw ACC | Scored cases | Excluded | Adjusted ACC | Gold issue flags |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `2026-06-16-final-v3-badcase-a` | badcase122 | 98.36% | 116 | 6 | 99.14% | missing year: 5; metric conflict: 1 |
| `2026-06-16-final-v3-badcase-b` | badcase122 | 95.90% | 116 | 6 | 95.69% | missing year: 5; metric conflict: 1 |
| `2026-06-16-final-v3-query-base` | query100 base | 94.00% | 92 | 8 | 94.57% | missing year: 6; broken time expression: 1; metric conflict: 1 |
| `2026-06-16-final-v3-query-seed20260616` | query100 seed 20260616 | 94.00% | 95 | 5 | 94.74% | missing year: 3; broken time expression: 1; metric conflict: 1 |
| `2026-06-16-final-v3-query-seed20260617` | query100 seed 20260617 | 93.00% | 93 | 7 | 93.55% | missing year: 6; metric conflict: 1 |

## Local Artifacts

Adjusted reports are generated under `eval_test/results/**/runs/` with suffix:

- `_gold_issue_adjusted_summary.json`
- `_gold_issue_adjusted_report.md`

These machine artifacts are local eval outputs and are not committed by default.

## Conclusion

在剥离明显 gold/task issue 后，当前 v3 主线在 badcase 和 query variant 两类集合上的综合表现已经稳定接近 95%：

- badcase122 两轮平均 97%+，说明当前 domain pack + generic tools 对已知业务场景覆盖较强。
- query100 三轮平均约 94.3%，说明换 query 后仍有较好的泛化性，但仍低于 badcase，后续优化应继续关注 query rewrite 下的时间表达、指标别名和表族选择。
- 这次提升主要来自更合理的评测统计口径，不代表模型能力本身再次提升；后续新评测会直接使用当前 runner 的 `excluded_from_acc` 主 ACC。
