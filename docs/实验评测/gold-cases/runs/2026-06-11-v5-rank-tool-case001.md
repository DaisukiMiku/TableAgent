# Gold Cases Parallel Eval Summary

> Started: 2026-06-11T09:51:06+0800  
> Finished: 2026-06-11T09:52:52+0800  
> Mode: `skill-on` | Judge: `deepseek-v4-pro` | Cases: `1`

## Metrics

| Metric | Value |
| --- | ---: |
| LLM judge ACC | 100.00% |
| Avg judge score | 1.0000 |
| Macro numeric F1 | 0.4167 |
| Macro entity F1 | 0.4762 |
| Retrieval tool call rate | 100.00% |
| Inspect tool call rate | 100.00% |
| Skill selection rate | 0.00% |
| Total answer tokens | 210649 |
| Total judge tokens | 890 |
| Avg elapsed ms | 102777.00 |

## By Task Type

| Task type | Count | ACC | Avg score | Numeric F1 | Entity F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| ranking_qa | 1 | 100.00% | 1.0000 | 0.4167 | 0.4762 |

## TableClaw Tool Calls

| Tool | Cases used |
| --- | ---: |
| `tableclaw_catalog_tables` | 0 |
| `tableclaw_retrieve_tables` | 1 |
| `tableclaw_inspect` | 1 |
| `tableclaw_locate_column` | 0 |
| `tableclaw_extract_series` | 1 |
| `tableclaw_topk` | 0 |
| `tableclaw_rank` | 1 |
| `tableclaw_filter` | 0 |

## Case Comparison

| # | Task | Type | Judge | Score | Numeric F1 | Entity F1 | Retrieval | Inspect | TableClaw tools | Skills | Tokens | Gold answer | Model preview | Reason |
| ---: | --- | --- | --- | ---: | ---: | ---: | --- | --- | --- | --- | ---: | --- | --- | --- |
| 1 | `gold_case_001_e922815ae2` | ranking_qa | correct | 1.00 | 0.42 | 0.48 | `True` | `True` | `tableclaw_retrieve_tables,tableclaw_inspect,tableclaw_extract_series,tableclaw_rank` | `-` | 210649 | 2024年3月，四川省应收账款绝对值为23.7亿元，占收比为7.3%，在全国200亿省中排名第1位。产数应收账款绝对值为15.5亿元，占收比达23.5%，在全国200亿省中排名第4位。 | 以下是基于上传表的查询结果： --- ## 四川省 2024年3月 应收账款数据 **使用的表**：`全国各省份数据-通报应收总额_202403.xlsx` ### 一、应收账款（整体） \| 指标 \| 数值 \| \|------\|------\| \| **应收账款绝对值** \| **23.74 亿元** \| \| **应收占收比** \| **7.33%** \| \| **应收占收比全国排名（从低到高）** \| **第 1 名**（共9省） \| \| **应收占收比200亿省排名（从低到高）** \| **第 1 名**（共6个 | 模型回答与标准答案在数值上一致（23.7亿≈23.74亿，7.3%≈7.33%，15.5亿≈15.51亿，23.5%≈23.51%），排名完全正确，且正确区分了全国排名和200亿省排名，未使用错误表格或月份。 |

## Case Details

### Case 1 / `gold_case_001_e922815ae2`

- Type: `ranking_qa`
- Judge: `correct` / score `1.00`
- Numeric F1: `0.4167`
- Entity F1: `0.4762`
- TableClaw tools: `tableclaw_retrieve_tables, tableclaw_inspect, tableclaw_extract_series, tableclaw_rank`
- Skills: `-`
- Tokens: `210649`

**Question**

```text
四川省2024年3月应收账款绝对值是多少，应收占收比是多少，应收占收比排名全国第几，200亿省排名第几？产数应收账款绝对值是多少，产数应收占收比是多少，排名全国第几，200亿省排名第几？
```

**Gold Answer**

```text
2024年3月，四川省应收账款绝对值为23.7亿元，占收比为7.3%，在全国200亿省中排名第1位。产数应收账款绝对值为15.5亿元，占收比达23.5%，在全国200亿省中排名第4位。
```

**Model Answer**

```text
以下是基于上传表的查询结果：

---

## 四川省 2024年3月 应收账款数据

**使用的表**：`全国各省份数据-通报应收总额_202403.xlsx`

### 一、应收账款（整体）

| 指标 | 数值 |
|------|------|
| **应收账款绝对值** | **23.74 亿元** |
| **应收占收比** | **7.33%** |
| **应收占收比全国排名（从低到高）** | **第 1 名**（共9省） |
| **应收占收比200亿省排名（从低到高）** | **第 1 名**（共6个200亿省） |

> 注：200亿省指2023年总收入≥200亿的省份，包括湖南、四川、浙江、上海、江苏、广东（共6省）。安徽(199.64亿)、湖北(195.28亿)、福建(184.54亿)不在此列。

### 二、产数应收账款

| 指标 | 数值 |
|------|------|
| **产数应收账款绝对值** | **15.51 亿元** |
| **产数应收占收比** | **23.51%** |
| **产数应收占收比全国排名（从低到高）** | **第 4 名**（共9省） |
| **产数应收占收比200亿省排名（从低到高）** | **第 4 名**（共6个200亿省） |

---

### 使用的表文件

| 文件名 | 说明 |
|--------|------|
| `全国各省份数据-通报应收总额_202403.xlsx` | 2024年3月全国各省份通报应收总额数据，含应收总额、应收占收比、产数应收、产数应收占收比及其排名 |

**完成状态**：✅ 成功完成。所有8个指标均已从该表中获取。该表包含四川行（row 10），数值来自列C（应收总额23.74亿）、列L（应收占收比7.33%）、列Q（产数应收15.51亿）、列Z（产数应收占收比23.51%），排名通过200亿省cohort（2023年总收入≥200亿）过滤计算得出。
```

**Judge Reason**

```text
模型回答与标准答案在数值上一致（23.7亿≈23.74亿，7.3%≈7.33%，15.5亿≈15.51亿，23.5%≈23.51%），排名完全正确，且正确区分了全国排名和200亿省排名，未使用错误表格或月份。
```

