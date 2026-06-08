# TableClaw Retrieval Smoke

> Generated at: 2026-06-08T14:02:58+0800

## Scope

本轮用于跑通 `用户上传表格 -> table index -> question retrieval -> Nanobot skill workflow -> trace/usage log` 的编排链路。
当前不作为最终准确率结论；候选表来自检索，不把 gold table path 显式写进 prompt。

## Key Observations

- 161 张工业表已模拟上传到 `workspace/uploads/`，并生成 `workspace/table_index/tables.jsonl` 文件级索引。
- 10/10 case 均触发了 table skill read；触发过 `xlsx`、`table-read`、`table-chart`、`table-clean`、`table-validate`。
- 总 token 约 1,514,435，平均每题约 151,444；平均耗时约 142.7 秒。
- 编排链路已经跑通：先召回候选表，再由 Nanobot 读取 skill、选择候选表、执行 openpyxl 脚本、输出答案。
- 当前瓶颈很清楚：模型仍在反复摸表头和列位置。下一步应优先做 schema cache、sheet/column retrieval、`tableclaw_locate_column`、`tableclaw_extract_series` 和 `tableclaw_topk` 等工具。

## Workspace Uploads

- Upload dir: `/Users/hxy/Desktop/TableClaw/workspace/uploads`
- Indexed tables: `161`
- Top-k per task: `8`

## Results

| Task | Type | Retrieved top1 | Skills read | Skill sequence | Total tokens | Prompt | Completion | Tools | Elapsed ms | Error |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- | ---: | --- |
| raw_eval_0001_2d97148e77 | chart_generation | 市州数据-欠费数据_台账.xlsx | `table-read,table-chart` | `table-read -> table-chart` | 116523 | 111590 | 4933 | read_file,read_file,exec,exec,exec,exec | 111757 | - |
| raw_eval_0002_cb0e47f4a1 | chart_generation | 区县数据-欠费数据.xlsx | `table-read,table-chart,xlsx` | `table-read -> table-chart -> xlsx` | 298220 | 289853 | 8367 | read_file,read_file,read_file,exec,exec,exec,exec,exec,exec,exec,exec,exec,exec | 198028 | - |
| raw_eval_0003_2f746bf211 | chart_generation | 市州数据-欠费数据_台账.xlsx | `table-read,table-chart,xlsx,table-clean` | `table-read -> table-chart -> xlsx -> table-clean` | 136027 | 129391 | 6636 | read_file,read_file,read_file,read_file,exec,exec,exec,exec | 167465 | - |
| raw_eval_0004_07b108a337 | chart_generation | 市州数据-欠费数据_台账.xlsx | `table-read,table-chart,xlsx` | `table-read -> table-chart -> xlsx` | 175836 | 169838 | 5998 | read_file,read_file,read_file,exec,exec,exec,exec,exec,exec | 147259 | - |
| raw_eval_0037_c641a8e211 | table_qa | 全国各省份数据-通报应收总额_202508.xlsx | `xlsx,table-read` | `xlsx -> table-read` | 68114 | 63637 | 4477 | read_file,read_file,read_file,exec,exec | 106755 | - |
| raw_eval_0038_da4052e8c9 | table_qa | 市州数据-市州应收账款情况表_202508.xlsx | `table-read,xlsx,table-validate` | `table-read -> xlsx -> table-validate` | 58931 | 55768 | 3163 | read_file,read_file,read_file,exec,exec | 84110 | - |
| raw_eval_0044_d494105389 | table_qa | 市州数据-市州应收账款情况表_202509.xlsx | `xlsx,table-read` | `xlsx -> table-read` | 165513 | 158317 | 7196 | read_file,read_file,exec,exec,exec,exec,exec,exec,exec,exec,exec | 180243 | - |
| raw_eval_0016_73abb469f5 | ranking_qa | 市州数据-欠费数据_台账.xlsx | `xlsx,table-read` | `xlsx -> table-read` | 87213 | 84709 | 2504 | read_file,read_file,exec,exec,exec | 62317 | - |
| raw_eval_0017_136f8511e9 | ranking_qa | 市州数据-欠费数据_台账.xlsx | `table-read,xlsx` | `table-read -> xlsx` | 178448 | 171091 | 7357 | read_file,read_file,exec,exec,exec,exec,exec,exec | 185526 | - |
| raw_eval_0018_0fcb224585 | ranking_qa | 市州数据-欠费数据_台账.xlsx | `xlsx,table-read` | `xlsx -> table-read` | 229610 | 222204 | 7406 | read_file,read_file,exec,exec,exec,exec,exec,exec,exec,exec | 183131 | - |

## Retrieval Details

### raw_eval_0001_2d97148e77

Question: 2025年1-12月，一年以上总欠费画个图

