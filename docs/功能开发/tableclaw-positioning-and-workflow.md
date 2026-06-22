# TableClaw 定位、产品调研与 Workflow 设计

> 最后更新：2026-06-22

## 0. 目标定位

TableClaw 是 To C / 通用 Table Agent 能力栈。它的目标不是只做“表格问答”，也不是把某个工业财资业务写成固定流程，而是面向完整表格上下游任务，形成可插拔、可追踪、可评测的表格 agent substrate：

- table read：读取 workbook、sheet、range、表头、合并单元格、指标列、公式上下文。
- table clean：清洗空行、合计行、缺失值、类型问题、重复记录。
- formula debug：定位公式、引用、错误值、依赖链和不一致公式。
- chart：生成或建议图表、dashboard、chart-ready summary。
- report：把计算结果转成管理报告、风险列表和行动建议。
- validate：给出可追溯证据、校验口径、结果复核和可回滚记录。

最终目标：

> 面向表格上下游任务，实现小模型、低消耗、快推理、结果可验证。

当前四川财资工业表格只是第一个 domain pack 验证场景。长期形态应支持单表上传、多表 workspace、行业/客户 domain pack、memory/RAG、表格读算工具、workbook artifact 生成和 harness/eval 共同工作。

当前项目进入第二阶段：在保留四川财资 domain pack 主线的同时，把能力迁移到更通用的表格上下游任务。这里的“通用”不只是问答，还包括：

- 清洗和重构复杂 workbook。
- 生成可交付 `.xlsx`、图表底表、报告、PPT 上游数据。
- 构建财务/经营模型、同行对标、预测模型。
- 在没有固定业务知识时，依靠通用 spreadsheet skill + generic tools + 工具执行轨迹完成任务。

因此现阶段有两种互补路线：

```text
高频 QA / 评测主线
  domain skill + domain knowledge + generic table tools
  目标：小模型、低成本、快推理、可验证

通用 workbook / artifact 主线
  anthropic-xlsx 大 skill + Python/openpyxl/LibreOffice + generic tools
  目标：复杂清洗、公式、格式、建模、可交付 Excel artifact
```

---

## 1. 产品调研：别人现在能做什么

### 1.1 集成到既有表格 APP 内的插件类 Table Agent

这一类产品不重新构建独立表格系统，而是把 LLM/Agent 能力嵌入用户已经使用的办公软件中，例如 Excel、WPS 表格、Google Sheets、飞书表格、钉钉表格、腾讯文档、Airtable、Rows 等。

用户仍然在原有表格环境中完成数据处理、公式编辑、报表分析和协作流程，AI 则作为侧边栏、插件、AI 按钮或智能助手参与执行。

典型流程：

```text
用户自然语言指令
-> 读取当前 workbook / sheet / range / formula / format 上下文
-> LLM 进行任务理解和操作规划
-> 自动选择 Skill / Tool / Connector
-> 调用表格原生 API 执行修改、分析、生成或格式化
-> 返回结果、记录日志、支持用户检查和回滚
```

这类产品本质上不是普通“表格问答工具”，而是嵌入表格工作流的 Table Agent。

#### Claude for Excel

链接：https://support.claude.com/en/articles/12650343-use-claude-for-excel

产品形态：

- Microsoft 365 Excel Add-in，即 Excel 插件。
- 把 Claude 模型嵌入 Excel 工作流。
- 面向财务分析、建模、多 sheet workbook、公式依赖、模板填充等专业场景。

Agent 属性：

- 能询问 workbook 并返回 cell-level citations。
- 能修改 assumptions，同时尽量保留公式依赖。
- 能 debug errors，识别 root causes。
- 能 build new models / fill templates。
- 能在 multi-tab workbook 中导航。
- 能使用 connectors 把外部上下文带入 spreadsheet。
- 支持 session logging：可创建 `Claude Log` sheet 记录每轮操作。
- Claude for Microsoft 365 还强调不同 Office 应用之间共享 conversation state。

