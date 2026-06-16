# Gold Cases Latest Eval Pointer

> 本文件只维护“当前最新主线评测”的指针，下一轮正式 benchmark 后可以覆盖更新。
> 关键里程碑必须另存到 `runs/`，避免被 latest 滚动覆盖。

## Current Latest

| Item | Value |
| --- | --- |
| Run | [V3 Final Five-Way Eval with Gold-Issue Exclusion](runs/2026-06-16-v3-final-gold-issue-adjusted.md) |
| Date | 2026-06-16 |
| Model | `deepseek-v4-pro` |
| Judge prompt | `data-correctness-v5-2026-06-16` |
| Cases | 122 badcase x 2 repeats; query variant 100 x 3 random splits |
| Average ACC | badcase122 adjusted ACC 97.41%; query100 adjusted ACC 94.28%; all scored cases 95.70% |
| Main Insight | 回退到 v3 主线后，剥离明显 gold/task issue，badcase 与 query variant 的综合表现稳定接近 95%。后续优化应继续关注 query rewrite 下的时间表达、指标别名和表族选择，而不是继续污染通用工具。 |

## Update Rule

- 新的正式 benchmark / @N 稳定性测试：先在 `runs/` 下创建带日期和语义的归档文件。
- 再更新本文件，让它指向新的归档。
- 不把长篇逐题报告直接塞进本文件；机器明细保留在 `eval_test/results/<dataset>/parallel/<run_group>/runs/`。
