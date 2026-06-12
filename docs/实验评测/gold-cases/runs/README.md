# Gold Case Benchmark Runs

> 每次 40-case gold benchmark 都保留一份独立报告。`latest-parallel-eval-summary.md` 只是滚动最新结果，不作为唯一历史记录。

## Run Index

| Run | Prompt / Workflow 特点 | ACC | Avg score | Numeric F1 | Entity F1 | Avg elapsed | Tokens | 结论 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| [v1-baseline](2026-06-10-v1-baseline-acc40.md) | retrieve + inspect + 按需 skill/code；不显式强推新增读算工具 | 40.00% | 0.4800 | 0.4131 | 0.6004 | 208.07s | 14,187,768 | ranking 强，chart/trend/filter 弱；作为第一版有效 baseline；当时未归档完整 JSON，markdown 中为 preview |
| [v2-forced-tools](2026-06-10-v2-forced-tools-acc37_5.md) | prompt 显式要求优先使用 locate/topk/filter/extract_series | 37.50% | 0.4650 | 0.4566 | 0.6360 | 199.11s | 14,804,564 | 工具调用率上升但 ACC 下降，说明强制工具流程限制基模发挥 |
| [v3-loose-tools](2026-06-10-v3-loose-tools-acc40.md) | 工具仍可用，但 prompt 不显式点名、不强制调用，由模型自主选择 skill/tool/code | 40.00% | 0.5050 | 0.4154 | 0.6538 | 221.85s | 17,096,327 | ACC 回到 baseline，分数和实体 F1 提升；但 token/耗时升高，需要 step/time budget 控制长尾 |
| [v4-table-catalog](2026-06-10-v4-table-catalog.md) | 预先生成 161 张表的 catalog/profile/description；retrieve 融合 catalog 描述增强召回 | 47.50% | 0.5625 | 0.4303 | 0.6667 | 229.85s | 18,784,002 | catalog 相对 v3 有收益，但仍需结构化约束优先的 retrieval router 和 per-case budget |
| [v5-structured-retrieval](2026-06-10-v5-structured-retrieval.md) | 在 v4 catalog 上增加 query intent、constraint score、fit/risks 和 table group discovery；39 条主 run + case21 单独重跑补齐 | 52.50% | 0.6250 | 0.4164 | 0.6712 | 265.26s | 16,834,667 | ACC/Avg score 继续提升，说明结构化召回有效；但 case21/case31/case40 仍卡在表内结构理解、汇总行过滤和预算控制 |
| [v6-rank-tool-full40](2026-06-11-v6-rank-tool-full40.md) | 新增 `tableclaw_rank`，支持百分比归一化、实体排名和 cohort 排名；同一轮保留 case001 对比实验 | 45.00% | 0.5800 | 0.4232 | 0.6649 | 201.53s | 16,970,759 | case001 修复且 ranking_qa 仍强，但 full40 低于 v5；rank 工具改善特定排名问题，同时 chart/filter/table 内结构理解仍是主要短板 |
| [v7-rank-official-header-path](2026-06-11-v7-rank-official-header-path-full40.md) | rank tool 优先官方排名列、增强 header path 与百分比归一化 | 57.50% | 0.6375 | 0.4723 | 0.6948 | 225.51s | 18,437,422 | 较 v6 明显回升，chart 和 trend 改善；filter 仍为 0% |
| [v8-topk-companion-multientity](2026-06-11-v8-topk-companion-multientity-full40.md) | topk companion columns 和多实体输出增强 | 45.00% | 0.5425 | 0.4441 | 0.6899 | 215.41s | 15,902,675 | ranking 达 90.91%，但 chart 回落，说明 topk/multientity 偏向排名题 |
| [v9h-answer-markdown](2026-06-11-v9h-full40-after-answer-markdown.md) | extract_matrix/time_series 返回可直接复制的 answer_markdown/chart table | 67.50% | 0.7375 | 0.6140 | 0.7007 | 158.68s | 14,786,544 | 当前最佳 full40；结构化底表直接输出显著提升 chart/table/trend |
| [current-full40-after-horizontal-series](2026-06-12-current-full40-after-horizontal-series.md) | 在 answer_markdown 基础上增强横向序列/台账类底表输出，模型自主规划使用 matrix/time_series/horizontal_series | 80.00% | 0.8125 | - | - | 110.45s | 12,906,668 | 当前已归档最高 ACC；ranking/table/trend 均 100%，chart_generation 72.73%，filter_qa 仍为主要短板 |
| [v10-general-fixes](2026-06-12-v10-full40-general-fixes.md) | 默认汇总行排除、half-up rounding、占比类默认低到高排名、图表/跨期 prompt 约束 | 60.00% | 0.6750 | 0.5834 | 0.7062 | 234.25s | 16,674,941 | chart 升至 63.64%，但 ranking/table/trend 回退；下一步要小步 A/B 和预算控制 |
| [case001-tableclaw-teleclaw-comparison](2026-06-11-case001-tableclaw-teleclaw-comparison.md) | case001 专项对比：记录当前 TableClaw 与当前 TeleClaw 的执行轨迹、耗时、token 消耗、百分比归一化处理和排名计算差异 | - | - | - | - | - | - | 单 case 对比报告，不计入 40-case ACC |