实现方式推测：

- 模型层：Claude LLM。
- 接口层：Office Add-in + JavaScript / Office.js。
- 可选 LLM Gateway：Amazon Bedrock、Google Vertex AI、Microsoft Azure 等。
- 技能调度：根据用户意图自动选择启用的 Skills 和 Connectors。
- 操作执行：通过 Excel 原生 API 读取/回写 cell、formula、format、chart、sheet 等。
- 日志与 context：本地 chat history / Claude Log / 长上下文压缩。
- 安全：用户确认关键操作，限制高风险宏/VBA，保留操作可审计性。

Claude for Excel 与普通表格助手的区别在于：它不是只回答“这个值是多少”，而是进入 Excel 的操作环境，形成 context gathering、skill routing、tool execution、change tracking、session logging、安全确认等完整 workflow。它是 TableClaw 的重要竞品和参考实现。

#### Microsoft Copilot in Excel

链接：

- https://support.microsoft.com/en-us/office/visualize-your-data-with-copilot-in-excel-05302e3f-de42-4475-b235-be9cb3d4e936
- https://support.microsoft.com/en-gb/office/get-insights-about-numerical-data-with-copilot-in-excel-52d97339-86c0-431c-b46c-e7b07b2898dd

能力概览：

- 在 Excel 中解释、分析、可视化数据。
- 生成公式列。
- 使用 Agent Mode 对 workbook data 进行 highlight、sort、filter。
- 使用 Copilot Chat 回答基础问题。
- 使用 Analyst 做更深的数据推理分析。

边界观察：

- 深度依赖 Excel 环境和 Microsoft 365 生态。
- 强在原生操作、交互体验和 Office 集成。
- 对复杂 workflow 的可验证性、可回滚性和评测透明度仍然不完全开放。

#### Google Gemini in Sheets

链接：https://support.google.com/docs/answer/14356410

能力概览：

- 在 Google Sheets 中创建表格、生成内容、辅助整理数据。
- 支持创建 pivot table。
- 与 Google Workspace 的 Drive、Gmail、Docs 等上下文协作。

边界观察：

- 强在协作环境和云端文档上下文。
- 更偏在线表格和 Workspace 工作流，不是本地 xlsx 文件的深度编辑 harness。
- 对复杂公式调试、文件级 diff、回滚和可验证报告的开放程度有限。

#### WPS AI Spreadsheet

链接：https://www.wps.com/academy/wps-ai-spreadsheet-practical-guide-for-smarter-data-work-quick-tutorials-1898358/

能力概览：

- 面向普通办公用户的 AI spreadsheet 助手。
- 覆盖数据分析、公式生成、表格处理、办公文档联动。
- 优势是国内办公生态、低门槛、Office 文件兼容。

边界观察：

- 产品可用性强，但内部 workflow、日志、skill、验证机制不透明。
- 更偏“嵌入办公产品的 AI 功能点”，TableClaw 更关注可插拔 harness、可追踪执行和低 token 成本。

#### 协作文档 / 企业办公集成类

代表：

- 飞书 AI Companion / Aily。
- 钉钉 AI 表格。
- 腾讯文档 Skill / MCP。

特点：

- 表格不再只是单文件，而是企业协作、知识管理和业务流程的一部分。
- 强调跨文档、跨系统、跨流程的 Agent 能力。
- 更接近“表格作为业务流程入口”。

#### 在线数据库 / AI Spreadsheet 类

代表：

- Airtable AI。
- Rows AI。

特点：

- 把 spreadsheet、database、automation、外部数据源和业务应用构建结合起来。
- 更强调“表格作为业务数据和 workflow 入口”。

#### 插件类 Table Agent 共性

