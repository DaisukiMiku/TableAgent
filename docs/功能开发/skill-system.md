# TableClaw Skill 模块设计

> 最后更新：2026-06-22
>
> 用途：记录 nanobot skill 的加载、筛选、调用机制，以及 TableClaw 在“通用表格能力 + 可插拔领域包”路线下的 skill 边界。

## 当前结论

TableClaw 当前有三类 skill 同时存在，但职责不同：

```text
nanobot/nanobot/skills/        # 产品内置 / 通用能力
workspace/skills/              # 当前运行工作区覆盖层 / 用户或领域挂载
domain_packs/<domain>/skills/  # 可版本化领域包，启动时同步到 workspace
```

当前主线结论：

- 通用、产品级、随代码版本发布的能力放入 `nanobot/nanobot/skills/`，作为 builtin skill。
- 用户级、客户级、项目级业务规则放入 `workspace/skills/`，作为 workspace skill。
- 可复用领域包放入 `domain_packs/<domain>/`，启动或评测前同步到 workspace。
- `anthropic-xlsx` 已作为 builtin skill 接入，和 `table-read` / `table-clean` / `table-chart` / `xlsx` 平级，用于验证更通用的 workbook/artifact 任务。
- 四川财资业务知识仍放在 `domain_packs/sichuan-finance/`，不进入 `anthropic-xlsx`，也不写死到通用 tools。

## Skill 来源

nanobot 当前有两个 skill 来源。

### Builtin Skill

路径：

```text
nanobot/nanobot/skills/<skill-name>/SKILL.md
```

适合：

- 产品内置能力。
- 所有用户都应该拥有的通用能力。
- 需要随代码版本发布、测试和回滚的能力。

当前 nanobot 已有的 builtin skill 包括：

- `xlsx`：Codex-style spreadsheet skill，宽能力兜底。
- `anthropic-xlsx`：Anthropic-style 大 spreadsheet skill，强调 Excel artifact、公式、格式、清洗、建模和重算验证。
- `table-read` / `table-clean` / `table-validate` / `table-report` / `table-formula-debug` / `table-chart`：TableClaw 轻量流程 skill。
- `memory`、`summarize`、`weather`、`github`、`cron`、`tmux`、`skill-creator`、`image-generation` 等 nanobot 原生 skill。

### Workspace Skill

路径：

```text
workspace/skills/<skill-name>/SKILL.md
```

适合：

- 用户自定义能力。
- 客户私有业务规则。
- 项目级临时实验。
- 对 builtin skill 的本地覆盖。

当前 `workspace/skills/` 主要由 `start.sh` 挂载四川财资领域 skill：

```text
workspace/skills/sichuan-finance/SKILL.md
```

它来自：

```text
domain_packs/sichuan-finance/skills/sichuan-finance/SKILL.md
```

这条路径保留为用户或客户覆盖层。若 workspace 中出现与 builtin 同名的 skill，workspace 版本会覆盖 builtin 版本。

## 加载优先级

加载逻辑在：

```text
nanobot/nanobot/agent/skills.py
```

核心规则：

1. 先扫描 `workspace/skills/`。
2. 再扫描 `nanobot/nanobot/skills/`。
3. 如果 workspace 和 builtin 有同名 skill，workspace 版本优先，builtin 版本会被跳过。
4. 如果配置里设置了 `disabledSkills`，对应 skill 会从可用列表里移除。
5. 如果 skill frontmatter 声明了依赖，例如二进制命令或环境变量，依赖不满足时会标记为 unavailable。

这意味着 workspace skill 天然是覆盖层，builtin skill 是产品默认层。

## Skill 如何进入模型上下文

相关代码：

```text
nanobot/nanobot/agent/context.py
nanobot/nanobot/templates/agent/skills_section.md
```

每轮对话前，`ContextBuilder` 会构建 system prompt。构建流程里会调用 `SkillsLoader`：

1. 读取 always skill。
2. 把 always skill 的完整内容直接放入 `# Active Skills`。
3. 读取普通 skill 的摘要。
4. 把普通 skill 的 name、description、SKILL.md 路径放入 `# Skills`。

普通 skill 不会默认把全文塞进 prompt，而是只给模型一个摘要列表。模板内容大意是：

```text
The following skills extend your capabilities.
To use a skill, read its SKILL.md file using the read_file tool.

- xlsx — Use this skill whenever the user asks about an Excel/table file... /path/to/SKILL.md
```

这样做的好处是节省上下文；缺点是模型需要自己判断是否读取某个 skill。

## 基模如何筛选 Skill

当前没有专门的 embedding 检索或硬路由。筛选主要依赖基模阅读 prompt 中的 skill summary。

判断依据主要来自：

- skill 名称。
- frontmatter 里的 `description`。
- 用户问题里的关键词、文件路径、文件类型、任务意图。

例如当前 builtin `xlsx` skill 的 description 包含：

```text
Use this skill whenever the user asks about an Excel/table file,
especially .xlsx, .xlsm, .xls, .csv, or .tsv paths.
```