| Rank | Table | Score | Scope | Subject | Month | Reasons |
| ---: | --- | ---: | --- | --- | --- | --- |
| 1 | 市州数据-欠费数据_台账.xlsx | 51.0 | city | 欠费 | - | keyword:总欠费, preview:12, filename:欠费, year-series-ledger, domain:arrears, domain:aging, chart-compatible |
| 2 | 区县数据-欠费数据.xlsx | 49.0 | county | 欠费 | - | preview:2025, preview:12, filename:欠费, year-series-ledger, domain:arrears, domain:aging, chart-compatible |
| 3 | 全国各省份数据-长账龄_202512.xlsx | 41.0 | province | 长账龄 | 202512 | filename:2025, keyword:一年以上, filename:12, month:202512, domain:aging, chart-compatible |
| 4 | 全国各省份数据-长账龄_202501.xlsx | 35.0 | province | 长账龄 | 202501 | filename:2025, keyword:一年以上, preview:12, month:202501, domain:aging, chart-compatible |
| 5 | 全国各省份数据-长账龄_202502.xlsx | 35.0 | province | 长账龄 | 202502 | filename:2025, keyword:一年以上, preview:12, month:202502, domain:aging, chart-compatible |
| 6 | 全国各省份数据-长账龄_202503.xlsx | 35.0 | province | 长账龄 | 202503 | filename:2025, keyword:一年以上, preview:12, month:202503, domain:aging, chart-compatible |
| 7 | 全国各省份数据-长账龄_202504.xlsx | 35.0 | province | 长账龄 | 202504 | filename:2025, keyword:一年以上, preview:12, month:202504, domain:aging, chart-compatible |
| 8 | 全国各省份数据-长账龄_202505.xlsx | 35.0 | province | 长账龄 | 202505 | filename:2025, keyword:一年以上, preview:12, month:202505, domain:aging, chart-compatible |

Answer preview:

```text
数据提取完成。以下是分析结果。

---

## 数据来源与提取逻辑

每个 `全国各省份数据-长账龄_YYYYMM.xlsx` 文件结构一致：列 D 为 "20XX年XX月末**一年以上应收账款余额**"，最后一行（第35行）为全国 **合计**。提取该合计值作为当月的"一年以上总欠费"，单位：亿元。

## 可用于绘图的底层数据表

```
月份        一年以上应收账款余额（亿元）
2025-01     134.19
2025-02     140.55
2025-03     153.64
2025-04     166.02
2025-05     170.15
2025-06     180.04
2025-07     194.66
2025-08     200.98
2025-09     201.38
2025-10     208.27
2025-11     206.62
2025-12     175.03
```

## 图表建议

- **推荐图表类型**：折线图（时间趋势）
- **X 轴**：月份（2025-01 ~ 2025-12）
- **Y 轴**：一年以上应收账款余额（亿元）
- **趋势特征**：1-10 月逐月上升（134→208 亿），11 月微降，12 月大幅回落至 175 亿（年末清欠效果明显）

## 候选表覆盖说明

系统检索召回了 8 个候选表，其中 `全国各省份数据-长账龄_*.xlsx` 系列只召回了 6 个月（202501-202505、202512），但工作区实际存在完整的 12 个月文件（202501-202512）。本任务使用了全部 12 个文件补齐年度数据。

---

**使用的候选表文件名：**
1. `全国各省份数据-长账龄_202501.xlsx`（候选 #4）
2. `全国各省份数据-长账龄_202502.xlsx`（候选 #5）
3. `全国各省份数据-长账龄_202503.xlsx`（候选 #6）
4. `全国各省份数据-长账龄_202504.xlsx`（候选 #7）
5. `全国各省份数据-长账龄_202505.xlsx`（候选 #8）
6. `全国各省份数据-长账龄_202512.xlsx`（候选 #3）
7. `全国各省份数据-长账龄_202506.xlsx` ~ `202511.xlsx`（候选表缺失，工作区补充）

**是否成功完成**：是 ✅
```

### raw_eval_0002_cb0e47f4a1

Question: 2025年1-12月，全省小微ICT欠费画个图

| Rank | Table | Score | Scope | Subject | Month | Reasons |
| ---: | --- | ---: | --- | --- | --- | --- |
| 1 | 区县数据-欠费数据.xlsx | 39.0 | county | 欠费 | - | preview:2025, preview:12, filename:欠费, year-series-ledger, domain:arrears, chart-compatible |
| 2 | 全国各省份数据-营业收现率_202512.xlsx | 37.0 | province | 营业收现率 | 202512 | filename:2025, filename:12, month:202512, scope:province, filename:province, chart-compatible |
| 3 | 全国各省份数据-营业现金比率_202512.xlsx | 37.0 | province | 营业现金比率 | 202512 | filename:2025, filename:12, month:202512, scope:province, filename:province, chart-compatible |
| 4 | 全国各省份数据-通报应收总额_202512.xlsx | 37.0 | province | 通报应收总额 | 202512 | filename:2025, filename:12, month:202512, scope:province, filename:province, chart-compatible |
| 5 | 全国各省份数据-长账龄_202512.xlsx | 37.0 | province | 长账龄 | 202512 | filename:2025, filename:12, month:202512, scope:province, filename:province, chart-compatible |
| 6 | 市州数据-欠费数据_台账.xlsx | 37.0 | city | 欠费 | - | preview:12, filename:欠费, year-series-ledger, domain:arrears, chart-compatible |
| 7 | 全国各省份数据-营业收现率_202502.xlsx | 31.0 | province | 营业收现率 | 202502 | filename:2025, preview:12, month:202502, scope:province, filename:province, chart-compatible |
| 8 | 全国各省份数据-营业收现率_202504.xlsx | 31.0 | province | 营业收现率 | 202504 | filename:2025, preview:12, month:202504, scope:province, filename:province, chart-compatible |

Answer preview:

