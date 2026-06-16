# TableClaw

TableClaw 是一个通用 Table Agent 项目。它面向真实业务表格工作流，把 agent 底层编排、tool、workspace、harness、memory、上传表管理、schema/cache、确定性读算工具、domain skill、domain knowledge 和评测观察组合在一起。

当前项目用“四川财资工业表格”作为第一个领域包验证路线，但 TableClaw 的底层目标不是写死四川业务，而是形成可插拔架构：换到另一个行业、客户或 To C 单表场景时，保留 agent core + 通用表格工具，只新增或启用对应领域的 skill、domain knowledge、memory/RAG 和必要的专属工具。

## 当前状态

- 长期产品方向：To C / 通用 Table Agent。用户可以只上传一张表，也可以在多表 workspace 中连续分析。
- 当前工程验证：四川财资工业表格 domain pack，用来验证多表召回、领域口径、sparse fallback、确定性读算工具和评测体系。
- 最新正式评测：`2026-06-16 v4rerun Five-Way Eval`。
  - badcase122 两轮完整 ACC：88.93%。
  - query100 三个随机 split 完整 ACC：89.00%。
- 当前主要短板：badcase run-to-run 波动、sparse/reporting fallback 的执行稳定性、ranking / reporting 口径冲突，以及 mandatory override 仍主要依赖模型自行读取和融合。

## 核心定位

TableClaw 的核心不是把某个业务流程写死，也不是假设模型可以在每个问题里从零探索。它要做的是一个面向表格任务的 Agent 能力栈，让表格工作从“模型临场猜和写代码”逐步变成“有工具、有口径、有记忆、有证据、有可追踪过程”的稳定执行系统。

这个能力栈包括：

- Core Agent：负责稳定执行，包括对话、工具调用、workspace、trace、权限、运行状态和任务上下文。
- Generic Table Tools：负责通用表格能力，包括上传表管理、结构理解、schema/cache、catalog、抽取、排序、筛选、时间序列和校验。
- Skill / Domain Knowledge / Memory：负责上下文和经验存储。Skill 说明一类任务怎么做；domain knowledge 保存领域/客户的稳定业务知识；memory 保存当前会话、用户、团队或历史任务中被确认过的上下文、偏好和经验。
- Domain Pack：负责领域适配，把某个行业/客户需要的 skill、domain knowledge、memory/RAG、评测样本和必要专属工具组织在一起。
- Harness / Eval：负责观察和验证，包括记录任务过程、比较结果、发现错误类型，为人工判断、知识维护和工程迭代提供依据。

一句话：

> Core Agent 让系统会做事，Generic Table Tools 让它擅长做表格，Skill / Domain Knowledge / Memory 让它带着上下文和经验工作，Domain Pack 让它懂某个行业/客户的表格，Harness 让每次改动有证据可看。

## 架构分层

TableClaw 更准确的定位不是“一个写死流程的业务 agent”，而是一个表格 agent substrate：

- 底层编排负责把 agent 跑稳：session、workspace、tool loading、skill loading、memory loading、trace、usage、eval harness。
- 通用表格层负责跨领域能力：inspect、catalog、schema cache、retrieve、extract、rank、filter、time series、validate。
- 上下文与存储层负责承接经验：skill、domain knowledge、working/session/long-term memory、RAG、历史 trace 和当前 artifacts。
- domain pack 负责业务语义和领域挂载：行业术语、指标别名、表族经验、cohort、排序口径、sparse fallback、客户知识库、领域记忆和必要的专属工具。
- 基模负责在上下文里选择路径：多表 workspace 场景可以先召回，单表上传场景可以跳过召回直接 inspect；工具多不代表每轮都必须使用。

理想分层架构：

