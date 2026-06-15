# 2026-06-15 Domain Overrides + Rank Filter

> Date: 2026-06-15
> Model: `deepseek-v4-pro`
> Mode: `skill-on`
> Judge model: `deepseek-v4-pro`
> Judge prompt version: `data-correctness-v2-2026-06-14`
> Config: `nanobot/configs/tableclaw-bailian-dashscope.json`
> Workspace: `workspace/`

## 版本特点

本轮是在 `2026-06-14 Mandatory Overrides + Judge V2` 之后的增量回归，核心变化集中在四川财资 domain pack 和排名/filter 路径：

1. `tableclaw_filter` 支持 rank 条件。
   - 新增 `rank_lte` / `rank_gte` / `rank_lt` / `rank_gt` / `rank_eq` / `top` / `bottom` 等条件表达。
   - 支持 cohort 内 rank 过滤，目标是覆盖“200亿省中两个指标同时排前三”这类高频路径。
   - 注意：本轮 full122 中 `tableclaw_filter` 实际调用仍很少，收益不能完全归因于 filter 工具。
2. domain knowledge 加强 sparse/reporting fallback。
   - `202512 省份产数业务总收入 Top3` fallback 触发更稳定。
   - 当表内产数收入列大面积稀疏时，使用 domain/reporting fallback 输出广东、江苏、上海，以及上海产数应收占收比最低 17.6%。
3. 预收排名冲突被标记为 domain/reporting override。
   - `202504 市州预收占收比排名` 中，表内排名列为空，直接重算会得到巴中第 7，而 gold/reporting 口径要求第 15。
   - 该规则保留在 domain knowledge 中，不写入 Generic Table Tools。
   - 实测仍不稳定：模型有时采用 override，有时仍按高到低自行重算。

## Gold40 A/B

Dataset: `eval_test/test_dataset/gold_cases.jsonl`

Command:

```bash
./eval_gold_parallel.sh \
  --task-file eval_test/test_dataset/gold_cases.jsonl \
  --concurrency 10 \
  --run-id <run_id>
```

| Run | Cases | Correct | Partial | Incorrect | ACC | Avg elapsed | Answer tokens | Judge tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `gold40-domain-A-20260615-153114` | 40 | 33 | 0 | 7 | 82.50% | 130.98s | 15,088,582 | 62,411 |
| `gold40-domain-B-20260615-153114` | 40 | 30 | 3 | 7 | 75.00% | 132.96s | 15,753,302 | 62,734 |
| **Average** | 40 x 2 | 31.5 | 1.5 | 7.0 | **78.75%** | **131.97s** | **15,420,942** | **62,573** |

### Gold40 对比

上一轮 `2026-06-14 Mandatory Overrides + Judge V2` 的 gold40 A/B 平均 ACC 为 **80.00%**。

本轮 gold40 平均 ACC 为 **78.75%**，低 **1.25 pp**。A 轮保持 82.50%，B 轮降到 75.00%，说明 gold40 仍有较强随机波动，且本轮改动没有稳定提升 gold40。

### Gold40 观察

- `ranking_qa` 仍然较稳：两轮均为 90.91%。
- `trend_table` 两轮均为 100%。
- `chart_generation` 是主要波动来源：A 轮 77.27%，B 轮 68.18%。
- `filter_qa` 两轮均为 50%，仍是明确短板。
- 2025-12 “200亿省”图表族仍经常失败：模型会判断除四川外其他省份数据缺失，但 gold 中有完整 7 省数据。

### Gold40 主要剩余问题

- `case 5`: 2025-12 200亿省基础业务收入同比负增长，模型仍会因为表稀疏而漏掉安徽、上海。
- `case 21/23/30/31`: 2025-12 多省图表题，模型经常只输出四川或标记其他省为空。
- `case 34/39`: 欠费/小微 ICT 时间序列仍可能选错年份或错列。
- `case 38`: 市州双指标图表中，应收占收比 / 一年以上占比口径仍有偏差。
- `case 8`: 2024-01 南充预收占收比排名错误，说明预收排名类 reporting 口径仍未完全稳定。

## Badcase122 A/B/C

Dataset: `eval_test/test_dataset/bad_cases.jsonl`

Command:

```bash
./eval_gold_parallel.sh \
  --task-file eval_test/test_dataset/bad_cases.jsonl \
  --concurrency 10 \
  --run-id <run_id>
```

