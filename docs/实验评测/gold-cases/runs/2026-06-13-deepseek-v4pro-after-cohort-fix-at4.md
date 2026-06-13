# DeepSeek V4 Pro After Cohort Fix @4

> 最新主线摘要：DeepSeek V4 Pro after-cohort-fix full40 @4 稳定性复测。
> 详细机器结果保存在 `eval_test/results/gold_cases/parallel/runs/`，本文只记录可读结论和下一步。

## Run Profile

| Item | Value |
| --- | --- |
| Date | 2026-06-13 |
| Model | `deepseek-v4-pro` |
| Mode | `skill-on` |
| Judge | `deepseek-v4-pro` |
| Cases | 40 gold cases |
| Parallelism | 每轮并发 8；共 4 轮稳定性复测 |
| Main Change | 四川财资 domain pack 修正 `200亿省` 当前 gold/reporting cohort 为 7 省；`tableclaw_extract_matrix` 在 `cohort="200亿省"` 且未显式指定动态阈值时，从 domain knowledge 自动展开实体名单。 |

## Per-Run Results

| Run | ACC | Labels | Avg elapsed | Total tokens |
| --- | ---: | --- | ---: | ---: |
| `2026-06-13-deepseek-v4pro-full40-after-cohort-fix-a` | 77.50% | 31 correct / 4 partial / 5 incorrect | 156.90s | 16,232,595 |
| `2026-06-13-deepseek-v4pro-full40-after-cohort-fix-b` | 82.50% | 33 correct / 3 partial / 4 incorrect | 139.70s | 14,496,454 |
| `2026-06-13-deepseek-v4pro-full40-after-cohort-fix-c` | 87.50% | 35 correct / 2 partial / 3 incorrect | 246.23s | 16,330,653 |
| `2026-06-13-deepseek-v4pro-full40-after-cohort-fix-d` | 82.50% | 33 correct / 3 partial / 4 incorrect | 147.61s | 15,204,484 |

## Aggregate @4

| Metric | Value |
| --- | ---: |
| Average ACC | 82.50% |
| Min / Max ACC | 77.50% / 87.50% |
| ACC std dev | 3.54 pp |
| Total labels across 160 cases | 132 correct / 12 partial / 16 incorrect |
| Average elapsed | 172.61s / case |
| Average total tokens | 15,566,046 / run |

## By Task Type @4

| Task type | Correct / Total | ACC | Labels |
| --- | ---: | ---: | --- |
| `chart_generation` | 69 / 88 | 78.41% | 69 correct / 8 partial / 11 incorrect |
| `filter_qa` | 3 / 8 | 37.50% | 3 correct / 0 partial / 5 incorrect |
| `ranking_qa` | 41 / 44 | 93.18% | 41 correct / 3 partial / 0 incorrect |
| `table_qa` | 11 / 12 | 91.67% | 11 correct / 1 partial / 0 incorrect |
| `trend_table` | 8 / 8 | 100.00% | 8 correct / 0 partial / 0 incorrect |

## Main Insight

- 修正前 DeepSeek V4 Pro A/B full40 为 65.00% / 67.50%；修正后 @4 平均达到 82.50%，说明 `domain pack -> tool -> answer` 的分层路线有效。
- `ranking_qa`、`table_qa`、`trend_table` 已经比较稳定，说明结构化读算工具和 answer-ready 底表输出是主线能力。
- `chart_generation` 明显改善，但 2025-12 sparse 表仍会出现“源表缺实际值、只有排名列”的长尾问题。
- `filter_qa` 仍是最弱类型，下一轮应优先做多条件筛选、阈值、cohort、缺值处理的工具/skill 联动。

## Artifact Paths

机器可读明细：

- `eval_test/results/gold_cases/parallel/runs/2026-06-13-deepseek-v4pro-full40-after-cohort-fix-a_results.jsonl`
- `eval_test/results/gold_cases/parallel/runs/2026-06-13-deepseek-v4pro-full40-after-cohort-fix-b_results.jsonl`
- `eval_test/results/gold_cases/parallel/runs/2026-06-13-deepseek-v4pro-full40-after-cohort-fix-c_results.jsonl`
- `eval_test/results/gold_cases/parallel/runs/2026-06-13-deepseek-v4pro-full40-after-cohort-fix-d_results.jsonl`

每个 run 同目录还有对应 `_summary.json`，用于后续复算指标。

## Next

1. 清洗 `eval_test/300条badcase.xlsx`，拆分为 `generic-tool` / `domain-knowledge` / `prompt-or-eval`。
2. 优先攻 `filter_qa`：多条件筛选、cohort 内筛选、缺值/排名列共存场景。
3. 针对 2025-12 sparse 表建立显式诊断：区分“源表真实缺值”和“需要业务补全/其他表召回”。
4. 给 40 gold cases 补 evaluator-only 的 gold table mapping，用 Recall@k 拆分召回问题和表内读算问题。