```text
TableClaw
├── Agent Core / Runtime
│   - 对话循环、工具调用协议、session、workspace、权限、trace、usage、harness
│   - 不绑定表格，也不绑定具体行业
│
├── Context / Storage Layer
│   - Skill：任务策略和操作流程
│   - Domain Knowledge：领域/客户稳定知识
│   - Memory：working memory / session memory / long-term memory
│   - Artifacts：上传文件、active file、schema cache、catalog、历史工具结果
│
├── Generic Table Tools
│   - retrieve / inspect / catalog / schema cache
│   - extract_matrix / rank / filter / time_series / validate
│   - 只处理跨领域通用的表格结构、抽取、计算和验证
│
├── Domain Pack
│   - domain skill
│   - domain knowledge
│   - domain memory / RAG
│   - domain-specific tools
│   - domain eval cases / badcase notes
│   - 负责某个行业/客户的业务口径、表族经验、执行策略和专属流程
│
└── Harness / Eval / Observability
    - trace、usage、评测结果、gold/badcase、错误归因、回归对照
    - 为人工判断、知识维护、工具迭代和长期闭环提供证据
```

单轮理想执行流程：

```text
User Query
  ↓
Agent Core / Runtime
  - 接收用户输入
  - 维护 session / workspace / trace
  - 准备本轮任务上下文
  ↓
Context Assembly / Routing
  - 判断任务类型：表格 / 文档 / 代码 / 通用问答
  - 判断是否命中某个 domain pack
  - 选择相关 skill
  - 读取相关 memory
  - 检索 domain knowledge / RAG
  - 加载当前 artifacts、active file、schema cache、历史 tool traces
  ↓
Strategy / Planning
  - 结合 query + skill + memory + domain knowledge + artifacts
  - 判断是否需要表格召回
  - 判断要使用哪些 generic tools / domain tools / core tools
  - 明确实体、指标、月份、sheet、口径、排序方向、输出形态
  ↓
Tool Execution
  - Core Agent Tools：file / shell / web / message / MCP
  - Generic Table Tools：retrieve / inspect / catalog / extract_matrix / rank / filter / time_series
  - Domain Tools：domain_knowledge / sparse_reconcile / 客户专属工具
  - 工具调用结果可继续回流到 planning，而不是只能线性执行一次
  ↓
Answer / Report / Evidence
  - 输出数值、表格、图表底表、结论或报告
  - 说明来源、口径、时间范围、单位和关键证据
  ↓
Post-turn Update
  - 写入 trace / usage / harness record
  - 更新 working memory / session memory
  - 标记可能进入 long-term memory、domain knowledge、skill 或 tool 的候选经验
```

核心原则：

> Skill 是调度说明书，domain knowledge 是业务知识库，memory 是动态上下文和历史经验，TableClaw tools 是执行器。

> Agent Core 不是直接进入某个固定 domain 流程；它先做 context assembly / routing，再结合 skill、memory、domain knowledge 和 artifacts 做 planning，然后选择合适工具执行，最后把 trace、结果和可复用经验回写到可观察体系。

## 能力边界原则

TableClaw 的能力不应该只有“通用 / 非通用”两类。更合理的边界是：

| 层级 | 示例 | 职责 |
| --- | --- | --- |
| Core Agent / Runtime | 对话循环、工具协议、session、workspace、权限、trace、harness | 提供 agent 通用运行能力，与表格和业务无关。 |
| Context / Storage Layer | skill、domain knowledge、memory、RAG、artifacts、tool traces | 提供本轮任务需要的流程经验、业务知识、动态上下文和历史证据。 |
| Generic Table Tools | retrieve、inspect、catalog、extract_matrix、rank、filter、time_series、validate | 解决跨领域表格结构、抽取、计算和验证问题。 |
| Domain Pack | domain skill、domain knowledge、domain memory/RAG、domain tools、domain eval cases | 组织某个行业/客户需要的业务口径、表族经验、专属流程和评测资产。 |
| Harness / Eval / Observability | trace、usage、gold/badcase、错误归因、回归对照 | 为人工判断、知识维护、工具迭代和长期闭环提供证据。 |

其中，`Context / Storage Layer` 可以继续细分为：

| 存储类型 | 示例 | 定位 |
| --- | --- | --- |
| Skill | table-read、table-clean、sichuan-finance skill | 保存“遇到某类任务应该怎么做”的流程经验和策略提醒。 |
| Domain Knowledge | 指标别名、表族映射、cohort、排序口径、fallback 规则 | 保存领域/客户层面的稳定业务知识。 |
| Memory | working memory、session memory、long-term memory | 保存当前任务状态、用户确认、团队偏好、历史交互和可复用上下文。 |
| Artifacts / Tool Traces | active file、schema cache、catalog、历史工具结果 | 保存当前任务和历史执行产生的可复用证据。 |

