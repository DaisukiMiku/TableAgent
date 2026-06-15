# TableClaw

TableClaw 是一个基于 Nanobot 的通用 Table Agent 原型。它面向真实业务表格工作流，把 agent 底层编排、memory、tool、workspace、harness、上传表召回、schema/cache、确定性读算工具、domain skill、domain knowledge 和评测闭环组合在一起。

当前项目用“四川财资工业表格”作为第一个领域包验证路线，但 TableClaw 的底层目标不是写死四川业务，而是形成可插拔架构：换到另一个行业、客户或 To C 单表场景时，保留 Nanobot + 通用表格工具，只新增或启用对应领域的 skill、domain knowledge、RAG/memory 和必要的专属工具。

## 核心思想

```text
通用探索能力兜底
+
稳定工具加速高频路径
+
skill/memory 承接半结构化经验
+
评测闭环决定什么该固化、什么该保持开放
```

含义：

- 基模负责未知问题中的探索、质疑、反证和临时代码执行。
- 工具负责把高频、确定、可测试的表格动作变得便宜和稳定。
- skill/memory/domain knowledge 负责沉淀“怎么做一类任务”的过程知识和业务口径，保留比工具更柔性的经验。
- 评测负责约束工具和 skill 的演进，避免只对单个 case 有效而伤害其他任务。

TableClaw 不追求把所有表格推理都写死成工具，也不把所有问题都交给模型临场探索。它不是让一个空 agent 从零开始摸索，而是先提供一组初始 agent/tool/harness 底座，再通过真实任务和评测闭环持续进化：

```text
初始工具底座
-> 临场探索
-> 发现可复用模式
-> 判断沉淀层级：domain knowledge / skill / generic table tool / core agent
-> 评测验证
-> 失败样本回流
-> 分层更新
-> 再评测
```

分层更新的原则是：越贴近业务，越快迭代；越靠近底座，越需要克制。

- Domain knowledge / skill 高频更新，用来沉淀业务口径、指标别名、执行策略、badcase 经验和 sparse fallback。
- Generic Table Tools 中频更新，用来沉淀跨 case、跨领域的表格结构和读算能力，例如多行表头、合并单元格、单位归一化、多条件筛选、排名、时间序列。
- Core Agent 低频更新，只在 tool 调用协议、memory/session、workspace、trace、harness、权限、并发等底层机制出现系统性问题时才改。

## 下一版架构：通用 Agent + 可插拔领域包

TableClaw 更准确的定位不是“一个写死流程的业务 agent”，而是一个表格 agent substrate：

- 底层编排负责把 agent 跑稳：session、memory、workspace、tool loading、skill loading、trace、usage、eval harness。
- 通用表格层负责跨领域能力：inspect、catalog、schema cache、retrieve、extract、rank、filter、time series、validate。
- domain pack 负责业务语义：行业术语、指标别名、表族经验、cohort、排序口径、sparse fallback、客户知识库和必要的专属工具。
- 基模负责在上下文里选择路径：多表 workspace 场景可以先召回，单表上传场景可以跳过召回直接 inspect；工具多不代表每轮都必须使用。

TableClaw 的理想分层是：

```text
User Query
  ↓
Nanobot Framework
  - 对话、工具调用、trace、session、workspace
  ↓
Domain Skill / Strategy Layer
  - 判断是否属于某个领域
  - 给出任务策略和调用顺序
  - 要求先查 domain knowledge，再交给通用工具执行
  ↓
Domain Knowledge / Memory Layer
  - 业务口径、指标别名、表族映射、cohort、排名方向
  - 可扩展为 RAG、badcase memory、客户知识库
  ↓
Generic TableClaw Tools / Execution Layer
  - retrieve / inspect / schema cache / catalog
  - extract_matrix / rank / filter / time_series
  - 只做领域无关的读表、定位、抽取、计算、验证
  - 工具是可选能力，不是固定流程；基模按任务选择是否调用
  ↓
Answer / Report / Evidence
  - 数值、表格、图表底表、来源说明、可追溯记录
```

一句话原则：

> Skill 是调度说明书，domain knowledge 是业务记忆，TableClaw tools 是执行器。

### 工具分层原则

TableClaw 的工具不应该只有“通用 / 非通用”两类。更合理的边界是：