| 共性 | 说明 |
| --- | --- |
| 嵌入式产品形态 | AI 嵌入 Excel/WPS/Sheets 等用户已有工作环境，而不是独立网页问答。 |
| 表格上下文读取 | 系统需要读取 workbook、sheet、range、cell、formula、format 等结构化信息。 |
| 自然语言到表格操作 | 用户用自然语言描述需求，系统转成公式生成、清洗、筛选、图表、调试等操作。 |
| LLM + 原生 API 执行 | LLM 负责理解/规划；真实修改依赖 Office.js、Excel API、Sheets API、WPS API。 |
| Workflow / Skill 调度 | 成熟产品开始出现任务拆解、skill、connector、MCP、日志、权限控制。 |
| 长上下文和日志机制 | 多 sheet、多轮修改和复杂依赖要求 context compression、history、operation log、cell citation。 |
| 安全和权限控制 | 表格常含敏感数据，也可能存在 prompt injection，需要权限、确认、审计、回滚。 |

### 1.2 通用原生 Agent 系统中的 Table 能力

第二类产品本身不是专门为表格设计的，而是通用原生 Agent 系统，例如 Claude Code、OpenAI Codex、Kimi Code / Kimi Claw、GLM Coding、Cline、Roo Code、Kilo Code、OpenClaw、Nanobot 等。

调研重点不是完整评估它们的通用 Agent 能力，而是观察哪些机制可以迁移到 TableAgent：

- 是否支持文件读写和代码执行，能否处理真实 CSV / XLSX / 多 sheet 文件。
- 是否支持 Skill / MCP / Tool 机制，能否沉淀和复用表格相关能力。
- 是否支持长上下文压缩、局部读取、文件摘要，能否降低长表格 token 成本。
- 是否支持多步 workflow 编排，能否完成 `读取 -> 分析 -> 修改 -> 验证 -> 输出` 闭环。
- 是否支持 sandbox、权限确认、diff、日志和回滚，能否保证表格修改过程可控可信。

通用 Agent 的价值：

- 文件系统能力：读写 xlsx/csv/json/md/report 等文件。
- 代码执行能力：通过 Python、pandas、openpyxl、LibreOffice、Node 等处理表格。
- 工具调用能力：把高频逻辑沉淀为 tool，而不是每次让模型临时写脚本。
- Skill 复用能力：把 read/clean/formula/chart/report/validate 等流程沉淀成可检索知识。
- 日志与回滚能力：记录工具轨迹、修改 diff、输出 artifact、支持失败恢复。

对 TableClaw 的启发：

> 采用“Core Agent / Runtime + Context / Storage + Generic Table Tools + Domain Pack + Harness”的路线。

底层运行时负责通用 agent 编排、session、workspace、tool/skill loading、trace 和 harness；上层沉淀 `table-read`、`table-clean`、`table-formula-debug`、`table-chart`、`table-report`、`table-validate` 等表格流程能力；通过 memory/context/RAG 降低重复探索和 token 消耗，并通过 eval harness 记录正确率、耗时、token、可追溯性和人工干预情况。

### 1.3 专门的 Table Agent / Spreadsheet Agent 论文系统

代表方向：

- SpreadsheetBench。
- SheetAgent / SheetMind / TableTalk 等 spreadsheet reasoning/manipulation 系统。
- 后续可补 BlueFin 等金融 spreadsheet benchmark。

SpreadsheetBench 是当前很值得参考的 benchmark：它强调真实业务 spreadsheet workflow，包含大量真实场景任务、不同格式的 tabular data，以及接近 online judge 的评估方式。其公开介绍中包含 912 个真实场景问题，论文强调任务来自真实 spreadsheet 用户 workflow。

论文/benchmark 对 TableClaw 的启发：

- Eval 不能只做简单 QA。
- 需要覆盖 cell-level manipulation 和 sheet-level manipulation。
- 需要把公式、清洗、筛选、布局编辑、图表、报告纳入任务集。
- 需要记录可执行性和可验证性，而不只是最终自然语言答案。

---

## 2. Eval 测试：构建统一测试集做横向对比

### 2.1 目标

构建统一测试集，用同一批任务横向比较：

