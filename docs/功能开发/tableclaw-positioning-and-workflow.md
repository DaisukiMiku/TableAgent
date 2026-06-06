# TableClaw 定位与 Workflow 设计

> 最后更新：2026-06-06

## 目标定位

TableClaw 是基于 Nanobot 搭建的 TableAgent workflow 原型，目标不是只做“表格问答”，而是覆盖表格上下游任务：

- table read：读取结构、sheet、表头、合并单元格、指标列。
- table clean：清洗空行、合计行、缺失值、类型问题。
- formula debug：定位公式、引用、错误值和不一致公式。
- chart：生成或建议图表、dashboard、chart-ready summary。
- report：把计算结果转成管理报告和行动建议。
- validate：给出可追溯证据、校验口径、结果复核。

最终希望做到：小模型、低消耗、快推理、结果可验证。

## 产品调研：别人现在能做什么

| 类型 | 代表 | 已有能力 | 观察到的边界 |
| --- | --- | --- | --- |
| Office 内置插件 | Microsoft Copilot in Excel | 自然语言分析数据、生成洞察、可视化、辅助公式和数据整理。 | 依赖 Excel 环境和表格规范；复杂 workflow 的验证链路仍需用户检查。 |
| Office 内置插件 | Gemini in Google Sheets | 在 Sheets 内生成表格、汇总、创建 pivot table，并围绕 Drive/Gmail 上下文协作。 | 更偏协作入口；复杂本地 Excel、多文件、可回滚执行链路不是重点。 |
| Office 内置插件 | WPS AI Spreadsheet | 自然语言生成公式、处理数据、兼容 Office 格式，强调低门槛办公场景。 | 更偏产品集成和易用性，技术可追溯、可插拔 harness 不透明。 |
| 通用 Agent | Claude Code / Codex / Kimi / Nanobot | 能通过文件读写和代码工具处理 xlsx/csv，适合复杂自动化。 | 通用能力强，但 table skill、context、验证、日志需要项目化沉淀。 |
| 论文系统 / Benchmark | SpreadsheetBench | 用真实业务 spreadsheet workflow 评估模型，覆盖复杂多 sheet、公式、调试、可视化等任务。 | 更偏评测基准；TableClaw 可吸收其任务分类和评价指标。 |

参考来源：

- Microsoft Copilot in Excel: https://support.microsoft.com/en-gb/office/get-insights-about-numerical-data-with-copilot-in-excel-52d97339-86c0-431c-b46c-e7b07b2898dd
- Microsoft Learn, Analyze and visualize data using Copilot: https://learn.microsoft.com/en-us/training/modules/analyze-visualize-data-copilot/
- Gemini in Google Sheets: https://support.google.com/docs/answer/14356410
- WPS AI Spreadsheet guide: https://www.wps.com/academy/wps-ai-spreadsheet-practical-guide-for-smarter-data-work-quick-tutorials-1898358/
- SpreadsheetBench: https://spreadsheetbench.github.io/
- SpreadsheetBench paper: https://proceedings.neurips.cc/paper_files/paper/2024/hash/ac840df270ac537dd74530a15c332684-Abstract-Datasets_and_Benchmarks_Track.html

## 能力边界分析

当前产品和通用 agent 的共同短板：

- 表格理解：大模型能猜结构，但对多级表头、合并单元格、长宽表、total/subtotal 行的口径不稳定。
- 表格操作：公式生成、清洗、格式调整可以做，但缺少统一验证和回滚。
- 结果生成：图表和报告能生成，但证据链、引用来源、可复算性常常不足。
- Workflow：多步任务拆解依赖模型自觉，缺少可观测的 skill routing 与阶段日志。
- Context：大表直接塞上下文 token 消耗高，缺少 schema cache、局部检索、结果缓存。

TableClaw 的切入点：

- 不只回答最终值，而是保留 `read -> clean -> compute -> validate -> report` 的轨迹。
- 不只靠一个大 skill，而是沉淀多个轻量、阶段化 table skills。
- 不只看准确率，还看 token、耗时、工具步数、是否可验证、是否可回滚。

## TableAgent Workflow v0

当前 v0 编排仍基于 Nanobot 原生机制：

