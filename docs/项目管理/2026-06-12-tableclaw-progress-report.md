# TableClaw 阶段进展报告

> 历史归档：本文记录 2026-06-12 阶段状态，部分底座名称、开发原则和评测结论已经被后续 README 与评测归档更新。当前项目定位以根目录 `README.md`、`docs/README.md` 和最新 gold-cases run 为准。

## 1. 项目背景

TableClaw 是基于 Nanobot 构建的本地工业表格 agent 原型，目标是面向真实业务表格任务，形成从上传表召回、结构理解、指标定位、数值计算、图表底表生成到结果验证的完整 workflow。

项目背景来自两类需求：

- 真实工业表通常不是规则数据表，而是多 sheet、多级表头、合并单元格、横向月份、汇总行、公式列、空值和业务口径混杂的 workbook。
- 通用大模型可以通过自主探索完成部分复杂任务，但在成本、耗时、稳定性和可复现性上存在明显不足；需要将高频、确定、可验证的表格操作沉淀为工具和 skill。

因此，TableClaw 的目标不是做单点“表格问答”，而是逐步覆盖表格上下游能力：

| 能力方向 | 说明 |
| --- | --- |
| table read | 读取 workbook、sheet、range、表头、合并单元格、公式和指标列 |
| table clean | 处理空行、汇总行、缺失值、类型混用和重复记录 |
| table QA | 回答指标、排名、筛选、趋势、对比等业务问题 |
| chart data | 生成可用于绘图的底层数据表，而非优先追求图形渲染 |
| formula debug | 识别公式错误、引用错误和缓存值异常 |
| validate | 对结果进行口径说明、数值校验和证据追踪 |
| report | 将结构化结果转化为管理报告或风险分析 |

当前阶段的重点是先把“找对表、找对行列、算对数值、说明口径”打稳，再将可视化渲染、报告排版等能力交给后续前端或专用绘图模块承接。

## 2. 设计原则

当前开发遵循以下原则：

```text
通用探索能力兜底
+
稳定工具加速高频路径
+
skill/memory 承接半结构化经验
+
评测闭环决定什么该固化、什么该保持开放
```

具体含义如下：

- 基模负责未知问题中的探索、规划、质疑和临时代码执行。
- 工具负责将高频、确定、可测试的表格动作变得低成本、稳定、可复用。
- skill 负责承接流程性经验，例如如何读多级表头、如何做图表底表、如何校验口径。
- memory / domain knowledge 负责承接业务术语、固定定义和表族经验。
- 评测负责判断一项规则是否具有全局收益，避免为单个 case 写死逻辑后影响其他任务。

该路线的核心不是在“完全依赖模型探索”和“完全工具写死”之间二选一，而是建立持续闭环：

```text
模型探索 -> 发现可复用模式 -> 工具/skill/memory 化 -> gold case 评测
-> 失败样本回流 -> 继续拆分和验证
```

## 3. 项目架构

TableClaw 当前由 Nanobot 主框架、TableClaw 工具层、skill 系统、运行态 workspace 和评测系统组成。

### 3.1 Nanobot 主框架

Nanobot 提供 agent 主循环、LLM provider、工具注册、skill 加载、workspace 访问、会话管理、memory、usage 记录和评测执行入口。TableClaw 没有重写 Nanobot 主循环，而是在其工具和 skill 体系中扩展表格能力。

关键模块包括：

| 模块 | 作用 |
| --- | --- |
| `nanobot/nanobot/agent/loop.py` | agent 主循环、上下文构建、工具执行调度 |
| `nanobot/nanobot/providers/` | DeepSeek / DashScope 等 OpenAI-compatible provider 接入 |
| `nanobot/nanobot/agent/tools/` | 文件、shell、search、TableClaw 等工具注册 |
| `nanobot/nanobot/agent/skills.py` | builtin skill 和 workspace skill 的加载与注入 |
| `workspace/usage/usage.jsonl` | 记录 token、工具和延迟信息 |

### 3.2 TableClaw 工具层

核心工具位于：

```text
nanobot/nanobot/agent/tools/tableclaw.py
```