- Claude / Claude for Excel。
- Copilot in Excel。
- WPS AI。
- Gemini in Sheets。
- 通用 Agent：Claude Code、Codex、Kimi、GLM、Nanobot。
- TableClaw。

记录：

- 正确率。
- 耗时。
- token 消耗。
- 是否可执行。
- 是否可追溯。
- 是否需要人工干预。
- 是否支持回滚或可审计日志。

### 2.2 任务规模

近期目标：20-50 个真实表格任务。

中期目标：80-150 个任务。

任务覆盖：

| 类别 | 示例 |
| --- | --- |
| 理解 | 单表、多 sheet、长表格、结构化信息理解、多级表头识别 |
| 清洗 | 空行、合计行、缺失值、类型转换、重复项、宽表/长表转换 |
| 公式 | 公式生成、公式调试、引用修复、一致性检查、重算验证 |
| 图表 | 图表推荐、chart-ready summary、dashboard、趋势/排名图 |
| 报告 | 管理摘要、风险列表、KPI 解读、模板填充 |
| 多步 workflow | 读取 -> 清洗 -> 计算 -> 验证 -> 报告/写回 |

### 2.3 当前 TableClaw Eval 状态

已完成：

- 四川财资 domain pack 主线：
  - gold40 / badcase122 / query100 系列评测。
  - `eval_gold_parallel.sh` 记录 tool timeline、token、latency、judge、gold issue flags。
  - 2026-06-16 V3 Final Eight-Way Eval：866 raw cases；排除 53 个明显 gold/task issue 后，813 scored cases official adjusted ACC 95.20%。
- 通用 workbook/artifact smoke：
  - `anthropic-xlsx` builtin skill 已接入。
  - Hermes 长表清洗、奢侈品同行对标、2026-2030 财务预测模型任务已跑通。
  - 报告位于 `workspace/reports/hermes_anthropic_test/hermes_anthropic_xlsx_skill_eval.md`。

历史 workflow 任务：

- `tc_workflow_001`：读表结构 + 数据质量检查 + 判断是否适合跨期分析。
- `tc_workflow_002`：读表、清洗、两期低于阈值筛选、排序、管理建议、校验说明。

当前观察：

- 业务 QA 任务中，domain pack + deterministic tools 的收益已经明确；继续提升应聚焦错误归因、召回和 reconciliation，而不是把业务知识写进通用工具。
- 通用 artifact 任务中，大 spreadsheet skill 能提升 workbook 交付质量，但 token / latency / 脚本执行成本更高，且需要 artifact 级评测。
- 轻量 TableClaw skills 与 `anthropic-xlsx` 大 skill 不应被看成二选一：前者适合高频、低成本、可评测 QA；后者适合复杂 workbook 产物生成。

---

## 3. 能力边界分析：这些产品在哪些任务上强/弱

| 能力 | 插件类 Table Agent | 通用 Agent 系统 | TableClaw 当前 | TableClaw 目标 |
| --- | --- | --- | --- | --- |
| 表格理解 | 强在当前 APP 上下文、原生 range/cell/formula | 能处理文件，但常靠临时脚本 | 已支持 xlsx 结构读取和多级表头任务 | schema cache + 局部检索 + 多 sheet |
| 表格操作 | 强在原生 API 写回、格式、图表 | 能改文件，但验证和回滚需自建 | 当前主要读/分析，编辑类未系统评测 | 可回滚副本编辑 + diff + validate |
| 公式能力 | Excel/Sheets 插件有原生公式上下文 | 可用 openpyxl/LibreOffice 检查 | 已有 `table-formula-debug` skill，但未跑真实公式任务 | 公式依赖图 + 重算 + 错误扫描 |
| 图表/报告 | 插件体验好，写回方便 | 可生成文件/图表，但质量需验证 | 已有 `table-chart` / `table-report` skill | chart-ready table + dashboard harness |
| Workflow | 插件逐渐具备 Agent Mode/Skill/Connector | 通用 Agent 最强，但不表格专精 | 已记录 skill sequence 和 tool timeline | 显式 table workflow router |
| Context | 插件有 workbook/session 上下文 | 通用 Agent 依赖上下文压缩和文件读取 | 有 session/memory/usage，未做表格 cache | schema memory + RAG + result cache |
| 验证/日志 | Claude Log / Office 操作历史等逐渐出现 | 工具轨迹强，但表格验证要补 | 有 eval JSON、tool timeline、usage | cell citation + diff + rollback |