```text
---

## 2025年全省小微ICT欠费 — 绘图底层数据

**数据来源**：候选表 #6 `市州数据-欠费数据_台账.xlsx`，Sheet「小微ICT欠费」，Row 56（四川全省合计行）。

**指标**：欠费金额（万元）

| 月份 | 欠费金额（万元） |
|------|----------------:|
| 2025-01 | 10,434.99 |
| 2025-02 | 10,677.37 |
| 2025-03 | 12,901.01 |
| 2025-04 | 11,931.86 |
| 2025-05 | 12,010.50 |
| 2025-06 | 14,759.07 |
| 2025-07 | 14,065.60 |
| 2025-08 | 14,418.02 |
| 2025-09 | 15,304.56 |
| 2025-10 | 14,812.40 |
| 2025-11 | 14,824.09 |
| 2025-12 | 13,659.93 |

**趋势特征**：全年呈倒V形走势，Q1-Q2持续攀升至6月峰值1.48亿，Q3高位震荡，9月达全年最高1.53亿，Q4回落后趋于平稳，年末1.37亿。下半年整体高于上半年。

**JSON 格式**（贴入图表工具即可用）：

```json
[
  {"月份":"2025-01","欠费金额_万元":10434.99},
  {"月份":"2025-02","欠费金额_万元":10677.37},
  {"月份":"2025-03","欠费金额_万元":12901.01},
  {"月份":"2025-04","欠费金额_万元":11931.86},
  {"月份":"2025-05","欠费金额_万元":12010.50},
  {"月份":"2025-06","欠费金额_万元":14759.07},
  {"月份":"2025-07","欠费金额_万元":14065.60},
  {"月份":"2025-08","欠费金额_万元":14418.02},
  {"月份":"2025-09","欠费金额_万元":15304.56},
  {"月份":"2025-10","欠费金额_万元":14812.40},
  {"月份":"2025-11","欠费金额_万元":14824.09},
  {"月份":"2025-12","欠费金额_万元":13659.93}
]
```

---

**使用的候选表文件名**：`市州数据-欠费数据_台账.xlsx`（#6，Sheet: 小微ICT欠费）

**是否成功完成**：✅ 是。数据完整覆盖2025年1-12月全省小微ICT欠费，可直接用于折线图/柱状图渲染。
```

### raw_eval_0003_2f746bf211

Question: 2025年1-12月，全省已列收欠费画个图

| Rank | Table | Score | Scope | Subject | Month | Reasons |
| ---: | --- | ---: | --- | --- | --- | --- |
| 1 | 市州数据-欠费数据_台账.xlsx | 41.0 | city | 欠费 | - | keyword:已列收, preview:12, filename:欠费, year-series-ledger, domain:arrears, chart-compatible |
| 2 | 区县数据-欠费数据.xlsx | 39.0 | county | 欠费 | - | preview:2025, preview:12, filename:欠费, year-series-ledger, domain:arrears, chart-compatible |
| 3 | 全国各省份数据-营业收现率_202512.xlsx | 37.0 | province | 营业收现率 | 202512 | filename:2025, filename:12, month:202512, scope:province, filename:province, chart-compatible |
| 4 | 全国各省份数据-营业现金比率_202512.xlsx | 37.0 | province | 营业现金比率 | 202512 | filename:2025, filename:12, month:202512, scope:province, filename:province, chart-compatible |
| 5 | 全国各省份数据-通报应收总额_202512.xlsx | 37.0 | province | 通报应收总额 | 202512 | filename:2025, filename:12, month:202512, scope:province, filename:province, chart-compatible |
| 6 | 全国各省份数据-长账龄_202512.xlsx | 37.0 | province | 长账龄 | 202512 | filename:2025, filename:12, month:202512, scope:province, filename:province, chart-compatible |
| 7 | 全国各省份数据-营业收现率_202502.xlsx | 31.0 | province | 营业收现率 | 202502 | filename:2025, preview:12, month:202502, scope:province, filename:province, chart-compatible |
| 8 | 全国各省份数据-营业收现率_202504.xlsx | 31.0 | province | 营业收现率 | 202504 | filename:2025, preview:12, month:202504, scope:province, filename:province, chart-compatible |

Answer preview:

```text
数据提取完成。以下是分析结果：

---

## 数据结构

- **文件**: 市州数据-欠费数据_台账.xlsx
- **Sheet**: 总欠费数据（总欠费分析——分已列收和未列收）
- **目标行**: Row 5，`四川 / 合计`（全省汇总）
- **指标列**: `列收欠费`（即"已列收欠费"）
- **单位**: 万元

## 图表底层数据表

| 月份 | 全省已列收欠费（万元） |
|------|----------------------|
| 2025-01 | 225,913.91 |
| 2025-02 | 248,623.15 |
| 2025-03 | 269,252.85 |
| 2025-04 | 274,696.41 |
| 2025-05 | 286,481.23 |
| 2025-06 | 329,899.80 |
| 2025-07 | 330,307.46 |
| 2025-08 | 342,043.74 |
| 2025-09 | 331,781.93 |
| 2025-10 | 332,239.07 |
| 2025-11 | 343,470.68 |
| 2025-12 | 326,570.07 |
| **全年合计** | **3,641,280.30** |

## 建议图表

- **类型**: 折线图（时间趋势）
- **X轴**: 月份（2025-01 ~ 2025-12）
- **Y轴**: 已列收欠费（万元）
- **系列**: 单系列「全省已列收欠费」

全年呈波动上升趋势，11月达峰值约34.3亿，12月回落至32.7亿；上半年从22.6亿逐步攀升至33.0亿，下半年在33亿附近震荡。

---

**使用的候选表**: 市州数据-欠费数据_台账.xlsx（#1，score 41.0）

**是否成功完成**: ✅ 是。候选表直接包含全省合计行的1-12月列收欠费数据，无需额外清洗或聚合。
```