工具层承担确定性表格动作，当前能力包括：

| 工具 | 功能定位 |
| --- | --- |
| `tableclaw_catalog_tables` | 生成上传表 profile/catalog，为召回和规划提供上下文 |
| `tableclaw_retrieve_tables` | 根据题面时间、指标、地域、单位和文件名线索召回候选表 |
| `tableclaw_inspect` | 读取 workbook 结构、sheet、表头、列概况和样例行，并复用 schema cache |
| `tableclaw_locate_column` | 在多级表头、合并表头和宽表中定位目标指标列 |
| `tableclaw_extract_matrix` | 抽取多实体、多指标矩阵，并输出 answer_markdown / chart_table |
| `tableclaw_time_series` | 跨月文件抽取时间序列，支持增长和环比计算 |
| `tableclaw_horizontal_series` | 处理横向月份展开的宽表和台账结构 |
| `tableclaw_extract_series` | 从单表或表族中抽取指定实体、指标序列 |
| `tableclaw_topk` | 执行 top-k / bottom-k 排序，并支持伴随指标 |
| `tableclaw_rank` | 计算实体排名、cohort 排名，并处理百分比混合编码 |
| `tableclaw_filter` | 执行条件筛选；当前仍需加强多条件口径校验 |

当前最有效的工具方向是让工具直接返回可用于最终回答或绘图的数据表，而不只是返回低层 JSON。这样可以减少模型二次整理、转置和格式改写中的错误。

### 3.3 Skill 与 Memory

TableClaw 不只依赖工具。Nanobot 的 skill 机制用于让模型在复杂任务中读取流程性说明。

当前相关 skill 包括：

| Skill | 作用 |
| --- | --- |
| `xlsx` | 通用 spreadsheet skill，提供 workbook 创建、编辑、渲染和验证兜底能力 |
| `table-read` | 表结构读取、表头识别、指标列定位 |
| `table-clean` | 空行、汇总行、缺失值和类型问题处理 |
| `table-validate` | 口径、数值、排序和证据校验 |
| `table-chart` | 图表类型选择和 chart-ready summary |
| `table-report` | 管理摘要、风险列表和报告表达 |
| `table-formula-debug` | 公式读取、错误值和引用修复 |

skill 分为 builtin 和 workspace 两层：

- builtin skill 放在 `nanobot/nanobot/skills/`，适合产品级通用能力。
- workspace skill 放在 `workspace/skills/`，适合客户或项目级业务规则覆盖。

后续业务知识不宜全部写入核心工具。固定业务定义、术语解释和表族经验更适合进入 workspace skill、memory 或 domain glossary，再由工具层执行确定性计算。

### 3.4 Workspace、Catalog 与 Schema Cache

运行态数据集中在 `workspace/`：

| 路径 | 作用 |
| --- | --- |
| `workspace/uploads/` | 模拟用户上传表，作为问题回答的数据来源 |
| `workspace/table_index/tables.jsonl` | 轻量召回索引 |
| `workspace/table_cache/*.schema.json` | `tableclaw_inspect` 生成的 schema cache |
| `workspace/table_catalog/catalog.jsonl` | 表级 catalog 入口 |
| `workspace/table_catalog/profiles/` | 确定性 profile |
| `workspace/table_catalog/clean_views/` | 不修改源表的虚拟 clean view |
| `workspace/table_catalog/descriptions/` | LLM/fallback 生成的表语义描述 |

Catalog 的定位是导航和规划上下文，不作为最终事实证据。最终数值仍需回到源表、schema cache 或 clean view 读取和验证。

### 3.5 评测系统

当前主评测为 40 条人工 gold case：

```text
eval_test/test_dataset/gold_cases.jsonl
```

评测流程：

1. 用户问题不显式给出表路径。
2. 上传表位于 `workspace/uploads/`。
3. agent 先召回候选表，再 inspect 表结构。
4. agent 按需调用 TableClaw 工具、skill 或简短代码完成任务。
5. gold answer 不进入 prompt，仅在答案生成后用于 judge。
6. 记录 answer、judge、工具轨迹、token、耗时和任务类型表现。

