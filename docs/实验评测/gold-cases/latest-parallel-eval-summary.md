# Gold Cases Latest Eval Pointer

> 本文件只维护“当前最新主线评测”的指针，下一轮正式 full40 后可以覆盖更新。
> 关键里程碑必须另存到 `runs/`，避免被 latest 滚动覆盖。

## Current Latest

| Item | Value |
| --- | --- |
| Run | [v4rerun Five-Way Eval](runs/2026-06-16-v4rerun-fiveway-eval.md) |
| Date | 2026-06-16 |
| Model | `deepseek-v4-pro` |
| Judge prompt | `data-correctness-v3-2026-06-15` |
| Cases | 122 badcase x 2 repeats; query variant 100 x 3 random splits |
| Average ACC | badcase122 raw 85.66% / 完整 ACC 88.93%; query100 raw 87.00% / 完整 ACC 89.00% |
| Main Insight | v4rerun 回退了 v5 额外 domain patch 后，query 改写泛化平均约 87%-89%；badcase 两轮波动较大，说明继续堆 domain JSON 的收益有限，下一步应做 mandatory override 的结构化 reconciliation。 |

## Update Rule

- 新的正式 full40 / @N 稳定性测试：先在 `runs/` 下创建带日期和语义的归档文件。
- 再更新本文件，让它指向新的归档。
- 不把长篇逐题报告直接塞进本文件；机器明细保留在 `eval_test/results/gold_cases/parallel/runs/`。
