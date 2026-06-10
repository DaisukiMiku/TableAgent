# Gold Case Benchmark Runs

> 每次 40-case gold benchmark 都保留一份独立报告。`latest-parallel-eval-summary.md` 只是滚动最新结果，不作为唯一历史记录。

## Run Index

| Run | Prompt / Workflow 特点 | ACC | Avg score | Numeric F1 | Entity F1 | Avg elapsed | Tokens | 结论 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| [v1-baseline](2026-06-10-v1-baseline-acc40.md) | retrieve + inspect + 按需 skill/code；不显式强推新增读算工具 | 40.00% | 0.4800 | 0.4131 | 0.6004 | 208.07s | 14,187,768 | ranking 强，chart/trend/filter 弱；作为第一版有效 baseline |
| [v2-forced-tools](2026-06-10-v2-forced-tools-acc37_5.md) | prompt 显式要求优先使用 locate/topk/filter/extract_series | 37.50% | 0.4650 | 0.4566 | 0.6360 | 199.11s | 14,804,564 | 工具调用率上升但 ACC 下降，说明强制工具流程限制基模发挥 |

## 记录规范

- 每次跑完 `./eval_gold_parallel.sh --concurrency 8` 后，将 `latest-parallel-eval-summary.md` 另存到本目录。
- 文件名建议：`YYYY-MM-DD-vN-<strategy>-accXX.md`。
- 每份报告顶部必须有 `Run Profile`，至少说明：
  - version / purpose
  - prompt strategy
  - tool exposure
  - skill behavior
  - main insight
- `latest-parallel-eval-summary.md` 可以被覆盖，但本目录下的 run 文件不要覆盖。