当前 judge 已调整为以数据正确性为主。图表类任务当前评估底层绘图数据是否正确，不因未生成真实图片或 Markdown 排版差异而重罚。

## 4. 迭代过程

TableClaw 的迭代过程主要围绕“召回是否准确、表内 grounding 是否稳定、工具输出是否接近最终答案、评测是否真实反映数据正确性”展开。

| 阶段 | ACC | 主要变化 | 结论 |
| --- | ---: | --- | --- |
| v1 baseline | 40.00% | 基础 retrieve + inspect + 临时代码 | ranking 有一定基础，chart/filter 较弱 |
| v2 forced tools | 37.50% | prompt 强制优先调用工具 | 强制流程限制模型自主判断，整体下降 |
| v4 catalog | 47.50% | 引入表 catalog/profile | 召回增强带来提升 |
| v5 structured retrieval | 52.50% | 增加 query intent、constraint score、表族发现 | 结构化召回继续提升 |
| v6 rank tool | 45.00% | 新增 `tableclaw_rank` | case001 修复，但整体回落，说明单一 rank 工具不是全局解 |
| v7 rank/header path | 57.50% | 强化 rank 官方列路径与 header path | 相比 v6 回升，但 filter 仍弱 |
| v8 topk companion | 45.00% | 增加 topk 伴随列和多实体输出 | ranking 较强，chart 回落 |
| v9h answer_markdown | 67.50% | matrix/time_series 输出可复制底表 | 证明“最终形态底表”对 chart/table/trend 有明显价值 |
| current full40 after horizontal_series | 80.00% | 增强横向序列和底表输出路径 | 历史最高记录，但后续回退重跑未稳定复现 |
| v10 general fixes | 60.00% | 汇总行排除、rounding、占比默认方向等同时加入 | 局部 chart 提升，但整体回退，需要拆分 A/B |
| rollback high baseline | 70.00% | 回退至高基线附近重跑 | 受 API 认证/runtime error 和随机探索影响，未完全复现 80% |

迭代过程中有三个关键观察：

1. 强制工具调用不一定提升准确率。v2 相比 baseline 下降，说明模型仍需要自主规划空间。
2. 结构化召回和 catalog 有稳定收益。v4、v5 提升说明先找对表是后续读算的前提。
3. 最有效的改动是让工具输出接近最终答案。v9h 与当前最高 run 的提升主要来自 `answer_markdown`、`chart_table` 和横向序列能力。

## 5. 历史最佳记录与复现情况

当前已归档最高 full40 结果如下。该结果代表现有迭代过程中的历史最佳表现，但由于后续回退重跑受到 API 认证错误、runtime error 和模型随机探索路径影响，目前尚未将其稳定复现为可持续基线。

| 指标 | 结果 |
| --- | ---: |
| Run id | `2026-06-12-current-full40-after-horizontal-series` |
| 测试集规模 | 40 cases |
| 判定结果 | 32 correct / 2 partial / 6 incorrect |
| ACC | 80.00% |
| Avg judge score | 0.8125 |
| Total answer tokens | 12,906,668 |
| Total judge tokens | 50,573 |
| Avg elapsed | 110.45s / case |
| 归档报告 | `docs/实验评测/gold-cases/runs/2026-06-12-current-full40-after-horizontal-series.md` |

按任务类型：

| 任务类型 | 数量 | ACC | 说明 |
| --- | ---: | ---: | --- |
| `ranking_qa` | 11 | 100.00% | 排名类任务已较稳定，`tableclaw_rank` 与占比归一化发挥主要作用 |
| `table_qa` | 3 | 100.00% | 单表、单实体或少量指标问答表现稳定 |
| `trend_table` | 2 | 100.00% | 跨月序列抽取与环比/增长计算路径有效 |
| `chart_generation` | 22 | 72.73% | 输出图表底层数据表后明显提升，但多省、多指标完整性仍需加强 |
| `filter_qa` | 2 | 0.00% | 多条件筛选、cohort 判断和排名组合仍是主要短板 |