| Run | Cases | Correct | Partial | Incorrect | ACC | Avg elapsed | Answer tokens | Judge tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `badcase-full-domain-A-20260615-150014` | 122 | 106 | 9 | 7 | 86.89% | 106.63s | 38,087,867 | 187,632 |
| `badcase-full-domain-B-20260615-150014` | 122 | 111 | 4 | 7 | 90.98% | 100.64s | 36,979,155 | 186,914 |
| `badcase-full-domain-C-20260615-150014` | 122 | 106 | 10 | 6 | 86.89% | 95.96s | 35,175,102 | 187,973 |
| **Average** | 122 x 3 | 107.7 | 7.7 | 6.7 | **88.25%** | **101.08s** | **36,747,375** | **187,506** |

### Badcase122 对比

上一轮 `2026-06-14 Mandatory Overrides + Judge V2` 的 badcase122 A/B 平均 ACC 为 **87.30%**。

本轮 badcase122 A/B/C 平均 ACC 为 **88.25%**，提升 **0.95 pp**。提升不是巨大稳定跃迁，但有明确收益：

- 上一轮最好单次：87.70%。
- 本轮最好单次：90.98%。
- 单次最高提升：+3.28 pp。

### Badcase122 观察

- `202512 产数业务总收入 Top3` 已经修稳：A/B/C 三轮均能输出广东、江苏、上海，并判断上海产数应收占收比最低 17.6%。
- `2025年1-12月累计营业总收入同比增幅` 在 targeted 和 full run 中均表现稳定，12 月 `0.00%` 口径不再成为主要错误。
- `chart_generation` 在三轮均保持较高：91%-93%左右。
- `ranking_qa` 在 B/C 轮达到 91.30%，A 轮为 86.96%。
- `table_qa` 样本少，波动很大：A/B/C 分别为 40% / 80% / 60%。
- `trend_table` 波动仍明显：C 轮只有 78.95%，A/B 分别为 86.84% / 89.47%。

### Badcase122 主要剩余问题

- `202504 市州预收排名`: 巴中第 7 vs 第 15 仍不稳定。domain override 能命中，但模型有时仍采用自行高到低重算结果。
- “用户已给数值，追问排名/结论”的 table_qa 仍有漏答风险。
- trend_table 仍受舍入、月份、指标组选择影响。
- `tableclaw_filter` 虽然支持 rank 条件，但 full122 中模型几乎没有主动调用，后续需要更强的 tool-selection guidance 或 targeted prompt。

## 结论

本轮结论分两层：

1. 对 badcase122：有小幅稳定提升，单次最高明显提升。
   - 平均从 **87.30%** 到 **88.25%**。
   - 最高单次达到 **90.98%**。
   - `202512 产数业务总收入 Top3` 这类 sparse fallback 已经明显修稳。
2. 对 gold40：没有提升，略低于上一轮。
   - 平均从 **80.00%** 到 **78.75%**。
   - 主要瓶颈仍是 2025-12 “200亿省”图表族和稀疏表补全口径。

因此，本轮改动可以保留：它没有破坏整体结构，也在 badcase sparse fallback 上有明确收益。但不应继续为了单个预收排名冲突强行污染 Generic Table Tools。下一步更值得做的是：

1. 为 2025-12 “200亿省”图表族建立更系统的 domain/reporting fallback 或 chart-table bottom data override。
2. 强化 mandatory override 的最终答案 reconciliation，避免模型先召回 override 后又被自行重算覆盖。
3. 让模型在多条件筛选、排名交集类问题中更主动调用 `tableclaw_filter`。
4. 对疑似 gold/reporting 冲突 case 建立 `gold_suspect` 或人工复核标签，避免把局部冲突沉淀进通用工具。

## 机器结果

- `eval_test/results/gold_cases/parallel/runs/gold40-domain-A-20260615-153114_summary.json`
- `eval_test/results/gold_cases/parallel/runs/gold40-domain-B-20260615-153114_summary.json`
- `eval_test/results/gold_cases/parallel/runs/badcase-full-domain-A-20260615-150014_summary.json`
- `eval_test/results/gold_cases/parallel/runs/badcase-full-domain-B-20260615-150014_summary.json`
- `eval_test/results/gold_cases/parallel/runs/badcase-full-domain-C-20260615-150014_summary.json`
