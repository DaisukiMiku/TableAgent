# 2026-06-16 v4rerun Five-Way Eval

## Summary

| Item | Value |
| --- | --- |
| Agent / domain version | v4rerun: rollback v5 extra domain patches; keep v4 mandatory overrides and generic tools |
| Model | `deepseek-v4-pro` via DashScope compatible API |
| Judge prompt | `data-correctness-v3-2026-06-15` |
| Runs | 2 x badcase122, 3 x query100 random splits |
| badcase122 完整 ACC | 88.93% |
| query100 完整 ACC | 89.00% |

完整 ACC 是本次主线汇报口径：只修正小数点、单位换算、报表舍入导致的明显 judge 误判；错月份、错指标、缺实体、排序/排名错误不调整。逐条机器明细保留在 `eval_test/results/`，本文档不再把原始 judge ACC 作为主指标展示。

## Run Results

| Run | Dataset | 完整口径修正 cases | 完整 ACC | Avg tokens | Avg seconds | Report |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `badcase122-v4rerun-a` | `eval_test/test_dataset/bad_cases.jsonl` | 36, 75, 99, 103 | 91.80% | 314001 | 109.2 | `eval_test/results/bad_cases/parallel/v4rerun-a/2026-06-16-badcase122-v4rerun-a_report.md` |
| `badcase122-v4rerun-b` | `eval_test/test_dataset/bad_cases.jsonl` | 21, 71, 97, 103 | 86.07% | 301369 | 111.3 | `eval_test/results/bad_cases/parallel/v4rerun-b/2026-06-16-badcase122-v4rerun-b_report.md` |
| `query100-v4rerun-base` | `eval_test/test_dataset/query_variants_100.jsonl` | 23, 69 | 88.00% | 312801 | 120.3 | `eval_test/results/query_variants/parallel/v4rerun-base/2026-06-16-queryvar100-v4rerun-base_report.md` |
| `query100-v4rerun-seed20260616` | `eval_test/test_dataset/query_variants_100_seed20260616.jsonl` | 46 | 89.00% | 315116 | 118.0 | `eval_test/results/query_variants/parallel/v4rerun-seed20260616/2026-06-16-queryvar100-v4rerun-seed20260616_report.md` |
| `query100-v4rerun-seed20260617` | `eval_test/test_dataset/query_variants_100_seed20260617.jsonl` | 21, 46, 59 | 90.00% | 327725 | 125.9 | `eval_test/results/query_variants/parallel/v4rerun-seed20260617/2026-06-16-queryvar100-v4rerun-seed20260617_report.md` |

## Query Split Notes

- `query_variants_100.jsonl`: 旧随机 100 条。
- `query_variants_100_seed20260616.jsonl`: 第二组随机 100 条，和旧 split 约 75 条不同。
- `query_variants_100_seed20260617.jsonl`: 第三组随机 100 条，和旧 split 约 79 条不同，和 seed20260616 约 82 条不同。

## Interpretation

- query100 三个 split 的完整 ACC 平均为 89.00%，单次结果为 88.00%、89.00%、90.00%，说明 query 改写泛化能力比单一旧 split 更可信。
- badcase122 两轮完整 ACC 平均为 88.93%，单次结果为 91.80%、86.07%。第二轮偏低主要来自模型路径漂移和若干排名/口径错误，说明 badcase 仍存在 run-to-run 波动。
- v5 额外补 domain knowledge 后没有带来稳定提升，说明继续堆 JSON badcase patch 的边际收益变低；下一轮更应该做 workflow/reconciliation，而不是继续扩大 domain override。
- 当前建议把本次作为 v4rerun 归档结果：query 泛化表现可用，badcase 仍有 run-to-run 波动。

## Next Improvement Direction

- 固定 judge prompt，不再随 agent 版本频繁回退或放宽。
- 对 `mandatory_overrides` 增加结构化执行/reconciliation，而不是只把知识返回给模型阅读。
- 对明显歧义 query（只写“2月”、无年份、断句缺主体）单独标记 ambiguous，不混入硬 ACC。
- 小数点/单位舍入建议进入 deterministic post-check，作为完整口径的一部分稳定记录，避免每轮人工重复修正。