核心判断：

- 插件类产品强在“嵌入真实表格环境”，弱在内部机制不透明、评测不可控。
- 通用 Agent 强在“开放工具和可编排”，弱在缺少表格专用 workflow 和低 token context。
- TableClaw 的机会在于把两者结合：开放可插拔 harness + 表格专用 skill/tool/context/验证。

---

## 4. TableClaw 方案设计：我们怎么做得更好

### 4.1 第一阶段：文件上传式 Workflow Agent

先不直接做 Excel/WPS 插件，而是做本地/服务端文件上传式 workflow agent：

```text
上传 xlsx/csv
-> 解析 workbook
-> 构建 sheet / range / formula / header 上下文
-> 用户输入任务
-> Nanobot 选择相关 table skills
-> 调用 Python / openpyxl / pandas / LibreOffice 等工具执行
-> 输出答案或修改后的 xlsx
-> 输出操作日志、cell citation、验证报告、可回滚副本
```

这一阶段的优势：

- 可控：不依赖 Office 插件生态。
- 易评测：所有输入、输出、工具轨迹和 token 都在 harness 中。
- 易沉淀：skill/tool/context 可以快速迭代。
- 可迁移：未来可以接 Excel/WPS/飞书/钉钉插件。

### 4.2 第二阶段：插件化 / App 嵌入式 Table Agent

后续再扩展为：

```text
Excel / WPS / 飞书 / 钉钉 插件
-> 读取当前表格上下文
-> 调用 TableClaw workflow
-> 返回可执行操作计划
-> 写回原表格环境
-> 记录日志和 diff
```

插件化时需要补：

- Office.js / Excel API / Google Sheets API / WPS API 适配层。
- 用户确认与权限控制。
- 修改前后 diff。
- 回滚和审计日志。
- 外部 connector / RAG。

### 4.3 TableAgent Workflow v0

当前 v0 编排仍基于现有本地 runtime 机制：

1. 用户提出单轮或多轮表格任务。
2. Runtime 把 builtin / workspace skill 列表注入上下文。
3. 模型按任务阶段读取合适的 `SKILL.md`。
4. 模型调用文件读取、Python/openpyxl、shell 等工具执行。
5. `eval_test/run_eval.py` 记录 skill 读取顺序、工具轨迹、token usage、latency、自动评分。
6. 运行时 usage 追加到 `workspace/usage/usage.jsonl`。

新增轻量 skill 池：

| Skill | 阶段 | 触发任务 |
| --- | --- | --- |
| `table-read` | structure | sheet、行列数、表头、合并单元格、指标列定位 |
| `table-clean` | cleaning | 空行、合计行、缺失值、类型转换、重复项 |
| `table-validate` | evidence | 口径校验、行列计数、公式/数值复核、证据说明 |
| `table-report` | reporting | 管理摘要、风险列表、建议、结论解释 |
| `table-formula-debug` | formula | 公式读取、错误值、引用修复、一致性检查 |
| `table-chart` | visualization | 图表选择、chart-ready table、dashboard 输出 |
| `xlsx` | broad spreadsheet | Codex 原文 spreadsheet skill，作为当前宽能力兜底 |
| `anthropic-xlsx` | workbook artifact | Anthropic-style 大 spreadsheet skill，适合清洗、公式、建模、格式化和可交付 `.xlsx` |

#### 通用 workbook/artifact 流程

Hermes smoke 暂时采用以下路径：