### raw_eval_0004_07b108a337

Question: 2025年1-12月，全省总欠费画个图

| Rank | Table | Score | Scope | Subject | Month | Reasons |
| ---: | --- | ---: | --- | --- | --- | --- |
| 1 | 市州数据-欠费数据_台账.xlsx | 41.0 | city | 欠费 | - | keyword:总欠费, preview:12, filename:欠费, year-series-ledger, domain:arrears, chart-compatible |
| 2 | 区县数据-欠费数据.xlsx | 39.0 | county | 欠费 | - | preview:2025, preview:12, filename:欠费, year-series-ledger, domain:arrears, chart-compatible |
| 3 | 全国各省份数据-营业收现率_202512.xlsx | 37.0 | province | 营业收现率 | 202512 | filename:2025, filename:12, month:202512, scope:province, filename:province, chart-compatible |
| 4 | 全国各省份数据-营业现金比率_202512.xlsx | 37.0 | province | 营业现金比率 | 202512 | filename:2025, filename:12, month:202512, scope:province, filename:province, chart-compatible |
| 5 | 全国各省份数据-通报应收总额_202512.xlsx | 37.0 | province | 通报应收总额 | 202512 | filename:2025, filename:12, month:202512, scope:province, filename:province, chart-compatible |
| 6 | 全国各省份数据-长账龄_202512.xlsx | 37.0 | province | 长账龄 | 202512 | filename:2025, filename:12, month:202512, scope:province, filename:province, chart-compatible |
| 7 | 全国各省份数据-营业收现率_202502.xlsx | 31.0 | province | 营业收现率 | 202502 | filename:2025, preview:12, month:202502, scope:province, filename:province, chart-compatible |
| 8 | 全国各省份数据-营业收现率_202504.xlsx | 31.0 | province | 营业收现率 | 202504 | filename:2025, preview:12, month:202504, scope:province, filename:province, chart-compatible |

Answer preview:

```text
数据提取完成。以下是分析结果：

---

## 2025年1-12月 全省总欠费 — 绘图底层数据

**指标**：总系统欠费 → 欠费金额（万元）

| 月份 | 欠费金额（万元） |
|------|-----------------|
| 2025-01 | 372,563.75 |
| 2025-02 | 401,219.63 |
| 2025-03 | 419,099.84 |
| 2025-04 | 428,899.24 |
| 2025-05 | 445,678.28 |
| 2025-06 | 486,399.18 |
| 2025-07 | 489,752.37 |
| 2025-08 | 507,977.63 |
| 2025-09 | 501,301.07 |
| 2025-10 | 506,891.10 |
| 2025-11 | 524,349.90 |
| 2025-12 | 432,095.31 |

**CSV格式（chart-ready）**：
```
month,total_arrears_wan_yuan
2025-01,372563.75398
2025-02,401219.630684
2025-03,419099.840027
2025-04,428899.243627
2025-05,445678.281429
2025-06,486399.175932
2025-07,489752.365418
2025-08,507977.631584
2025-09,501301.071046
2025-10,506891.099117
2025-11,524349.895246
2025-12,432095.305198
```

**图表建议**：
- **类型**：折线图（时间趋势）
- **X轴**：月份（2025-01 → 2025-12）
- **Y轴**：总欠费金额（万元）
- **趋势**：1-11月逐月攀升（从37.3亿到52.4亿），12月大幅回落至43.2亿

---

**使用的候选表**：`市州数据-欠费数据_台账.xlsx`（候选表1，score=41.0）

**是否成功完成**：是 — 从"总欠费数据"sheet的全省合计行中完整提取了2025年1-12月共12个月的总欠费数据，可直接用于绘图。
```

### raw_eval_0037_c641a8e211

Question: 2025年8月，各200亿省（年收入>200亿），“应收总额同比增幅”与“收入同比增幅”趋势对比。