## Run Time Index

> 每轮详细时间来自 `eval_test/results/gold_cases/parallel/runs/*_summary.json` 的 `started_at`、`finished_at` 和 `avg_elapsed_ms` 字段。v1 baseline 当时未归档完整 summary，因此只在主表保留平均耗时。

| Run | Started | Finished | Avg elapsed |
| --- | --- | --- | ---: |
| `2026-06-10-v2-forced-tools-acc37_5` | `2026-06-10T14:45:36+0800` | `2026-06-10T15:09:14+0800` | 199.11s |
| `2026-06-10-v3-loose-tools-acc40` | `2026-06-10T15:33:39+0800` | `2026-06-10T16:02:26+0800` | 221.85s |
| `2026-06-10-v4-table-catalog` | `2026-06-10T22:52:54+0800` | `2026-06-10T23:24:11+0800` | 229.85s |
| `2026-06-10-v5-structured-retrieval-combined` | `2026-06-10T23:41:00+0800` | `2026-06-11T09:10:07+0800` | 265.26s |
| `2026-06-11-v6-rank-tool-full40` | `2026-06-11T09:56:48+0800` | `2026-06-11T10:37:38+0800` | 201.53s |
| `2026-06-11-v7-rank-official-header-path-full40` | `2026-06-11T17:08:29+0800` | `2026-06-11T17:35:45+0800` | 225.51s |
| `2026-06-11-v8-topk-companion-multientity-full40` | `2026-06-11T22:09:39+0800` | `2026-06-11T22:31:38+0800` | 215.41s |
| `2026-06-11-v9h-full40-after-answer-markdown` | `2026-06-11T23:49:36+0800` | `2026-06-12T00:07:12+0800` | 158.68s |
| `2026-06-12-v10-full40-general-fixes` | `2026-06-12T00:32:54+0800` | `2026-06-12T01:58:32+0800` | 234.25s |
| `2026-06-12-current-full40-after-horizontal-series` | `2026-06-12T11:01:56+0800` | `2026-06-12T11:13:40+0800` | 110.45s |
| `2026-06-12-rollback-highbaseline-full40` | `2026-06-12T13:26:10+0800` | `2026-06-12T13:39:06+0800` | 117.23s |

## 记录规范

- 每次跑完 `./eval_gold_parallel.sh --concurrency 8` 后，将 `latest-parallel-eval-summary.md` 另存到本目录。
- 机器可读完整结果会写入 `eval_test/results/gold_cases/parallel/runs/<run_id>_results.jsonl` 和 `<run_id>_summary.json`。该目录是本地运行产物，不进 git；正式对外记录以本目录下的 markdown 为准。
- 文件名建议：`YYYY-MM-DD-vN-<strategy>-accXX.md`。
- 每份报告顶部必须有 `Run Profile`，至少说明：
  - version / purpose
  - prompt strategy
  - tool exposure
  - skill behavior
  - main insight
- `latest-parallel-eval-summary.md` 可以被覆盖，但本目录下的 run 文件不要覆盖。