当用户问题包含 Excel 路径或表格分析任务时，模型更容易判断该 skill 相关，并调用 `read_file` 读取完整 `SKILL.md`。

实际调用链路：

```text
用户问题
  ↓
system prompt 中包含 skills summary
  ↓
模型判断某个 skill 相关
  ↓
模型调用 read_file 读取 SKILL.md
  ↓
模型按照 skill 指令调用工具
  ↓
模型返回答案
```

在终端中，如果看到类似：

```text
read …/nanobot/nanobot/skills/xlsx/SKILL.md
```

就说明模型确实选择并读取了该 skill。

## Always Skill

skill frontmatter 可以标记 always。被标记为 always 且依赖满足的 skill，会被完整放进 prompt 的 `# Active Skills`。

适合 always 的场景：

- 非常短。
- 对几乎所有任务都必须生效。
- 不想依赖模型主动选择。

不建议把大型表格 skill 直接设为 always，因为会长期占用上下文，并提高每轮 token 成本。

## 当前 xlsx Skill 的定位

当前有两条通用 spreadsheet skill 路线：

```text
nanobot/nanobot/skills/xlsx/SKILL.md
nanobot/nanobot/skills/anthropic-xlsx/SKILL.md
```

`xlsx` 的定位：

- 来自 Codex-style spreadsheet skill。
- 适合作为宽能力兜底，覆盖 workbook 创建、编辑、渲染和验证的思路。
- 仍偏重 Codex artifact runtime，不是 TableClaw 最终唯一核心 skill。

`anthropic-xlsx` 的定位：

- 来自 Anthropic-style spreadsheet skill。
- 更适合当前第二阶段的通用 workbook/artifact 任务：清洗长表、重构工作簿、写公式、构建财务模型、生成对标表、重算/扫错。
- 任务目标通常是交付 `.xlsx` 文件，而不只是自然语言问答。
- 已在 Hermes 长表任务中验证可用，报告位于 `workspace/reports/hermes_anthropic_test/hermes_anthropic_xlsx_skill_eval.md`。

这两者不应同时被理解为最终架构答案。它们是两种参考路线：

```text
轻量 TableClaw skills + 通用工具
  适合高频 QA、排序、筛选、矩阵抽取、领域评测

大 spreadsheet skill
  适合复杂 workbook 清洗、建模、公式、格式、artifact 交付
```

后续可以继续比较两条路线，而不是过早删除其中一条。

## Skill 可见性与评测模式

常用模式：

| 模式 | 配置 | 用途 |
| --- | --- | --- |
| 默认交互 | `nanobot/configs/tableclaw-bailian-dashscope.json` | 所有 builtin skill + workspace skill 可见，用于真实开发和探索。 |
| 低温评测 | `nanobot/configs/tableclaw-bailian-dashscope-eval.json` | 默认评测配置，降低路径漂移。 |
| 小表格 skill 关闭 | `nanobot/configs/tableclaw-bailian-dashscope-no-xlsx-skill.json` | 对照测试，隐藏 `xlsx` 和轻量 table skills。 |
| Anthropic 大 skill 测试 | `nanobot/configs/tableclaw-bailian-dashscope-anthropic-xlsx-only.json` | 隐藏 `xlsx` 与轻量 table skills，只保留 `anthropic-xlsx` 作为主要 spreadsheet skill。 |

注意：

- `disabledSkills` 同时作用于 builtin 和 workspace skill。
- `anthropic-xlsx-only` 当前只屏蔽小表格 skills，没有屏蔽 `sichuan-finance`。Hermes 测试中模型没有走四川业务路线，但如果要做严格“纯通用”对照，应使用干净 workspace 或把 `sichuan-finance` 也加入 `disabledSkills`。
- 不建议把大型 spreadsheet skill 设为 `always`，否则每轮都会消耗大量上下文。

## Builtin Skill 验证结果

### `xlsx`

2026-05-29 已做 smoke test：

- workspace `xlsx` skill 已删除。
- `SkillsLoader` 返回 `xlsx` 的 source 为 `builtin`。
- xlsx 问题触发读取 `nanobot/nanobot/skills/xlsx/SKILL.md`。
- 模型最终答对 eval 表中的 `202602` 最高“营业收现率完成”问题。

### `anthropic-xlsx`

2026-06-22 已做 Hermes artifact test：

- `anthropic-xlsx` 已放入 `nanobot/nanobot/skills/anthropic-xlsx/SKILL.md`，和 `table-read` 等 builtin skill 平级。
- 使用 `tableclaw-bailian-dashscope-anthropic-xlsx-only.json` 隐藏小 table skills。
- 模型明确读取 `anthropic-xlsx/SKILL.md`。
- 输入 `workspace/uploads/Hermes_20Year_Panorama_2006_2025.xlsx`。
- 输出：
  - `workspace/Hermes_Cleaned_Standardized.xlsx`
  - `workspace/Luxury_Peer_Benchmarking.xlsx`
  - `workspace/Hermes_2026_2030_Forecast.xlsx`
