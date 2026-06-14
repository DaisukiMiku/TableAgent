# 2026-06-12 GPT-5.5 Current Full40

## Run Profile

- Run ID: `2026-06-12-gpt55-current-full40`
- Agent model: `gpt-5.5`
- Judge model: `gpt-4.1-mini`
- Mode: `skill-on`
- Concurrency: `4`
- Started: `2026-06-12T15:51:29+0800`
- Finished: `2026-06-12T16:04:09+0800`
- Purpose: 在当前 TableClaw 代码基础上接入更强基模，跑一次 full40，观察正确率、耗时、token 消耗和工具轨迹。

## Overall Result

| Metric | Value |
| --- | ---: |
| Cases | 40 |
| Correct / Partial / Incorrect | 33 / 5 / 2 |
| LLM judge ACC | 82.50% |
| Avg judge score | 0.8925 |
| Macro numeric F1 | 0.6277 |
| Macro entity F1 | 0.7151 |
| Avg elapsed | 56.44s |
| Total answer tokens | 7,019,124 |
| Total judge tokens | 47,451 |

这轮结果达到 82.50%，高于此前归档的 full40 高分 run。需要注意的是，本轮更换了 agent 基模，因此不能和 DeepSeek 主线 run 直接做同口径结论；它更适合作为强基模上限和轨迹蒸馏样本。

## By Task Type

| Task type | Count | ACC | Avg score |
| --- | ---: | ---: | ---: |
| `ranking_qa` | 11 | 100.00% | 1.0000 |
| `trend_table` | 2 | 100.00% | 1.0000 |
| `chart_generation` | 22 | 81.82% | 0.8909 |
| `filter_qa` | 2 | 50.00% | 0.5000 |
| `table_qa` | 3 | 33.33% | 0.7000 |

主要提升体现在 ranking、trend 和 chart 底层数据类任务；filter/table 仍然是短板，尤其是 2025-12 的 200 亿省基础业务字段和欠费台账口径。

## Tool Usage

| Tool | Cases used |
| --- | ---: |
| `tableclaw_retrieve_tables` | 40 |
| `tableclaw_inspect` | 28 |
| `tableclaw_extract_matrix` | 27 |
| `tableclaw_rank` | 8 |
| `tableclaw_topk` | 4 |
| `tableclaw_time_series` | 4 |
| `tableclaw_extract_series` | 4 |
| `tableclaw_filter` | 2 |
| `tableclaw_locate_column` | 4 |

从原始日志看，除 TableClaw 工具外，模型还大量使用了 `exec`、`read_file` 和 `grep`。这说明本轮正确率不是单纯来自固定工具，而是“TableClaw 稳定路径 + GPT-5.5 自主代码探索”共同完成。

## Case Outcomes

| # | Type | Judge | Score | Tokens | Elapsed | Main TableClaw tools |
| ---: | --- | --- | ---: | ---: | ---: | --- |
| 1 | ranking_qa | correct | 1.0 | 91,767 | 47.8s | retrieve, inspect, matrix, rank |
| 2 | ranking_qa | correct | 1.0 | 92,410 | 43.8s | retrieve, matrix, rank |
| 3 | ranking_qa | correct | 1.0 | 103,184 | 32.2s | retrieve, topk, matrix |
| 4 | table_qa | partial | 0.5 | 143,778 | 39.8s | retrieve, time_series, inspect |
| 5 | filter_qa | incorrect | 0.0 | 88,739 | 35.4s | retrieve, inspect, filter |
| 6 | table_qa | partial | 0.6 | 1,089,361 | 304.9s | retrieve, inspect |
| 7 | ranking_qa | correct | 1.0 | 595,815 | 112.6s | retrieve, inspect, matrix, rank |
| 8 | ranking_qa | correct | 1.0 | 203,564 | 51.9s | retrieve, inspect, matrix, locate, rank |
| 9 | ranking_qa | correct | 1.0 | 157,397 | 45.0s | retrieve, inspect, topk, locate |
| 10 | table_qa | correct | 1.0 | 77,235 | 25.3s | retrieve, rank, matrix |
| 11 | ranking_qa | correct | 1.0 | 187,169 | 83.8s | retrieve, inspect, matrix, rank |
| 12 | ranking_qa | correct | 1.0 | 277,887 | 67.4s | retrieve, topk, inspect |
| 13 | ranking_qa | correct | 1.0 | 232,113 | 59.3s | retrieve, inspect, matrix, rank, locate |
| 14 | trend_table | correct | 1.0 | 95,334 | 36.0s | retrieve, time_series |
| 15 | trend_table | correct | 1.0 | 96,411 | 49.1s | retrieve, time_series |
| 16 | chart_generation | correct | 1.0 | 203,545 | 63.8s | retrieve, matrix |
| 17 | chart_generation | correct | 1.0 | 90,434 | 24.6s | retrieve, inspect, matrix |
| 18 | chart_generation | correct | 1.0 | 133,513 | 37.8s | retrieve, inspect, matrix |
| 19 | chart_generation | correct | 1.0 | 108,972 | 38.2s | retrieve, inspect, matrix |
| 20 | chart_generation | correct | 1.0 | 111,008 | 43.0s | retrieve, inspect, matrix |
| 21 | chart_generation | correct | 1.0 | 53,521 | 30.8s | retrieve, matrix |
| 22 | chart_generation | correct | 1.0 | 208,946 | 43.5s | retrieve, matrix |
| 23 | chart_generation | incorrect | 0.0 | 53,166 | 24.8s | retrieve, matrix |
| 24 | ranking_qa | correct | 1.0 | 71,958 | 27.2s | retrieve, inspect, rank, matrix |
| 25 | chart_generation | correct | 1.0 | 110,360 | 43.9s | retrieve, inspect, matrix |
| 26 | chart_generation | correct | 1.0 | 90,349 | 28.3s | retrieve, inspect, matrix |
| 27 | chart_generation | correct | 1.0 | 111,702 | 26.6s | retrieve, inspect, matrix |
| 28 | chart_generation | correct | 1.0 | 162,405 | 52.6s | retrieve, inspect, locate, matrix |
| 29 | chart_generation | correct | 1.0 | 90,205 | 28.7s | retrieve, inspect, matrix |
| 30 | chart_generation | partial | 0.5 | 53,538 | 25.0s | retrieve, matrix |
| 31 | chart_generation | partial | 0.5 | 73,835 | 29.0s | retrieve, matrix |
| 32 | chart_generation | correct | 1.0 | 50,283 | 24.6s | retrieve, time_series |
| 33 | chart_generation | correct | 1.0 | 141,847 | 48.6s | retrieve, inspect, series |
| 34 | chart_generation | correct | 1.0 | 154,516 | 51.7s | retrieve, inspect, series |
| 35 | chart_generation | correct | 1.0 | 126,607 | 43.4s | retrieve, inspect, matrix |
| 36 | ranking_qa | correct | 1.0 | 191,997 | 62.9s | retrieve, inspect, topk |
| 37 | chart_generation | partial | 0.6 | 248,796 | 91.5s | retrieve, series, inspect |
| 38 | chart_generation | correct | 1.0 | 173,686 | 85.1s | retrieve, inspect, matrix |
| 39 | chart_generation | correct | 1.0 | 285,616 | 76.4s | retrieve, inspect, series |
| 40 | filter_qa | correct | 1.0 | 386,155 | 171.1s | retrieve, inspect, matrix, filter |