| Rank | Table | Score | Scope | Subject | Month | Reasons |
| ---: | --- | ---: | --- | --- | --- | --- |
| 1 | 全国各省份数据-通报应收总额_202508.xlsx | 56.0 | province | 通报应收总额 | 202508 | filename:2025, keyword:同比, keyword:增幅, filename:应收, month:202508, domain:receivable, scope:province, filename:province |
| 2 | 全国各省份数据-长账龄_202508.xlsx | 52.0 | province | 长账龄 | 202508 | filename:2025, keyword:同比, keyword:增幅, keyword:应收, month:202508, domain:receivable, scope:province, filename:province |
| 3 | 全国各省份数据-通报应收总额_202501.xlsx | 48.0 | province | 通报应收总额 | 202501 | filename:2025, keyword:同比, keyword:增幅, filename:应收, year-match, domain:receivable, scope:province, filename:province |
| 4 | 全国各省份数据-通报应收总额_202502.xlsx | 48.0 | province | 通报应收总额 | 202502 | filename:2025, keyword:同比, keyword:增幅, filename:应收, year-match, domain:receivable, scope:province, filename:province |
| 5 | 全国各省份数据-通报应收总额_202503.xlsx | 48.0 | province | 通报应收总额 | 202503 | filename:2025, keyword:同比, keyword:增幅, filename:应收, year-match, domain:receivable, scope:province, filename:province |
| 6 | 全国各省份数据-通报应收总额_202504.xlsx | 48.0 | province | 通报应收总额 | 202504 | filename:2025, keyword:同比, keyword:增幅, filename:应收, year-match, domain:receivable, scope:province, filename:province |
| 7 | 全国各省份数据-通报应收总额_202505.xlsx | 48.0 | province | 通报应收总额 | 202505 | filename:2025, keyword:同比, keyword:增幅, filename:应收, year-match, domain:receivable, scope:province, filename:province |
| 8 | 全国各省份数据-通报应收总额_202506.xlsx | 48.0 | province | 通报应收总额 | 202506 | filename:2025, keyword:同比, keyword:增幅, filename:应收, year-match, domain:receivable, scope:province, filename:province |

Answer preview:

```text
现在数据已经清楚了。以下是分析结果：

---

## 2025年8月 200亿省「应收总额同比增幅」vs「收入同比增幅」趋势对比

**筛选标准**：2024年总收入（横向汇总）> 200亿

从表中识别出 **7个200亿省**，按应收总额同比增幅从高到低排列：

```
省份    2024年总收入    应收总额同比增幅    收入同比增幅    差距(应收-收入)
─────────────────────────────────────────────────────────────
湖南      223.30亿        +39.2%            +4.5%        +34.7pp
安徽      218.57亿        +33.1%            -0.4%        +33.5pp
四川      318.23亿        +23.8%            +0.9%        +22.9pp
江苏      508.73亿        +23.4%            +1.3%        +22.1pp
浙江      339.31亿        +21.0%            +2.3%        +18.7pp
广东      619.80亿        +10.2%            +1.2%         +9.0pp
上海      329.35亿        +4.5%             +1.1%         +3.4pp
```

**趋势判断**：

1. **应收增幅远高于收入增幅**。7个省份的应收总额同比增幅（4.5%~39.2%）全面碾压收入同比增幅（-0.4%~4.5%），差距在 3.4pp 到 34.7pp 之间。
2. **收入增长几乎停滞**。除湖南（+4.5%）外，其余省份收入同比增幅均在 2.3% 以下，安徽甚至微降 0.4%。整体呈"应收狂奔、收入原地踏步"的态势。
3. **头部大省应收控制较好**。广东（+10.2%）和上海（+4.5%）作为收入体量最大的两个省，应收增幅相对克制；而湖南（+39.2%）、安徽（+33.1%）应收增幅显著偏高，风险值得关注。

---

**使用的候选表**：
- `全国各省份数据-通报应收总额_202508.xlsx`（table_id=tbl_5c49747718）

**是否成功完成**：是。单表即覆盖"年收入>200亿筛选""应收总额同比增幅""收入同比增幅"三个关键字段，无需其他候选表。
```

### raw_eval_0038_da4052e8c9

Question: 2025年8月，各省（年收入>200亿），“基础应收总额同比增幅”与“基础收入同比增幅”趋势对比。

| Rank | Table | Score | Scope | Subject | Month | Reasons |
| ---: | --- | ---: | --- | --- | --- | --- |
| 1 | 市州数据-市州应收账款情况表_202508.xlsx | 48.0 | city | 应收账款 | 202508 | filename:2025, preview:200, keyword:同比, keyword:增幅, filename:应收, month:202508, domain:receivable |
| 2 | 全国各省份数据-通报应收总额_202508.xlsx | 46.0 | province | 通报应收总额 | 202508 | filename:2025, keyword:同比, keyword:增幅, filename:应收, month:202508, domain:receivable |
| 3 | 全国各省份数据-长账龄_202508.xlsx | 42.0 | province | 长账龄 | 202508 | filename:2025, keyword:同比, keyword:增幅, keyword:应收, month:202508, domain:receivable |
| 4 | 市州数据-市州应收账款情况表_202501.xlsx | 40.0 | city | 应收账款 | 202501 | filename:2025, preview:200, keyword:同比, keyword:增幅, filename:应收, year-match, domain:receivable |
| 5 | 市州数据-市州应收账款情况表_202502.xlsx | 40.0 | city | 应收账款 | 202502 | filename:2025, preview:200, keyword:同比, keyword:增幅, filename:应收, year-match, domain:receivable |
| 6 | 市州数据-市州应收账款情况表_202503.xlsx | 40.0 | city | 应收账款 | 202503 | filename:2025, preview:200, keyword:同比, keyword:增幅, filename:应收, year-match, domain:receivable |
| 7 | 市州数据-市州应收账款情况表_202504.xlsx | 40.0 | city | 应收账款 | 202504 | filename:2025, preview:200, keyword:同比, keyword:增幅, filename:应收, year-match, domain:receivable |
| 8 | 市州数据-市州应收账款情况表_202505.xlsx | 40.0 | city | 应收账款 | 202505 | filename:2025, preview:200, keyword:同比, keyword:增幅, filename:应收, year-match, domain:receivable |

Answer preview:

