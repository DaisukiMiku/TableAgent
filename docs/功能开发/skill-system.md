# TableClaw Skill 模块设计

> 最后更新：2026-05-29
>
> 用途：记录 nanobot skill 的加载、筛选、调用机制，以及 TableClaw 后续开发 skill 功能时的工程边界。

## 当前结论

TableClaw 目前已经把 `xlsx` skill 从 workspace 迁移到 nanobot builtin：

```text
nanobot/nanobot/skills/xlsx/SKILL.md
```

该 builtin skill 当前来自 `skills/codex/SKILL.md`，用于验证“表格能力进入 nanobot 主流程后，xlsx 问题是否仍会触发 skill”。原来的 `workspace/skills/xlsx/SKILL.md` 已删除。

建议上线形态：

- 产品级、稳定、每个部署都需要的能力：放入 `nanobot/nanobot/skills/`，作为 builtin skill。
- 用户级、客户级、项目级业务规则：放入 `workspace/skills/`，作为 workspace skill。
- 后续如果要求更稳定的触发率：在 skill summary 之外增加轻量 skill router，对 `.xlsx`、`.csv`、表格路径等场景做显式激活或强提示。

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

- `memory`
- `summarize`
- `weather`
- `github`
- `cron`
- `tmux`
- `skill-creator`
- `image-generation`

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

当前 TableClaw 不再把核心 `xlsx` skill 放在这里。`workspace/skills/` 保留为用户或客户覆盖层。

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

当前文件：

```text
nanobot/nanobot/skills/xlsx/SKILL.md
```

它承担三个作用：

1. 触发表格任务能力：告诉模型遇到 xlsx/csv/table 问题时读取该 skill。
2. 把 Codex Spreadsheets 的单文件工作簿处理规范先接入 nanobot builtin skill 体系。
3. 验证 workspace 删除后，nanobot 主流程仍能通过 builtin skill 发现表格能力。

注意：当前 builtin `xlsx` 内容偏向 workbook 创建、编辑、渲染和产物验证；它不是最终 TableClaw Core Table Skill。后续仍需要结合 TableClaw 的 QA/eval 目标继续精简和重写。

## Builtin xlsx 验证结果

2026-05-29 已做一次 smoke test：

- workspace `xlsx` skill 已删除。
- `SkillsLoader` 返回 `xlsx` 的 source 为 `builtin`。
- xlsx 问题触发读取 `nanobot/nanobot/skills/xlsx/SKILL.md`。
- 模型最终答对 eval 表中的 `202602` 最高“营业收现率完成”问题。

早期 xlsx skill/no-skill 对照文档已从主线 docs 中清理；当前正式评测入口统一收敛到 [Gold Cases Benchmark](../实验评测/gold-cases/README.md)。

观察：

- 当前 Codex skill 原文约 38KB，token 成本偏高。
- 模型先尝试直接读取表格，遇到截断后才读取 skill。
- 这证明 builtin 接入成功，但也说明下一步需要写更轻、更偏 QA 的 TableClaw 专用表格 skill。

## 参考 Skill 选型

TableClaw 当前有三个外部 spreadsheet skill 可参考：

- `skills/codex/SKILL.md`
- `skills/kimi_xlsx_skill/SKILL.md`
- `skills/anthropic_xlsx_skill/SKILL.md`

它们不建议整包照搬，而应吸收各自强项后沉淀为 TableClaw 自己的核心表格 skill。详细分析见：

- [参考 Spreadsheet Skills 分析](reference-spreadsheet-skills.md)

## 上线建议

### 第一阶段：保持 workspace skill

当前已不再保留 workspace 版本：

```text
workspace/skills/xlsx/SKILL.md
```

目标：

- 该路径未来只用于用户或客户自定义覆盖。
- 如果需要临时覆盖 builtin `xlsx`，可以重新在 workspace 创建同名 skill。
- 默认产品能力以 `nanobot/nanobot/skills/xlsx/SKILL.md` 为准。

### 第二阶段：沉淀 TableClaw builtin skill

当前已先把 Codex 单文件 skill 放入：

```text
nanobot/nanobot/skills/xlsx/SKILL.md
```

后续如果要避免和用户通用 `xlsx` 语义冲突，可以再迁移或复制为：

```text
nanobot/nanobot/skills/tableclaw-xlsx/SKILL.md
```

产品内置 skill 应覆盖：

- 通用 Excel/CSV 读取。
- 多级表头识别。
- 合计/小计行识别。
- 排序、筛选、分组、聚合。
- 公式值读取和精度处理。
- 输出结构化结果。

### 第三阶段：业务 skill 留在 workspace

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

### 第四阶段：增加 Skill Router

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

- 继续测试 `nanobot/nanobot/skills/xlsx/SKILL.md` 是否稳定触发表格任务。
- 增加自动 eval runner，记录是否读取 skill、是否调用 Python/openpyxl、答案是否正确、token 消耗。
- 在更多工业表格上验证当前 xlsx skill 是否仍然有效。
- 基于测试结果重写 `tableclaw-xlsx` 或 `tableclaw-table` builtin skill 的最终内容和命名。
- 评估是否需要第一版规则型 skill router。