```text
用户给复杂 workbook 任务
-> 使用 anthropic-xlsx-only 配置隐藏轻量 table skills
-> 模型读取 anthropic-xlsx/SKILL.md
-> tableclaw_inspect 识别 workbook 结构
-> Python/openpyxl/pandas/LibreOffice 执行清洗、重构、建模
-> 输出多个 xlsx artifact
-> 写入运行报告和工具轨迹
```

这条路径更接近 Claude for Excel / 财务模型类工作流，但目前还不是正式 benchmark：

- 需要补 artifact 评测：sheet、公式、格式、图表、重算结果、文件可打开性。
- 需要补数据来源评测：外部同行数据不能由模型“估算后当真”。
- 需要补渲染/截图检查：复杂 workbook 和图表不能只看文件存在。
- 需要评估是否禁用领域 workspace skill，避免通用任务被四川财资 skill 摘要污染。

### 4.4 单轮与多轮场景

单轮：

- 用户一次性给出完整任务。
- 模型应在同一轮中按阶段读取多个 skill。
- 评测重点：skill sequence、工具步数、正确率、token。

多轮：

- 用户先问结构，再问清洗，再问报告或图表。
- 每轮 query 都应能重新选择当前最合适的 skill。
- memory 记录稳定事实和用户偏好，不记录完整大表正文。
- session 记录当前对话上下文；workspace 存放可复用摘要、结果和产物。

---

## 5. Memory / Context / RAG 设计

v0 先设计和验证，不急着重写底层 runtime。

| 层 | 内容 | 目标 |
| --- | --- | --- |
| Session Context | 当前多轮对话、最近工具结果、用户当前问题 | 保持自然连续对话 |
| Table Schema Memory | 表路径、sheet、行列、表头映射、关键列、合计行 | 避免每轮重复读全表 |
| Result Cache | 最近一次计算的中间结果、排序/筛选结果、校验摘要 | 复用多轮追问 |
| RAG Index | 大表的 sheet/chunk/schema 向量或关键词索引 | 大表局部检索，减少 token |
| User Memory | 用户偏好的输出格式、精度、业务口径 | 长期个性化 |
| Operation Log | 每次工具调用、修改、验证和输出 artifact | 可追溯、可回滚 |

近期最小实现建议：

1. 先不做向量库，写 `workspace/table_cache/` JSON 缓存 schema。
2. 缓存 key 使用文件路径 + mtime + size + sheet。
3. `table-read` 阶段生成 schema summary。
4. 后续 query 先查 schema cache，再决定是否重新 inspect。
5. eval 增加 cached/non-cached 对照，观察 token 和耗时差异。

中期扩展：

- sheet summary：每个 sheet 的字段、数据范围、公式区域、异常区域。
- range retrieval：按列名、期间、指标、用户问题检索局部区域。
- formula dependency graph：公式引用链、错误传播路径。
- operation log：操作前后 diff、修改位置、验证结果。
- rollback snapshot：编辑任务在副本上执行，用户确认后再写回。

---

## 6. 可插拔 Harness 设计

目标：把“模型会不会做”变成“系统能不能稳定执行和验证”。

Harness v0 已有：

- 文件路径拼接：`render_prompt` 自动把 `{table_path}` 变成 eval dataset 绝对路径。
- skill-on/off：两份 nanobot config 控制 skill 是否可见。
- 轨迹日志：tool timeline、skill read、skill sequence、first skill step、tools used。
- 结果评分：required facts + numeric checks。
- token usage：prompt/completion/total/cached。
- 完整 answer 保存：便于后续重评分，不必重复烧模型。

下一步 harness 扩展：

- 文件输出检查：验证生成的 xlsx/csv/report 是否存在。
- workbook 检查：cell 值、公式、sheet、图表、格式。
- 回滚机制：编辑类任务在副本上执行，失败不污染原文件。
- task schema 扩展：支持 read/clean/formula/chart/report/validate 六类任务。
- 多模型横评：Claude / Copilot / WPS / Gemini / 通用 Agent / TableClaw。
- 人工干预标记：记录是否需要人工确认、修正或重跑。