该结果说明当前工具层已经具备较强的表格定位、排名计算、跨月序列和图表底表生成能力；主要短板集中在更复杂的条件筛选和业务 cohort 解释上。后续评测应将 80.00% 作为历史最高参考点，而不是已稳定复现的最终水平。

## 6. 当前问题分析

### 6.1 多条件筛选能力不足

`filter_qa` 当前准确率为 0%。此类任务通常同时包含 cohort、指标方向、排名条件、时间口径等约束。现有工具可以生成部分底表，但缺少稳定的“条件解释、执行、反查验证”链路。

### 6.2 `200亿省` 属于业务知识

当前工具主要依据表内收入阈值动态计算 `200亿省`。当目标月份表缺少收入字段、数据稀疏，或 gold 使用外部固定 cohort 时，动态计算会失效。该知识更适合放入 domain memory / glossary，而不是硬编码进通用 rank/filter 逻辑。

### 6.3 2025-12 稀疏表问题

部分 2025-12 省份表中只有四川等少数省份有完整指标，其他省份目标字段为空；但 gold case 中存在多省答案。这类问题需要表族召回、前后期补表、业务知识或外部补充材料支撑，不能仅通过调整排序或筛选工具解决。

### 6.4 图表任务中的多实体完整性

部分 chart case 中模型只输出四川，缺失同一 cohort 下其他省份。说明在调用矩阵工具前，实体集合确定仍不稳定。后续需要加强 cohort 展开、实体列表校验和输出完整性检查。

### 6.5 API 可用性与复现不稳定

近期 DeepSeek / DashScope 评测链路出现 API key 认证问题，导致部分回退重跑出现 runtime error。同时，即使回退到接近历史最高 run 的代码状态，full40 结果也未稳定复现 80.00%。这说明当前系统仍受到基模探索路径、API 可用性和评测环境波动影响，需要在后续阶段重新建立更稳定的可复现基线。

## 7. 后续计划

1. 将 80.00% run 作为历史最高参考点保留，不再假设当前代码状态可以稳定复现该结果。
2. 在 DeepSeek API 暂不可用、且历史最高 run 难以稳定复现的情况下，后续主线临时切换为 `GPT-5.5 + 当前 TableClaw 工具层`，用于继续生成高质量轨迹和验证工具编排。
3. 合并老师之前开发版本中的有效能力，重点吸收其中的业务知识、召回策略、口径定义和 bad case 处理经验；合并时按模块拆分，不直接整体覆盖当前工具层。
4. 将业务知识按稳定程度分别沉淀到 domain memory、workspace skill、工具函数或可检索材料中。例如 `200亿省`、省份 cohort、表族口径、2025-12 稀疏表等问题，应优先进入 domain knowledge 层。
5. 对老师版本、当前版本和 GPT-5.5 轨迹中的成功路径做对齐，形成新的评测基准和执行规范，再重新跑 full40。
6. 后续新增的一批 bad case 作为重点回归集，与 full40 同步使用：先单 case 修复，再小集合回归，最后 full40 验证全局影响。
7. 对 v10 中曾带来局部提升但整体回退的补丁继续做单项 A/B，不一次性合入多个规则。
8. 在业务知识、召回和工具层进一步稳定后，再切换更小或更便宜的模型复测，验证工具/skill/memory 是否能够降低对强基模的依赖。

## 8. 阶段结论

TableClaw 已从初始的“模型临时读表”演进为“Nanobot 编排 + TableClaw 工具层 + skill/memory + catalog/cache + gold eval”的表格 agent 原型。历史最高 full40 ACC 达到 80.00%，其中 ranking、table_qa 和 trend_table 表现稳定，chart_generation 明显提升，filter_qa 与业务 cohort 是后续主要优化方向。

下一阶段的重点不是继续堆叠单点规则，而是在当前工具层基础上融合已有业务知识版本，并使用 GPT-5.5 和后续 bad case 持续迭代：补充业务知识、加强多条件 filter、完善 cohort 展开、改进稀疏表和表族召回，并通过重点 bad case 与 full40 的循环评测验证每一项改动的全局收益。