判断一个能力放在哪里：

- 如果特殊性来自业务口径，例如 `200亿省`、`预收账款排名默认看预收占收比`、`2025-12 sparse 表 reporting fallback`，放进 domain knowledge 或 domain tool。
- 如果特殊性来自普遍表格结构，例如多行表头、合并单元格、百分比编码、排名列识别、横向月份序列，沉淀成 generic table tool。
- 如果特殊性来自任务流程，例如“先查领域知识，再召回候选表，再 inspect，再抽取验证”，放进 skill。
- 如果特殊性来自当前用户、当前会话或历史确认，例如“这次 200亿省临时包含湖北”“这个用户默认要 Markdown 表格”“当前 active file 是某张上传表”，放进 memory。
- 如果只是某个 badcase 的临场操作经验，先放 skill / domain knowledge / memory，经人工分析和评测观察后再决定是否工具化或长期沉淀。

## Memory 的角色

Memory 也是一种存储层，和 skill、domain knowledge 同处上下文与经验沉淀体系中，但定位不同。

```text
Skill
  一类任务怎么做

Domain Knowledge
  某个领域/客户的稳定知识是什么

Memory
  这个用户、这次会话、这个团队或历史任务中实际发生过什么、确认过什么、偏好什么
```

Memory 不应该只是长文本聊天记录，也不应该和 domain knowledge 混在一起。它更像一个有作用域、有时间、有来源、有置信度的上下文存储：

- Working Memory：保存当前任务状态，例如 active file、active sheet、当前指标、已 inspect 的 schema、最近工具结果、中间结论。
- Session Memory：保存本会话中用户确认过的约束和改口径，例如“这次 200亿省包含湖北”“后续都看 2025-12”“这个表第 3 行是真表头”。
- Long-term Memory：保存跨会话的用户/团队偏好和历史确认，例如常用输出格式、组织内部简称、固定报表习惯、常问表族。
- Domain Knowledge：保存领域/客户层面的稳定知识，与某一次会话无关，例如当前默认 `200亿省` 名单、指标别名、排序口径。

简单区分：

> Domain Knowledge 是“这个领域通常如此”；Memory 是“这个用户/这次任务曾经如此”。

例如：

- `200亿省当前默认是广东、江苏、浙江、上海、四川、安徽、湖南`：domain knowledge。
- `用户这次明确说 200亿省临时加湖北`：session memory。
- `这个用户所在团队长期希望 200亿省报表包含湖北`：long-term memory，需要来源、时间和可撤销机制。

Memory 的维护也需要演进，但它的演进逻辑不是简单工具化，而是上下文提炼和治理：

```text
原始对话 / 工具 trace
-> 候选记忆
-> 判断作用域：本轮 / 本会话 / 用户 / 团队 / 客户 / 领域
-> 判断有效期：临时 / 会话内 / 一段时间 / 长期
-> 判断可信度：用户明确确认 / 工具验证 / 多次出现 / 模型推测
-> 写入 memory
-> 后续使用时可解释来源，并允许更新、覆盖或撤销
```

真正的表格工作流往往不是单问单答，而是连续分析、修正、追问、改口径、生成图表和报告。没有 memory，agent 每轮都会像从零开始；有了 memory，工具调用和领域知识才能在多轮任务里连续工作。

## 长期展望：可闭环的持续学习系统

TableClaw 的长期方向，是让真实任务、trace、harness、eval、memory、tool、skill 和 domain pack 逐步形成一个可控的反馈系统：系统用得越多，越理解具体行业、客户、团队和用户的表格习惯；case 跑得越多，越能发现高频错误和可复用模式；沉淀得越多，后续同类任务越稳定、越便宜、越可追溯。

理想中的演进路径是：

```text
真实任务 / badcase
-> trace、memory 与评测记录
-> 归因失败原因与可复用模式
-> 判断应该沉淀到哪一层
   - memory
   - domain knowledge / skill
   - generic table tool
   - core agent
   - eval 标注或 gold 修正
-> 小样本验证
-> 更大范围评测
-> 再决定是否进入主线
```

这个方向不是简单的“让模型自己改自己”。越靠近用户和业务的经验，越适合快速沉淀；越靠近底层的机制，越需要稳定、可测试、可审计。