1. 用户提出单轮或多轮表格任务。
2. Nanobot 把 builtin skill 列表注入上下文。
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

## 单轮与多轮场景

单轮：

- 用户一次性给出完整任务。
- 模型应在同一轮中按阶段读取多个 skill。
- 评测重点：skill sequence、工具步数、正确率、token。

多轮：

- 用户先问结构，再问清洗，再问报告或图表。
- 每轮 query 都应能重新选择当前最合适的 skill。
- memory 记录的是稳定事实和用户偏好，不记录完整大表正文。
- session 记录当前对话上下文；workspace 存放可复用摘要、结果和产物。

## Memory / Context / RAG 设计

v0 先设计，不急着重写 Nanobot 核心。

| 层 | 内容 | 目标 |
| --- | --- | --- |
| Session Context | 当前多轮对话、最近工具结果、用户当前问题 | 保持自然连续对话 |
| Table Schema Memory | 表路径、sheet、行列、表头映射、关键列、合计行 | 避免每轮重复读全表 |
| Result Cache | 最近一次计算的中间结果、排序/筛选结果、校验摘要 | 复用多轮追问 |
| RAG Index | 大表的 sheet/chunk/schema 向量或关键词索引 | 大表局部检索，减少 token |
| User Memory | 用户偏好的输出格式、精度、业务口径 | 长期个性化 |

近期最小实现建议：

1. 先不做向量库，写 `workspace/table_cache/` JSON 缓存 schema。
2. 缓存 key 使用文件路径 + mtime + size + sheet。
3. `table-read` 阶段生成 schema summary。
4. 后续 query 先查 schema cache，再决定是否重新 inspect。
5. eval 增加 cached/non-cached 对照，观察 token 和耗时差异。

## 可插拔 Harness 设计

目标：把“模型会不会做”变成“系统能不能稳定执行和验证”。

Harness v0 已有：

- 文件路径拼接：`render_prompt` 自动把 `{table_path}` 变成 eval dataset 绝对路径。
- skill-on/off：两份 nanobot config 控制 skill 是否可见。
- 轨迹日志：tool timeline、skill read、first skill step、tools used。
- 结果评分：required facts + numeric checks。
- token usage：prompt/completion/total/cached。

下一步 harness 扩展：

- 文件输出检查：验证生成的 xlsx/csv/report 是否存在。
- workbook 检查：cell 值、公式、sheet、图表、格式。
- 回滚机制：编辑类任务在副本上执行，失败不污染原文件。
- task schema 扩展：支持 read/clean/formula/chart/report/validate 六类任务。
- 多模型横评：Claude / Copilot / WPS / Gemini / 通用 Agent / TableClaw。

## Eval 路线

当前已完成：

- 12 个任务。
- 1 张真实工业表格。
- skill-on/off 对照。
- Codex `xlsx` skill + 6 个 TableClaw 轻量 workflow skills。

近期扩展目标：

- 20-50 个真实表格任务。
- 覆盖理解、清洗、公式、图表、报告、多步 workflow。
- 指标包括正确率、耗时、token、工具步数、是否可执行、是否可追溯、是否需要人工干预。

中期横评：

- Office 插件类：Copilot in Excel、WPS AI、Gemini in Sheets。
- 通用 Agent：Claude Code、Codex、Kimi、GLM、Nanobot。
- 论文系统 / benchmark：SpreadsheetBench、SheetMind、TableTalk 等。

## 当前完成度

已完成：

- 基于 Nanobot 跑通 TableClaw 本地 workflow。
- `start.sh` / `eval.sh` 一键入口。
- DashScope `deepseek-v4-pro` 配置。
- 项目内 workspace 与 usage log。
- builtin Codex `xlsx` skill。
- 新增 6 个轻量 TableClaw table skills。
- 12-task eval dataset，其中 2 个 workflow routing task。
- harness 记录 skill sequence、工具轨迹、token、latency、自动评分。

未完成：

- Table schema cache / RAG。
- 文件编辑、公式调试、图表生成、报告生成的真实产物评测。
- 可回滚编辑 harness。
- 多模型 / 多产品横评。
- TableClaw native xlsx skill v0 替代 Codex 大 skill。
