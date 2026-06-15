# Gold Cases Latest Eval Pointer

> 本文件只维护“当前最新主线评测”的指针，下一轮正式 full40 后可以覆盖更新。
> 关键里程碑必须另存到 `runs/`，避免被 latest 滚动覆盖。

## Current Latest

| Item | Value |
| --- | --- |
| Run | [Domain Overrides + Rank Filter](runs/2026-06-15-domain-overrides-rank-filter.md) |
| Date | 2026-06-15 |
| Model | `deepseek-v4-pro` |
| Judge prompt | `data-correctness-v2-2026-06-14` |
| Cases | 40 gold cases x 2 repeats; 122 badcase x 3 repeats |
| Average ACC | gold40 78.75%; badcase122 88.25% |
| Main Insight | badcase122 平均小幅提升到 88.25%，单次最高 90.98%；gold40 略降到 78.75%，主要瓶颈仍是 2025-12 200亿省图表族和 sparse 表 fallback。 |

## Update Rule

- 新的正式 full40 / @N 稳定性测试：先在 `runs/` 下创建带日期和语义的归档文件。
- 再更新本文件，让它指向新的归档。
- 不把长篇逐题报告直接塞进本文件；机器明细保留在 `eval_test/results/gold_cases/parallel/runs/`。