| 工具层 | 示例 | 职责 |
| --- | --- | --- |
| Core Agent Tools | file、shell、web、memory、message、MCP | 提供 agent 通用运行能力，与表格和业务无关。 |
| Generic Table Tools | retrieve、inspect、catalog、extract_matrix、rank、filter、time_series、validate | 解决跨领域表格结构、抽取、计算和验证问题。 |
| Domain Tools | domain_knowledge、sparse_reconcile、客户专属口径解析器 | 处理离开该领域就没有自然意义的业务口径、fallback 和专属流程。 |

> Core Agent 让系统会做事，Generic Table Tools 让它擅长做表格，Domain Pack 让它懂某个行业/客户的表格。

判断一个能力放在哪里：

- 如果特殊性来自业务口径，例如 `200亿省`、`预收账款排名默认看预收占收比`、`2025-12 sparse 表 reporting fallback`，放进 domain pack。
- 如果特殊性来自普遍表格结构，例如多行表头、合并单元格、百分比编码、排名列识别、横向月份序列，沉淀成 generic table tool。
- 如果只是某个 badcase 的临场操作经验，先放 skill / domain knowledge / memory，经评测验证后再决定是否工具化。

### 三层职责边界

| 层 | 职责 | 不应该做 |
| --- | --- | --- |
| Domain Skill | 识别领域任务，规定策略顺序，例如“这是四川财资问题，先查 domain knowledge，再抽表验证”。 | 不直接给最终数值答案。 |
| Domain Knowledge | 返回结构化业务上下文，例如 `200亿省` 名单、指标别名、表族建议、排名方向、稀疏表处理经验。 | 不替代原始表格证据，不把每个 case 的答案写成答案库。 |
| Generic Tools | 按给定实体、指标、表路径执行召回、inspect、矩阵抽取、排名、筛选、时间序列等确定性操作。 | 不写死四川财资、某个客户或某个评测集的业务规则。 |

### 单表与多表工作流

`tableclaw_retrieve_tables` 是多表 workspace 场景下的能力，而不是 TableClaw 的强制入口。

- 多表/历史文件池：用户只问业务问题时，先召回候选表，再 inspect 和抽取。
- 单表上传：如果上下文只有一个 active table，或用户明确给出文件路径，可以直接 inspect，不需要召回。
- 已知 sheet/range：直接走 locate/extract/rank/filter/time_series。
- 业务语义不明确：先查 domain knowledge，再把明确的实体、指标、月份、表族提示交给通用工具执行。

因此，To C 单表场景不会否定召回工具的价值；它只是让召回从主路径变成可选 fallback。TableClaw 提供能力集合，具体路径由 skill、domain context 和基模共同决定。

### 当前领域包：四川财资

当前内置领域包位于：

```text
domain_packs/sichuan-finance/
├── skills/sichuan-finance/SKILL.md
└── knowledge/tableclaw_industrial_finance.json
```

启动和评测前会同步到 workspace：

```text
workspace/skills/sichuan-finance/SKILL.md
workspace/domain_knowledge/tableclaw_industrial_finance.json
```

例如，四川财资问题中：

- skill 负责提示：这是四川财资问题，先调用 `tableclaw_domain_knowledge`。
- domain knowledge 负责返回：`200亿省 = 广东、江苏、浙江、上海、四川、安徽、湖南`、基础应收总额优先找通报应收总额表的基础业务区、占收比/欠费类指标的排序口径。
- generic tools 负责执行：按实体、指标、月份和候选表抽出矩阵或排名，并返回可追溯的底层数据。

未来接入其他领域时，新增一个类似的 `domain_packs/<domain>/`，而不是改 Nanobot 主流程或把业务规则塞进通用工具。

## 快速入口

| 文档 | 用途 |
| --- | --- |
| [文档总览](docs/README.md) | 项目文档入口，包含架构、功能开发、实验评测和项目管理索引。 |
| [Domain Knowledge Migration](docs/功能开发/domain-knowledge-migration.md) | 说明领域包、skill、domain knowledge 与通用工具的边界。 |
| [Gold Cases Benchmark](docs/实验评测/gold-cases/README.md) | 40 条人工 gold case 的 benchmark 入口和历史 run。 |
| [Run History](docs/实验评测/gold-cases/runs/README.md) | 已归档的 40-case benchmark 与专项 case 对比报告。 |
| [Latest Eval: Mandatory Overrides + Judge V2](docs/实验评测/gold-cases/runs/2026-06-14-mandatory-overrides-judge-v2.md) | 当前最新主线评测归档：gold40 A/B 与 badcase122 A/B。 |
| [开发日志](docs/项目管理/development-log.md) | 按时间记录关键决策、实现和评测结果。 |

## 常用命令

```bash
./start.sh
./eval_gold_parallel.sh --concurrency 4
```