## Bad And Partial Cases

- Case 04: 回答了增长额，但没有输出增长百分比；单位也没有明确标注为亿元。
- Case 05: 200 亿省基础业务收入同比增幅筛选错误，只识别到四川，漏掉安徽、上海。
- Case 06: 欠费台账类问题只答对总欠费、已列收、未列收和占收比；一年以上欠费、小微 ICT 欠费口径错误或缺失。该 case 耗时 304.9s、消耗 1,089,361 tokens，是本轮最典型的高成本探索样本。
- Case 23: 2025年12月 200 亿省基础应收总额及占收比只输出四川，漏掉其他省份。
- Case 30: 2025年12月 200 亿省基础应收总额同比增幅、基础收入同比增幅只输出四川，漏掉其他省份。
- Case 31: 2025年12月 200 亿省基础应收占收比及同比增量只输出四川，漏掉其他省份。
- Case 37: 成都 2023-01 至 2025-12 总欠费占收比趋势，时间范围正确，但部分月份数值存在偏差。

## Trajectory Analysis

1. `retrieve_tables + extract_matrix` 是当前最稳定的高频路径，尤其适合多省份、多指标底表和 chart_generation 任务。
2. `rank/topk` 在 ranking_qa 中表现稳定，本轮 ranking_qa 11/11 correct。
3. GPT-5.5 遇到复杂结构时会主动写 Python 读 Excel，并配合 `read_file/grep` 校验工具结果。这提升了正确率，但带来较高 token 和耗时。
4. 2025年12月基础业务相关 case 仍暴露出 `extract_matrix` 的 cohort 展开不稳：部分题只返回四川，未覆盖全部 200 亿省。
5. 欠费台账类问题不是单纯表格抽取问题，还包含 sheet 选择、单位换算、行列口径、长账龄/小微 ICT 等业务知识，需要进入 skill/memory 或领域知识层。

## Next Actions

1. 将 GPT-5.5 正确轨迹作为样本，提炼可复用的表格探索策略，而不是把单个 case 写死到工具里。
2. 优先修复 `extract_matrix` 在 cohort 多实体展开上的稳定性，重点覆盖 2025-12 基础业务多省份缺失问题。
3. 为欠费台账建立独立 skill 或领域记忆，承接 sheet/字段/单位/口径规则，避免模型每次重新探索。
4. 后续与老师已有版本融合时，重点吸收业务知识、召回逻辑和坏例经验，再用 full40 与新增 bad cases 持续闭环评测。

## Artifacts

- Summary JSON: `eval_test/results/gold_cases/parallel/runs/2026-06-12-gpt55-current-full40_summary.json`
- Results JSONL: `eval_test/results/gold_cases/parallel/runs/2026-06-12-gpt55-current-full40_results.jsonl`
- Rolling report: `eval_test/results/gold_cases/parallel/latest_report.md`
