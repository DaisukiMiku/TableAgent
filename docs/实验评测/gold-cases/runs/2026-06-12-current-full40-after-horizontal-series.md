# Gold Cases Parallel Eval Summary

## Run Profile

| Item | Value |
| --- | --- |
| Run id | `2026-06-12-current-full40-after-horizontal-series` |
| Purpose | 验证 `extract_matrix` / `time_series` / `horizontal_series` 等工具输出可直接复用的底层数据表后，full40 的整体效果 |
| Prompt strategy | 宽松工具策略；模型自主规划，优先使用召回、inspect、矩阵/序列/横向序列工具，必要时再用代码校验 |
| Tool exposure | `tableclaw_retrieve_tables`、`tableclaw_inspect`、`tableclaw_extract_matrix`、`tableclaw_time_series`、`tableclaw_horizontal_series`、`tableclaw_rank` 等均可见 |
| Main insight | 当前已记录 full40 最高准确率：80.00%。说明“稳定工具给出可直接回答/绘图的结构化底表”明显优于让模型反复自行重排 JSON 或临时读表 |

> Started: 2026-06-12T11:01:56+0800
> Finished: 2026-06-12T11:13:40+0800
> Mode: `skill-on` | Cases: `40`

## Metrics

| Metric | Value |
| --- | ---: |
| LLM judge ACC | 80.00% |
| Judge labels | 32 correct / 2 partial / 6 incorrect |
| Avg judge score | 0.8125 |
| Retrieval tool call rate | 100.00% |
| Inspect tool call rate | 70.00% |
| Skill selection rate | 0.00% |
| Total answer tokens | 12,906,668 |
| Total judge tokens | 50,573 |
| Avg elapsed ms | 110,450.80 |

## By Task Type

| Task type | Count | ACC | Avg score | Numeric F1 | Entity F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| chart_generation | 22 | 72.73% | 0.7500 | 0.5141 | 0.7447 |
| filter_qa | 2 | 0.00% | 0.0000 | 0.2295 | 0.5249 |
| ranking_qa | 11 | 100.00% | 1.0000 | 0.5413 | 0.7434 |
| table_qa | 3 | 100.00% | 1.0000 | 0.4606 | 0.6984 |
| trend_table | 2 | 100.00% | 1.0000 | 0.6487 | 0.3667 |

## TableClaw Tool Calls

| Tool | Cases used |
| --- | ---: |
| `tableclaw_catalog_tables` | 0 |
| `tableclaw_retrieve_tables` | 40 |
| `tableclaw_inspect` | 28 |
| `tableclaw_locate_column` | 7 |
| `tableclaw_extract_series` | 1 |
| `tableclaw_extract_matrix` | 31 |
| `tableclaw_time_series` | 5 |
| `tableclaw_horizontal_series` | 5 |
| `tableclaw_topk` | 2 |
| `tableclaw_rank` | 8 |
| `tableclaw_filter` | 4 |

## Non-Correct Cases

| Case | Type | Judge | Main issue |
| ---: | --- | --- | --- |
| 5 | filter_qa | incorrect | 2025-12 表中 200亿省/基础业务收入同比增幅口径没有稳定识别，遗漏安徽、上海负增长结果 |
| 16 | chart_generation | incorrect | 题面指标与 gold 表标签存在冲突；本轮按模型输出被判为错误指标/错误范围 |
| 18 | chart_generation | partial | 200亿省多省图表中遗漏安徽，排序/覆盖不完整 |
| 21 | chart_generation | incorrect | 只输出四川，缺少其他 200亿省的产数应收总额和占收比 |
| 23 | chart_generation | incorrect | 只输出四川，缺少广东、江苏、浙江、上海、安徽、湖南等省份 |
| 30 | chart_generation | incorrect | 只输出四川，缺少其他 200亿省双指标对比数据 |
| 31 | chart_generation | partial | 只输出四川，缺少多省双指标底表 |
| 40 | filter_qa | incorrect | 2025-12 200亿省多条件“同时排前三”判断错误，结论与金标相反 |

## Interpretation

这轮的关键增益来自工具返回值更接近最终答案：

- `extract_matrix` 能直接输出多实体、多指标底表，减少模型自己从 JSON 重排为表格时的错位。
- `time_series` 能直接跨月取数并计算增长、环比等序列。
- `horizontal_series` 能处理台账类横向月份结构，降低欠费/小微ICT图表题的临时探索成本。
- `rank` 在占比类排序、200亿省子集排序中提供稳定路径。

剩余错误主要不是单一 rank 或 topk 能解决的问题，而是集中在：

- 2025-12 sparse 省份表：部分省份目标列为空，但 gold 中存在多省结果，需要业务知识或表族补充。
- `200亿省` 口径：属于业务知识，当前仅按表内总收入阈值动态计算，缺少稳定 domain glossary。
- 多条件 filter：同时筛选 cohort、指标方向、排名前三等条件时，模型仍可能走错判断路径。
- chart 多省底表完整性：模型有时只输出四川，缺失同 cohort 其他省份。

结论：该 run 是目前工具层设计的最好证据。后续不宜把单个失败 case 硬写死，而应把成功轨迹中稳定可迁移的读表/重排/计算流程继续沉淀到工具、skill 和 domain memory。