- Memory 可以持续承接当前任务状态、用户确认、团队偏好和历史交互，让系统越来越懂具体用户和组织。
- Domain knowledge / skill 可以承接高频业务口径、流程经验、客户知识和 badcase 经验，让系统越来越懂某个领域。
- Generic Table Tools 可以沉淀跨 case、跨领域稳定复用的表格能力，让系统越来越擅长处理复杂表格。
- Core Agent 只吸收被充分验证的底层机制改进，例如工具协议、memory/session、workspace、trace、harness 等。
- Eval / harness 提供回归、对照和证据，让每次沉淀都能被验证，而不是只凭单个 case 的直觉。

因此，TableClaw 最终希望做到的不是一次性写死所有表格规则，而是形成一套“可观察、可验证、可记忆、可沉淀、可回归”的持续学习机制：底层稳定，工具增强，记忆变准，领域知识增厚，整体系统越用越好用。

## 单表与多表工作流

`tableclaw_retrieve_tables` 是多表 workspace 场景下的能力，而不是 TableClaw 的强制入口。

- 多表/历史文件池：用户只问业务问题时，先召回候选表，再 inspect 和抽取。
- 单表上传：如果上下文只有一个 active table，或用户明确给出文件路径，可以直接 inspect，不需要召回。
- 已知 sheet/range：直接走 locate/extract/rank/filter/time_series。
- 业务语义不明确：先查 domain knowledge / memory，再把明确的实体、指标、月份、表族提示交给通用工具执行。

因此，To C 单表场景不会否定召回工具的价值；它只是让召回从主路径变成可选 fallback。TableClaw 提供能力集合，具体路径由 skill、domain context、memory 和基模共同决定。

## 当前领域包：四川财资

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

- skill 负责提示：这是四川财资问题，先调用 `tableclaw_domain_knowledge`，并结合当前 session memory 中的用户临时约束。
- domain knowledge 负责返回：`200亿省 = 广东、江苏、浙江、上海、四川、安徽、湖南`、基础应收总额优先找通报应收总额表的基础业务区、占收比/欠费类指标的排序口径。
- memory 负责保留：当前 active file、用户本轮指定的月份/实体/临时 cohort、已经确认过的口径和多轮追问上下文。
- generic tools 负责执行：按实体、指标、月份和候选表抽出矩阵或排名，并返回可追溯的底层数据。

未来接入其他领域时，新增一个类似的 `domain_packs/<domain>/`，并按需挂载该领域的 skill、domain knowledge、memory/RAG、评测样本和专属工具，而不是改 agent core 主流程或把业务规则塞进通用工具。

## 快速入口

| 文档 | 用途 |
| --- | --- |
| [文档总览](docs/README.md) | 项目文档入口，包含架构、功能开发、实验评测和项目管理索引。 |
| [Domain Knowledge Migration](docs/功能开发/domain-knowledge-migration.md) | 说明领域包、skill、domain knowledge 与通用工具的边界。 |
| [Gold Cases Benchmark](docs/实验评测/gold-cases/README.md) | 40 条人工 gold case 的 benchmark 入口和历史 run。 |
| [Run History](docs/实验评测/gold-cases/runs/README.md) | 已归档的 40-case benchmark 与专项 case 对比报告。 |
| [Latest Eval: v4rerun Five-Way Eval](docs/实验评测/gold-cases/runs/2026-06-16-v4rerun-fiveway-eval.md) | 当前最新主线评测归档：badcase122 两轮与 query100 三个随机 split。 |
| [开发日志](docs/项目管理/development-log.md) | 按时间记录关键决策、实现和评测结果。 |

## 常用命令

```bash
./start.sh
./eval_gold_parallel.sh --concurrency 4
./eval_gold_parallel.sh --task-file eval_test/test_dataset/bad_cases.jsonl --concurrency 10
```

## 文档维护

- 根 `README.md` 只放项目定位、架构分层、当前状态和最重要入口。
- 详细架构、工具、skill、catalog、schema cache 等设计放在 `docs/功能开发/` 和 `docs/架构/`。
- 正式评测归档放在 `docs/实验评测/gold-cases/runs/`。
- 临时评测 subset、screen 日志和滚动结果不进入主线文档，除非整理成正式报告。
