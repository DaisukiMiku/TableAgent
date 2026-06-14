# Gold Cases Latest Eval Pointer

> 本文件只维护“当前最新主线评测”的指针，下一轮正式 full40 后可以覆盖更新。
> 关键里程碑必须另存到 `runs/`，避免被 latest 滚动覆盖。

## Current Latest

| Item | Value |
| --- | --- |
| Run | [Mandatory overrides + judge v2](runs/2026-06-14-mandatory-overrides-judge-v2.md) |
| Date | 2026-06-14 |
| Model | `deepseek-v4-pro` |
| Judge prompt | `data-correctness-v2-2026-06-14` |
| Cases | 40 gold cases x 2 repeats; 122 badcase x 2 repeats |
| Average ACC | gold40 80.00%; badcase122 87.30% |
| Main Insight | `mandatory_overrides` + judge v2 让 badcase 表现提升到约 87%，但 2025-12 sparse 表、TOP 排序语义和少量疑似 gold/reporting 冲突仍是下一轮重点。 |

## Update Rule

- 新的正式 full40 / @N 稳定性测试：先在 `runs/` 下创建带日期和语义的归档文件。
- 再更新本文件，让它指向新的归档。
- 不把长篇逐题报告直接塞进本文件；机器明细保留在 `eval_test/results/gold_cases/parallel/runs/`。
