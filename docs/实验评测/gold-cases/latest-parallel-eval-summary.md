# Gold Cases Latest Eval Pointer

> 本文件只维护“当前最新主线评测”的指针，下一轮正式 full40 后可以覆盖更新。
> 关键里程碑必须另存到 `runs/`，避免被 latest 滚动覆盖。

## Current Latest

| Item | Value |
| --- | --- |
| Run | [DeepSeek V4 Pro after cohort fix @4](runs/2026-06-13-deepseek-v4pro-after-cohort-fix-at4.md) |
| Date | 2026-06-13 |
| Model | `deepseek-v4-pro` |
| Cases | 40 gold cases x 4 repeats |
| Average ACC | 82.50% |
| Main Insight | 四川财资 domain pack + `200亿省` 7 省 cohort + `extract_matrix` 自动展开领域 cohort，让 DeepSeek V4 Pro 达到 GPT-5.5 单次参考水平。 |

## Update Rule

- 新的正式 full40 / @N 稳定性测试：先在 `runs/` 下创建带日期和语义的归档文件。
- 再更新本文件，让它指向新的归档。
- 不把长篇逐题报告直接塞进本文件；机器明细保留在 `eval_test/results/gold_cases/parallel/runs/`。