- 详细报告：`workspace/reports/hermes_anthropic_test/hermes_anthropic_xlsx_skill_eval.md`。

## 参考 Skill 选型

TableClaw 当前有三个外部 spreadsheet skill 可参考：

- `skills/codex/SKILL.md`
- `skills/kimi_xlsx_skill/SKILL.md`
- `skills/anthropic_xlsx_skill/SKILL.md`

目前 `anthropic-xlsx` 是为了评估通用 workbook/artifact 方向而内置。其许可证标注为 Proprietary；在推送到公开或公司仓库前，需要确认该 skill 的授权边界。长期仍应吸收三家强项，沉淀为 TableClaw 自己的核心表格 skill。详细分析见：

- [参考 Spreadsheet Skills 分析](reference-spreadsheet-skills.md)

## 上线建议

### 1. 保持分层，不把业务知识塞进通用 skill

四川财资这类业务知识继续走：

```text
domain_packs/sichuan-finance/
  -> workspace/skills/sichuan-finance/
  -> workspace/domain_knowledge/
```

通用表格 skill 不写 `200亿省`、四川省指标口径、特定报表 sparse fallback 等业务事实。

### 2. 保留两条通用 spreadsheet 路线

- 轻量 TableClaw skills：保留模块化流程，便于小模型、低 token、高频 QA。
- `anthropic-xlsx` 大 skill：保留复杂 workbook/artifact 交付路线，适合清洗、建模、公式、报告/图表/PPT 上游产物。

后续用真实任务评测决定：

- 哪些规则进入轻量 TableClaw skill。
- 哪些流程继续依赖大 spreadsheet skill。
- 哪些稳定操作应下沉为 deterministic tools。

### 3. 未来 TableClaw native skill

如果要避免 `xlsx` / `anthropic-xlsx` 语义混杂，可以新增：

```text
nanobot/nanobot/skills/tableclaw-table/SKILL.md
nanobot/nanobot/skills/tableclaw-workbook/SKILL.md
```

建议边界：

- `tableclaw-table`：通用 QA、读取、抽取、排序、筛选、校验。
- `tableclaw-workbook`：清洗、编辑、公式、格式、图表、可交付 `.xlsx` artifact。

产品内置 skill 应逐步覆盖：

- 通用 Excel/CSV 读取。
- 多级表头识别。
- 合计/小计行识别。
- 排序、筛选、分组、聚合。
- 公式值读取和精度处理。
- 输出结构化结果。
- workbook 清洗、公式重算、错误扫描、artifact 验证。

### 4. 业务 skill 留在 workspace / domain pack

客户或业务场景专属规则继续放在：

```text
workspace/skills/<business-name>/SKILL.md
```

示例：

```text
workspace/skills/cash-collection-ledger/SKILL.md
workspace/skills/sales-kpi/SKILL.md
workspace/skills/finance-monthly-report/SKILL.md
```

这些 skill 可以描述业务口径：

- 哪些行是汇总行。
- 哪些字段是核心指标。
- 指标单位和展示格式。
- 特定报表的异常值规则。

### 5. 增加 Skill Router

如果后续发现模型有时不读 skill，可以增加一层轻量 router。

router 不需要一开始很复杂，先做规则即可：

- 用户消息包含 `.xlsx`、`.xls`、`.csv`、`.tsv`。
- 用户上传文件的 MIME type 是 spreadsheet。
- 用户问题包含“表格、Excel、筛选、排序、统计、排名、求和、透视”等词。

命中后可以：

- 在 runtime context 里强提示应优先考虑 `tableclaw-xlsx`。
- 或把对应 skill 临时作为 active skill 注入。
- 或在产品层先执行表格结构预解析，再把结构摘要交给 agent。

这会比完全依赖模型从 skill summary 里自选更稳定。

## 设计原则

- 核心能力产品化，业务规则 workspace 化。
- skill 应写流程和判断标准，不堆大量代码。
- 复杂、可测试、可复用的逻辑应沉淀为 tool 或脚本，由 skill 指导模型调用。
- 大 skill 不设 always，避免每轮 token 成本失控。
- description 要短而强，直接覆盖触发条件。
- skill/no-skill 差异要能被日志和 eval 复现，而不是只靠手动观察。

## 当前待办

- 为 `anthropic-xlsx` 路线补 artifact eval：sheet、关键值、公式、文件可打开性、重算/扫错、截图/渲染检查。
- 为纯通用任务明确 skill 可见性：是否禁用 `sichuan-finance`、是否使用干净 workspace、是否只暴露 `anthropic-xlsx`。
- 在更多非四川财资 workbook 上验证大 skill 是否稳定触发和产出可用 artifact。
- 基于测试结果设计 `tableclaw-table` / `tableclaw-workbook` native skill，而不是长期依赖外部 skill 原文。
- 评估是否需要第一版规则型 skill router，尤其是上传文件、单表 active file、复杂 artifact 任务场景。