```text
数据已经齐全。以下是分析结果。

---

## 2025年8月 年收入>200亿省份：基础应收总额同比增幅 vs 基础收入同比增幅

筛选条件：2024年总收入 > 200亿（K列），排除"合计/南方省/北方省"汇总行，共7省。

```
省份    2024总收入    基础应收总额同比增幅    基础收入同比增幅
广东    619.80亿       +3.6%                +1.0%
江苏    508.73亿      -14.1%                +1.8%
浙江    339.31亿       +3.9%                +2.8%
上海    329.35亿      -29.9%                -4.7%
四川    318.23亿      -11.2%                +1.2%
湖南    223.30亿      -12.6%                +3.0%
安徽    218.57亿      +19.2%                -1.0%
```

### 趋势对比

**1. 基础应收总额同比增幅波动剧烈，基础收入同比增幅窄幅震荡。**
- 应收增幅区间：-29.9%（上海）到 +19.2%（安徽），极差约49个百分点。
- 收入增幅区间：-4.7%（上海）到 +3.0%（湖南），极差仅约8个百分点。

**2. 两者走势无明显同向性，多数省份出现背离。**
- 同向（应收和收入方向一致）：广东（双增）、浙江（双增）、上海（双减）——仅3省。
- 背离（应收降但收入增）：江苏、四川、湖南——3省应收在降，收入反而微增。
- 背离（应收大增但收入降）：安徽——应收暴增19.2%，收入却微降1.0%。

**3. 上海是唯一"双杀"省份**：应收-29.9%、收入-4.7%，两项均为负且应收降幅极为突出。

**4. 广东、浙江表现最稳**：两项指标均为正，且数值接近，反映应收与收入增长基本匹配。

**5. 江苏、四川、湖南值得关注**：应收在收缩但收入稳中有升，可能意味着回款节奏变化或业务结构调整。

---

### 使用的候选表

| 文件名 | 用途 |
|--------|------|
| 全国各省份数据-通报应收总额_202508.xlsx | 核心数据源：提供各省AH列"基础业务应收总额同比增幅"、AL列"基础业务收入同比增幅"、K列"2024年总收入"用于筛选 |

### 候选表说明

- **表2**（全国各省份数据-通报应收总额_202508.xlsx）完全覆盖需求，数据充足。
- **表1**（市州数据）为市州级、**表3**（长账龄）为长账龄主题，均不直接适用。
- **表4-8** 为其他月份市州数据，
```

### raw_eval_0044_d494105389

Question: 2025年9月，各省（年收入>200亿），“预收账款”与“预收占收比”趋势对比。

| Rank | Table | Score | Scope | Subject | Month | Reasons |
| ---: | --- | ---: | --- | --- | --- | --- |
| 1 | 市州数据-市州应收账款情况表_202509.xlsx | 36.0 | city | 应收账款 | 202509 | filename:2025, preview:200, keyword:占收比, month:202509, domain:receivable |
| 2 | 全国各省份数据-通报应收总额_202509.xlsx | 34.0 | province | 通报应收总额 | 202509 | filename:2025, keyword:占收比, month:202509, domain:receivable |
| 3 | 全国各省份数据-长账龄_202509.xlsx | 30.0 | province | 长账龄 | 202509 | filename:2025, month:202509, domain:receivable |
| 4 | 区县数据-欠费数据.xlsx | 28.0 | county | 欠费 | - | preview:2025, preview:200, keyword:占收比, year-series-ledger, domain:receivable |
| 5 | 市州数据-市州应收账款情况表_202501.xlsx | 28.0 | city | 应收账款 | 202501 | filename:2025, preview:200, keyword:占收比, year-match, domain:receivable |
| 6 | 市州数据-市州应收账款情况表_202502.xlsx | 28.0 | city | 应收账款 | 202502 | filename:2025, preview:200, keyword:占收比, year-match, domain:receivable |
| 7 | 市州数据-市州应收账款情况表_202503.xlsx | 28.0 | city | 应收账款 | 202503 | filename:2025, preview:200, keyword:占收比, year-match, domain:receivable |
| 8 | 市州数据-市州应收账款情况表_202504.xlsx | 28.0 | city | 应收账款 | 202504 | filename:2025, preview:200, keyword:占收比, year-match, domain:receivable |

Answer preview:

```text
数据已提取完毕，以下是分析结果。

---

## 2025年9月 | 年收入>200亿省份 | 预收账款与预收占收比趋势对比

**筛选条件**：2024年总收入 > 200亿元，共筛选出 **7 个省份**（合计行已排除）。

| 省份 | 2024.09 预收款(亿) | 2025.09 预收款(亿) | 同比增幅 | 2024.09 占收比 | 2025.09 占收比 | 占收比变动(PP) |
|------|-------------------|-------------------|---------|---------------|---------------|---------------|
| 广东 | 66.55 | 70.31 | +5.6% | 10.80% | 11.30% | +0.50 |
| 江苏 | 71.91 | 71.27 | -0.9% | 14.20% | 13.80% | -0.40 |
| 浙江 | 50.86 | 50.20 | -1.3% | 14.70% | 14.30% | -0.40 |
| 上海 | 38.16 | 39.21 | +2.8% | 11.70% | 12.00% | +0.30 |
| 四川 | 17.92 | 24.83 | +38.6% | 5.60% | 7.80% | +2.20 |
| 湖南 | 28.24 | 31.20 | +10.5% | 12.60% | 13.30% | +0.70 |
| 安徽 | 18.12 | 19.86 | +9.6% | 8.40% | 9.10% | +0.70 |

**关键发现**：

- **预收账款规模**：江苏（71.27亿）和广东（70.31亿）遥遥领先，占7省预收款总额的近一半。
- **增速分化明显**：四川同比暴增 +38.6%，而江苏、浙江微降（-0.9%、-1.3%），呈现明显分化。
- **占收比**：浙江（14.30%）和江苏（13.80%）占收比最高，但同比均下滑；四川占收比最低（7.80%）但增幅最大（+2.20PP）。
- **整体趋势**：7省中5省预收占收比同比提升，江苏、浙江小幅回落，整体呈改善趋势。

---

### 使用的表格

| 用途 | 文件 | 是否候选表 |
|------|------|-----------|
| 预收账款 & 预收占收比数据 | `全国各省份数据-营业现金比率_202509.xlsx` | ❌ 不在候选表 |
| 年收入筛选（2024年总收入） | `全国各省份数据-通报应收总额_202509.xlsx` | ✅ 候选表 #2 |

### 候选表缺口说明

候选表中 **没有任何一张表包含"预收账款"字段**。候选表 #2（通报应收总额）虽有省份维度和收入
```

### raw_eval_0016_73abb469f5

Question: 2025年10月，总欠费占收比最高的5个市州是哪些？这5个市州的总欠费分别是多少？

| Rank | Table | Score | Scope | Subject | Month | Reasons |
| ---: | --- | ---: | --- | --- | --- | --- |
| 1 | 市州数据-欠费数据_台账.xlsx | 70.0 | city | 欠费 | - | keyword:占收比, keyword:总欠费, preview:10, filename:市州, filename:欠费, year-series-ledger, domain:arrears, domain:receivable, scope:city |
| 2 | 市州数据-市州应收账款情况表_202510.xlsx | 56.0 | city | 应收账款 | 202510 | filename:2025, keyword:占收比, filename:10, filename:市州, month:202510, domain:receivable, scope:city |
| 3 | 区县数据-欠费数据.xlsx | 54.0 | county | 欠费 | - | preview:2025, keyword:占收比, preview:10, filename:欠费, year-series-ledger, domain:arrears, domain:receivable |
| 4 | 市州数据-50万以上大额长账督办待回收情况_202510.xlsx | 52.0 | city | 大额长账 | 202510 | filename:2025, filename:10, filename:市州, month:202510, domain:receivable, scope:city |
| 5 | 全国各省份数据-通报应收总额_202510.xlsx | 42.0 | province | 通报应收总额 | 202510 | filename:2025, keyword:占收比, filename:10, month:202510, domain:receivable |
| 6 | 市州数据-市州应收账款情况表_202501.xlsx | 42.0 | city | 应收账款 | 202501 | filename:2025, keyword:占收比, preview:10, filename:市州, year-match, domain:receivable, scope:city |
| 7 | 市州数据-市州应收账款情况表_202502.xlsx | 42.0 | city | 应收账款 | 202502 | filename:2025, keyword:占收比, preview:10, filename:市州, year-match, domain:receivable, scope:city |
| 8 | 市州数据-市州应收账款情况表_202503.xlsx | 42.0 | city | 应收账款 | 202503 | filename:2025, keyword:占收比, preview:10, filename:市州, year-match, domain:receivable, scope:city |

Answer preview:

```text
**2025年10月总欠费占收比最高的5个市州：**

| 排名 | 市州 | 总欠费（万元） | 占收比 |
|------|------|--------------|--------|
| 1 | 巴中 | 17,314.42 | 21.53% |
| 2 | 甘孜 | 11,177.24 | 19.63% |
| 3 | 攀枝花 | 7,426.49 | 19.39% |
| 4 | 乐山 | 22,706.64 | 19.05% |
| 5 | 阿坝 | 8,113.34 | 18.84% |

---

**使用的候选表文件名：**
- `市州数据-欠费数据_台账.xlsx`（table_id=tbl_d6dc87e47b，score=70.0）—— Sheet「总欠费数据」，2025年10月列（col 176 欠费金额万元 / col 178 占收比%），共21个市州，排除合计行后按占收比降序取前5。

**是否成功完成：** 是。
```

### raw_eval_0017_136f8511e9

Question: 2025年10月，总欠费同比增幅最高的5个市州是哪些？分别的总欠费金额是多少？

