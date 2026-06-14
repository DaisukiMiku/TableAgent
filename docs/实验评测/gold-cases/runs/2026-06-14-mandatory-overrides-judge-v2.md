# 2026-06-14 Mandatory Overrides + Judge V2

> Date: 2026-06-14
> Model: `deepseek-v4-pro`
> Mode: `skill-on`
> Judge model: `deepseek-v4-pro`
> Judge prompt version: `data-correctness-v2-2026-06-14`
> Config: `nanobot/configs/tableclaw-bailian-dashscope.json`
> Workspace: `workspace/`

## 版本特点

本轮是四川财资 domain pack 接入后的进一步稳定性评测，核心变化有两点：

1. `tableclaw_domain_knowledge` 增加 `mandatory_overrides`。
   - 对 `must_use_when_applies=true` 或 `priority=high` 的领域规则单独返回。
   - 当上传表出现稀疏、空值或报表口径冲突时，要求模型先检查表，再用 override facts 做最终 reconciliation。
   - 目标是减少 `202512 产数业务总收入 Top3` 这类 sparse-table case 中“只看到四川有值，所以无法确定”的失败。
2. LLM judge prompt 升级为 `data-correctness-v2-2026-06-14`。
   - 图表题只评估底层数据、实体、指标、单位、排序和口径。
   - 不因没有真正画图、Markdown 排版、叙述风格或未使用特定工具扣分。
   - `correct` 才计入 ACC；`partial` 明确不算 passed。
   - 合理接受单位转换、百分比/小数表达和四舍五入差异。

## Gold40 A/B

Dataset: `eval_test/test_dataset/gold_cases.jsonl`
Command:

```bash
./eval_gold_parallel.sh --concurrency 10 --run-id <run_id>
```

| Run | Cases | Correct | Partial | Incorrect | ACC | Avg elapsed | Answer tokens | Judge tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2026-06-14-gold40-mandatory-overrides-a` | 40 | 33 | 0 | 7 | 82.50% | 139.50s | 15,836,713 | 62,819 |
| `2026-06-14-gold40-mandatory-overrides-b` | 40 | 31 | 3 | 6 | 77.50% | 145.70s | 18,173,019 | 66,081 |
| **Average** | 40 x 2 | 32.0 | 1.5 | 6.5 | **80.00%** | **142.60s** | **17,004,866** | **64,450** |

### Gold40 观察

- `ranking_qa` 仍然是最稳定类型：A 轮 100%，B 轮 90.91%。
- `trend_table` 在两轮均 100%。
- 主要波动来自 `chart_generation`，尤其 2025-12 sparse 表、多省图表和长时间序列图表。
- `filter_qa` 仍偏弱，典型错误是基础业务收入同比负增长省份漏检。
- 两轮共同暴露：2025-12 部分省份表值稀疏时，模型仍可能只输出四川一省，未稳定结合 domain fallback。

### Gold40 主要剩余问题

- `case 5`: 2025-12 200亿省基础业务收入同比负增长，模型仍会因为表稀疏而漏掉安徽、上海。
- `case 21/23/30/31`: 2025-12 多省图表题，模型经常只输出四川或标记其他省为空。
- `case 37/39`: 多月图表/序列题仍可能选错年份或错列。
- `case 20` B 轮 partial：200亿省集合偶发漏安徽/混入湖南。

## Badcase122 A/B

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
| `2026-06-14-badcase-full122-mandatory-overrides-a` | 122 | 107 | 8 | 7 | 87.70% | 106.45s | 37,042,131 | 189,689 |
| `2026-06-14-badcase-full122-mandatory-overrides-b` | 122 | 106 | 11 | 5 | 86.89% | 103.82s | 35,406,304 | 189,737 |
| **Average** | 122 x 2 | 106.5 | 9.5 | 6.0 | **87.30%** | **105.13s** | **36,224,218** | **189,713** |

### Badcase122 观察

- 相比上一轮 full122（约 81.97% / 83.61%），本轮提升到约 87%。
- `chart_generation` 在 A 轮达到 100%，B 轮 96.43%，说明 judge v2 + 底层数据口径更贴合当前阶段目标。
- `ranking_qa` 仍有 202512 sparse fallback、长账龄排名口径和 TOP 语义方向问题。
- `table_qa` 样本少但仍是弱项，主要因为问题会要求结论/排名，而模型只验证数值。
- 两轮共同 non-correct cases：`1, 7, 13, 28, 29, 71, 122`。

### Badcase122 主要剩余问题

- `case 1/29`: 202504 预收排名中巴中 `7 vs 15`，疑似 gold/reporting 口径冲突，当前先保留为人工复核项。
- `case 7`: 四川 202512 产数收入同比答对负增长，但没稳定补充“7 个 200亿省中唯一负增长”横向结论。
- `case 13`: “TOP 5 应收占收比”应按高到低，但模型按风险低到高排序。
- `case 28`: 202512 产数业务总收入 Top3 仍有概率未采用 mandatory fallback。
- `case 71`: 累计营业总收入同比 12 月 `-0.05% vs 0.00%`，属于舍入/口径尾差。
- `case 122`: 用户给出数值后问全国排名，模型只验证数值，漏答排名第 5。

## 结论

本轮证明：

- `mandatory_overrides` 是有效方向，能提升 badcase 稳定性，但还没有完全消除 202512 sparse 表失败。
- judge v2 更符合当前阶段目标：评估表格结果是否正确，而不是图表外观或叙述格式。
- 当前 TableClaw 在四川财资 badcase 上已达到约 87% ACC；40 条 gold case 在当前 judge v2 下约 80% ACC。

下一轮建议：

1. 对 `mandatory_overrides` 增加更强的最终答案 reconciliation 检查，尤其是 202512 产数 Top3 和 200亿省 sparse 表。
2. 明确 `TOP/最高/前N` 默认高到低，只有“最低/风险低/占比低更优”才低到高。
3. 给“用户已给数值，问排名/结论”的 case 增加目标字段检查，防止只验证输入事实。
4. 对疑似 gold 冲突 case 建立 `gold_suspect` 标注，不让它们误导通用工具。
5. 后续正式报告同时记录 gold40 和 badcase122，避免只看单一数据集。

## 机器结果

- `eval_test/results/gold_cases/parallel/runs/2026-06-14-gold40-mandatory-overrides-a_summary.json`
- `eval_test/results/gold_cases/parallel/runs/2026-06-14-gold40-mandatory-overrides-b_summary.json`
- `eval_test/results/gold_cases/parallel/runs/2026-06-14-badcase-full122-mandatory-overrides-a_summary.json`
- `eval_test/results/gold_cases/parallel/runs/2026-06-14-badcase-full122-mandatory-overrides-b_summary.json`
