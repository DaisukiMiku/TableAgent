# TableClaw

TableClaw 是一个基于 Nanobot 的通用 Table Agent 原型。它面向真实业务表格工作流，把上传表召回、schema/cache、确定性读算工具、domain skill、domain knowledge 和评测闭环组合在一起。

当前项目用“四川财资工业表格”作为第一个领域包验证路线，但 TableClaw 的底层目标不是写死四川业务，而是形成可插拔架构：换到另一个行业或客户时，保留 Nanobot + 通用表格工具，只新增对应领域的 skill、domain knowledge、RAG/memory 和必要的专属工具。

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

TableClaw 不追求把所有表格推理都写死成工具，也不把所有问题都交给模型临场探索。当前方向是在两者之间建立可验证的循环：

```text
临场探索 -> 发现可复用模式 -> 工具/skill 化 -> 评测验证
-> 失败样本回流 -> 更新工具/skill/memory -> 再评测
```

## 下一版架构：通用 Agent + 可插拔领域包

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
  ↓
Answer / Report / Evidence
  - 数值、表格、图表底表、来源说明、可追溯记录
```

一句话原则：

> Skill 是调度说明书，domain knowledge 是业务记忆，TableClaw tools 是执行器。

### 三层职责边界

| 层 | 职责 | 不应该做 |
| --- | --- | --- |
| Domain Skill | 识别领域任务，规定策略顺序，例如“这是四川财资问题，先查 domain knowledge，再抽表验证”。 | 不直接给最终数值答案。 |
| Domain Knowledge | 返回结构化业务上下文，例如 `200亿省` 名单、指标别名、表族建议、排名方向、稀疏表处理经验。 | 不替代原始表格证据，不把每个 case 的答案写成答案库。 |
| Generic Tools | 按给定实体、指标、表路径执行召回、inspect、矩阵抽取、排名、筛选、时间序列等确定性操作。 | 不写死四川财资、某个客户或某个评测集的业务规则。 |

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