| Rank | Table | Score | Scope | Subject | Month | Reasons |
| ---: | --- | ---: | --- | --- | --- | --- |
| 1 | 市州数据-欠费数据_台账.xlsx | 58.0 | city | 欠费 | - | keyword:总欠费, preview:10, keyword:同比, filename:市州, filename:欠费, year-series-ledger, domain:arrears, scope:city |
| 2 | 市州数据-市州应收账款情况表_202510.xlsx | 48.0 | city | 应收账款 | 202510 | filename:2025, filename:10, keyword:同比, keyword:增幅, filename:市州, month:202510, scope:city |
| 3 | 区县数据-欠费数据.xlsx | 42.0 | county | 欠费 | - | preview:2025, preview:10, keyword:同比, filename:欠费, year-series-ledger, domain:arrears |
| 4 | 市州数据-50万以上大额长账督办待回收情况_202510.xlsx | 40.0 | city | 大额长账 | 202510 | filename:2025, filename:10, filename:市州, month:202510, scope:city |
| 5 | 全国各省份数据-营业收现率_202510.xlsx | 34.0 | province | 营业收现率 | 202510 | filename:2025, filename:10, keyword:同比, keyword:增幅, month:202510 |
| 6 | 全国各省份数据-通报应收总额_202510.xlsx | 34.0 | province | 通报应收总额 | 202510 | filename:2025, filename:10, keyword:同比, keyword:增幅, month:202510 |
| 7 | 全国各省份数据-长账龄_202510.xlsx | 34.0 | province | 长账龄 | 202510 | filename:2025, filename:10, keyword:同比, keyword:增幅, month:202510 |
| 8 | 市州数据-市州应收账款情况表_202501.xlsx | 34.0 | city | 应收账款 | 202501 | filename:2025, preview:10, keyword:同比, keyword:增幅, filename:市州, year-match, scope:city |

Answer preview:

```text
结果已从候选表中提取完毕。

---

**2025年10月 总欠费同比增幅 Top 5 市州：**

| 排名 | 市州 | 总欠费（万元） | 同比增幅 |
|------|------|---------------|----------|
| 1 | 宜宾 | 17,540.56 | 103.72% |
| 2 | 眉山 | 10,874.75 | 65.41% |
| 3 | 遂宁 | 8,553.44 | 49.17% |
| 4 | 广元 | 10,192.45 | 47.54% |
| 5 | 资阳 | 7,896.43 | 40.95% |

---

**使用的候选表：**
- `市州数据-欠费数据_台账.xlsx`（候选1，tbl_d6dc87e47b）→ Sheet「总欠费数据」→ 区块「总欠费分析（分已列收和未列收）」，取 202510 列（欠费金额=176列，同比=177列），R6-R26 共21个市州。

**候选表2**（市州应收账款情况表_202510.xlsx）虽月份匹配，但其主题是"应收账款"而非"总欠费"，与本问口径不一致，故未采用。

**是否成功完成：** 是。
```

### raw_eval_0018_0fcb224585

Question: 2025年11月，总欠费占收比最高的5个市州是哪些？这5个市州的总欠费分别是多少？

| Rank | Table | Score | Scope | Subject | Month | Reasons |
| ---: | --- | ---: | --- | --- | --- | --- |
| 1 | 市州数据-欠费数据_台账.xlsx | 70.0 | city | 欠费 | - | keyword:占收比, keyword:总欠费, preview:11, filename:市州, filename:欠费, year-series-ledger, domain:arrears, domain:receivable, scope:city |
| 2 | 市州数据-市州应收账款情况表_202511.xlsx | 56.0 | city | 应收账款 | 202511 | filename:2025, keyword:占收比, filename:11, filename:市州, month:202511, domain:receivable, scope:city |
| 3 | 区县数据-欠费数据.xlsx | 52.0 | county | 欠费 | - | preview:2025, keyword:占收比, filename:欠费, year-series-ledger, domain:arrears, domain:receivable |
| 4 | 全国各省份数据-通报应收总额_202511.xlsx | 42.0 | province | 通报应收总额 | 202511 | filename:2025, keyword:占收比, filename:11, month:202511, domain:receivable |
| 5 | 市州数据-市州应收账款情况表_202501.xlsx | 42.0 | city | 应收账款 | 202501 | filename:2025, keyword:占收比, preview:11, filename:市州, year-match, domain:receivable, scope:city |
| 6 | 市州数据-市州应收账款情况表_202502.xlsx | 42.0 | city | 应收账款 | 202502 | filename:2025, keyword:占收比, preview:11, filename:市州, year-match, domain:receivable, scope:city |
| 7 | 市州数据-市州应收账款情况表_202503.xlsx | 42.0 | city | 应收账款 | 202503 | filename:2025, keyword:占收比, preview:11, filename:市州, year-match, domain:receivable, scope:city |
| 8 | 市州数据-市州应收账款情况表_202504.xlsx | 42.0 | city | 应收账款 | 202504 | filename:2025, keyword:占收比, preview:11, filename:市州, year-match, domain:receivable, scope:city |

Answer preview:

```text
**2025年11月，总欠费占收比最高的5个市州：**

| 排名 | 市州 | 总欠费（万元） | 占收比 |
|------|------|---------------|--------|
| 1 | 巴中 | 16,891.96 | 21.08% |
| 2 | 甘孜 | 11,740.33 | 20.53% |
| 3 | 攀枝花 | 7,524.29 | 19.47% |
| 4 | 阿坝 | 8,267.39 | 19.05% |
| 5 | 乐山 | 21,774.44 | 18.22% |

**参考：** 同期四川全省合计总欠费 524,349.90 万元，占收比 16.76%。

---

**使用的候选表：**
- `市州数据-欠费数据_台账.xlsx`（table_id=tbl_d6dc87e47b, score=70.0）— 工作表「总欠费数据」，202511列（欠费金额 + 占收比）

**未使用的候选表：**
- 候选表2（市州应收账款情况表_202511）是"应收账款"口径，与用户问的"总欠费"概念不同，不需要使用。
- 其余候选表为区县级/省级/其他月份，不匹配。

**是否成功完成：** ✅ 是
```