---

## 7. Eval 路线

当前已完成：

- 四川财资主线：gold40、badcase122、query rewrite 100 系列，并支持 gold/task issue 排除。
- 通用工具观测：记录 retrieve / inspect / matrix / rank / filter / time_series / domain_knowledge 等工具轨迹、耗时和 token。
- skill 观测：记录 skill read、skill sequence、工具调用路径和最终答案。
- Hermes artifact smoke：`anthropic-xlsx-only` 模式下完成复杂 workbook 清洗、同行对标和预测模型输出。

近期扩展目标：

- 5-10 个非四川财资真实 workbook artifact 任务，覆盖清洗、公式、图表、报告、模型、PPT 上游数据。
- 为 artifact 任务建立结构化评测：文件存在、sheet/schema、关键值、公式错误、格式基本检查、渲染截图、数据来源说明。
- 保留 QA ACC 评测，但不要把 artifact 任务强行压成自然语言答案。
- 分开记录业务 domain pack 评测和通用 workbook/artifact 评测，避免混淆准确率口径。

中期横评：

- APP 插件类：Claude for Excel、Copilot in Excel、WPS AI、Gemini in Sheets。
- 通用 Agent：Claude Code、Codex、Kimi、GLM、Nanobot。
- 论文系统 / benchmark：SpreadsheetBench、SheetAgent、SheetMind、TableTalk 等。

---

## 8. 当前完成度

已完成：

- 跑通 TableClaw 本地 workflow。
- `start.sh` / `eval.sh` / `eval_gold_parallel.sh` 一键入口。
- DashScope `deepseek-v4-pro` 配置。
- 项目内 workspace、usage log、schema cache、table catalog。
- builtin Codex `xlsx` skill。
- builtin `anthropic-xlsx` skill。
- 6 个轻量 TableClaw table skills。
- 四川财资 domain pack + `tableclaw_domain_knowledge`。
- gold40 / badcase122 / query100 主线评测与 gold/task issue 排除口径。
- Hermes 通用 workbook/artifact smoke。
- harness 记录 skill sequence、工具轨迹、token、latency、自动评分。
- 初步产品调研与 TableClaw 方案设计文档。

未完成：

- 跨领域通用任务集：当前仍以四川财资和 Hermes 单例为主。
- 文件编辑、公式调试、图表生成、报告生成的系统化 artifact 评测。
- 可回滚编辑 harness。
- 多模型 / 多产品横评。
- TableClaw native table/workbook skill v0：吸收 Codex/Kimi/Anthropic 强项，但不直接依赖外部大 skill。

---

## 9. 参考来源

- Claude for Excel: https://support.claude.com/en/articles/12650343-use-claude-for-excel
- Claude for Microsoft 365 overview: https://claude.com/docs/office-agents
- Microsoft Copilot in Excel, visualize data: https://support.microsoft.com/en-us/office/visualize-your-data-with-copilot-in-excel-05302e3f-de42-4475-b235-be9cb3d4e936
- Microsoft Copilot in Excel, insights about numerical data: https://support.microsoft.com/en-gb/office/get-insights-about-numerical-data-with-copilot-in-excel-52d97339-86c0-431c-b46c-e7b07b2898dd
- Gemini in Google Sheets: https://support.google.com/docs/answer/14356410
- WPS AI Spreadsheet guide: https://www.wps.com/academy/wps-ai-spreadsheet-practical-guide-for-smarter-data-work-quick-tutorials-1898358/
- SpreadsheetBench project: https://spreadsheetbench.github.io/
- SpreadsheetBench paper: https://proceedings.neurips.cc/paper_files/paper/2024/hash/ac840df270ac537dd74530a15c332684-Abstract-Datasets_and_Benchmarks_Track.html
- SheetAgent paper: https://arxiv.org/abs/2403.03636
