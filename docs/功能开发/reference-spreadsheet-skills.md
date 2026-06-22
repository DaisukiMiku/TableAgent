# 参考 Spreadsheet Skills 分析

> 最后更新：2026-06-22
>
> 用途：比较 `skills/` 下三个外部参考表格 skill，判断哪些能力适合吸收到 TableClaw Core Table Skill。

## 总结结论

三个参考 skill 不建议长期整包照搬进 TableClaw。更合理的方式是吸收各自强项，沉淀成 TableClaw 自己的核心表格流程。

当前工程状态有一个阶段性例外：`anthropic_xlsx_skill/` 已被复制为 builtin `nanobot/nanobot/skills/anthropic-xlsx/`，用于第二阶段通用 workbook/artifact 任务实验。这是为了快速验证复杂 `.xlsx` 清洗、公式、格式、建模和交付型 artifact 能力，不代表最终产品必须长期依赖该外部 skill 原文。

| 参考 skill | 核心定位 | 主要依赖 | 最适合吸收的能力 | 不适合直接照搬的原因 |
| --- | --- | --- | --- | --- |
| Codex Spreadsheets | 高质量创建、编辑、渲染、验证工作簿 | Node.js + `@oai/artifact-tool` + Codex workspace dependencies | 工作簿产物质量标准、render/inspect/verify 闭环、dashboard/chart/table 输出规范 | 依赖 Codex 专用 runtime 和 artifact-tool，和当前 nanobot 本地 Python/openpyxl 路线不完全一致 |
| Kimi xlsx | 高级 Excel 生成、验证、PivotTable 工具链 | Python + pandas/openpyxl + `KimiXlsx` CLI | formula recheck、reference-check、OpenXML validate、PivotTable 创建顺序和参数化流程 | `KimiXlsx` 是 73MB 二进制且路径写死为 `/app/.kimi/...`，当前 macOS 本地不可直接产品化 |
| Anthropic/Claude xlsx | 稳健的 openpyxl/pandas + LibreOffice 重算流程 | Python + pandas/openpyxl + LibreOffice + `scripts/recalc.py` | 公式不硬编码、LibreOffice 重算、公式错误扫描、金融模型格式规范 | 它的目标强调“必须交付 Excel 文件”，而 TableClaw 当前首先是表格 QA/分析 agent |

当前 TableClaw 的长期下一步不应是“选一个搬进去”，而是做：

```text
TableClaw Core Table Skill v0
```

当前已先把 Codex 单文件 skill 放入 `nanobot/nanobot/skills/xlsx/SKILL.md`，并把 Anthropic spreadsheet skill 放入 `nanobot/nanobot/skills/anthropic-xlsx/SKILL.md`。前者作为宽能力兜底，后者作为复杂 workbook/artifact 路线实验。后续仍应吸收三者强项，沉淀成 TableClaw 自己的核心表格流程。

## Codex Spreadsheets Skill

路径：

```text
skills/codex/SKILL.md
```

### 擅长什么

Codex skill 最强的是“产物型 spreadsheet 工作流”。

它强调：

- 创建、修改、分析、可视化 spreadsheet。
- 用 `@oai/artifact-tool` 统一处理 workbook。
- 支持 inspect、render、trace、export。
- 交付前必须做视觉渲染和公式检查。
- 对 dashboard、chart、table、data validation、conditional formatting 等产物质量要求很高。
- 对 Google Sheets 目标产物有明确导入路径。

适合的任务：

- 新建一个专业工作簿。
- 修改现有工作簿并保持格式。
- 做 dashboard、图表、KPI summary。
- 生成面向交付的 `.xlsx` 或 Google Sheets。

### 主要依赖

- Codex workspace dependency loader。
- Node runtime。
- `@oai/artifact-tool`。
- Google Drive plugin，若目标是 native Google Sheets。

它明确要求不要使用系统 node/python、不要随便安装包、不要 fallback 到 openpyxl，除非用户明确要求。

### 适合 TableClaw 吸收的部分

适合吸收为流程规范：

- 先 build，再 inspect，再 render，再 repair，再 export。
- 对非平凡表格输出，必须有 verification pass。
- 对 dashboard/chart 类任务，不能只输出普通表格。
- 交付前检查公式错误、图表空白、关键标题和数值是否被裁剪。
- 输出 artifact 时只暴露最终文件，不暴露中间 builder/log。

这些可以成为 TableClaw 未来“生成/编辑表格”的质量标准。

### 不建议直接照搬的部分

不建议直接照搬整个 skill，因为：

- 依赖 Codex 专用 runtime，不是当前 nanobot 普通本地环境天然具备的能力。
- 它禁止 openpyxl/pandas fallback，而 TableClaw 当前最稳定的读取和 QA 路线正是 Python/openpyxl。
- 它偏“生成高质量 workbook artifact”，而当前 TableClaw 首要目标是“读用户表格并回答问题”。

## Kimi xlsx Skill

路径：

```text
skills/kimi_xlsx_skill/SKILL.md
skills/kimi_xlsx_skill/pivot-table.md
skills/kimi_xlsx_skill/scripts/KimiXlsx
```

### 擅长什么

Kimi skill 最强的是“Excel 结构验证 + PivotTable 工具化”。

它包含一个 `KimiXlsx` CLI，提供：

- `inspect`：分析 sheet、headers、data range。
- `recheck`：检查公式错误、0 值异常、隐式数组公式。
- `reference-check`：检查公式引用范围、表头误引用、孤立公式模式。
- `pivot`：用 OpenXML SDK 创建 PivotTable，可带 chart。
- `chart-verify`：检查 chart 是否有真实数据。
- `validate`：检查 OpenXML 结构，确保 Excel 可打开。

特别值得注意的是，它对 PivotTable 的流程写得很清楚：

```text
recheck -> reference-check -> inspect -> pivot -> validate
```

理由是 PivotTable 会缓存源数据，所以必须在创建 pivot 之前完成数据和公式验证。

### 主要依赖

- Python 3。
- pandas。
- openpyxl。
- `KimiXlsx` CLI 二进制。

当前仓库里 `KimiXlsx` 文件大小约 73MB，并且原 skill 中命令路径写死为：

```text
/app/.kimi/skills/kimi-xlsx/scripts/KimiXlsx
```

### 适合 TableClaw 吸收的部分

适合吸收为工程检查项：

- 表格任务先 `inspect`，不要盲目读取大表。
- 公式任务要做 recheck。
- 公式引用要做 reference-check。
- 生成图表后要验证 chart 非空。
- 生成或修改复杂 workbook 后要做 OpenXML validate。
- PivotTable 必须在源数据稳定后创建。

适合未来做成 TableClaw 工具：

```text
table_inspect
table_formula_check
table_reference_check
table_chart_verify
table_openxml_validate
table_pivot_create
```

这些可以先不用二进制实现，先用 Python/openpyxl 或更轻量的校验脚本做 v0。

### 不建议直接照搬的部分

不建议直接搬整个 Kimi skill，因为：

- 二进制体积大。
- 当前二进制环境兼容性不明，macOS 本地不能直接按 `/app/.kimi/...` 路径使用。
- 直接内置会引入发布、许可证、跨平台、沙箱执行等问题。
- 它同样更偏“创建/修改 Excel 产物”，而不是当前最小 Table QA。

## Anthropic / Claude xlsx Skill

路径：

```text
skills/anthropic_xlsx_skill/SKILL.md
skills/anthropic_xlsx_skill/scripts/recalc.py
```

### 擅长什么

Anthropic skill 最强的是“用标准 Python Excel 栈可靠完成表格创建、编辑、公式验证”。

它强调：

- pandas 负责数据分析、清洗、批量处理。
- openpyxl 负责公式、格式、Excel 特性。
- 所有计算应尽量写成 Excel 公式，而不是 Python 算完硬编码。
- 用 LibreOffice 重算公式缓存。
- 用 `scripts/recalc.py` 扫描所有公式错误。
- 修改已有模板时保持原格式，不强行套新样式。
- 对金融模型有明确颜色、数字格式、假设单元格、硬编码来源注释规范。

### 主要依赖

- Python。
- pandas。
- openpyxl。
- LibreOffice。
- `scripts/recalc.py` 及其 office helper。

当前仓库里只保留了 `scripts/recalc.py`，但它在原 skill 中依赖 `scripts/office/` helper。若要实际复用，需要确认辅助脚本是否完整。

### 适合 TableClaw 吸收的部分

非常适合当前 TableClaw v0 吸收：

- QA 时读取公式结果用 `load_workbook(..., data_only=True)`。
- 不要把 Excel 公式误保存为纯值。
- 对公式和复杂表格编辑，保存后必须重算并扫错。
- 处理财务/经营指标时，要保留数值精度和单位。
- 编辑已有表格时，优先尊重原模板结构和格式。
- 大表读取时用 `read_only=True`。

这些和 TableClaw 后续 Core Table Skill 的 QA 路线最接近。

### 不建议直接照搬的部分

不建议长期原样照搬，因为：

- 它的 description 明确要求“deliverable must be a spreadsheet file”，而 TableClaw 现在很多场景只是问答，不需要生成文件。
- 金融模型规范很重，不适合每个普通表格 QA 都加载。
- 若 `scripts/recalc.py` 的依赖目录不完整，直接写进 TableClaw 流程会造成工具不可用。

### 当前实验接入状态

2026-06-22，Anthropic-style xlsx skill 已接入为：

```text
nanobot/nanobot/skills/anthropic-xlsx/
├── SKILL.md
├── LICENSE.txt
└── scripts/
    ├── recalc.py
    └── office/
```

专用测试配置：

```text
nanobot/configs/tableclaw-bailian-dashscope-anthropic-xlsx-only.json
```

该配置隐藏 `xlsx` 与 6 个轻量 table skills，用于观察大 spreadsheet skill 是否能独立指导复杂 workbook artifact 任务。Hermes smoke 已验证它能产出清洗表、同行对标表和 2026-2030 预测模型。

注意事项：

- 该 skill frontmatter 标注为 proprietary license，公开或公司分发前需要确认授权边界。
- 它更适合交付 `.xlsx` 文件，不适合作为每个表格 QA 的 always skill。
- 它能提升 artifact workflow 的流程质量，但仍需要 TableClaw 自己的 deterministic tools、artifact eval 和数据来源校验。

## 对 TableClaw 的能力取舍

### 当前阶段：QA 主线 + Artifact 迁移并行

当前 TableClaw 有两条重点：

- QA / benchmark 主线：用户给表格路径或业务问题，Agent 能召回、inspect、抽取、计算、验证并说明来源。
- Workbook / artifact 主线：用户给复杂 workbook，Agent 能清洗、重构、写公式、生成模型/图表/报告上游文件，并验证产物可打开、公式可重算。

因此 v0 应继续吸收 Anthropic 的 Python/openpyxl/LibreOffice 路线、Kimi 的 inspect/check 思想，以及 Codex 的 render/verify artifact 标准。

Codex 的 artifact/render/dashboard 能力可以先作为后续“生成工作簿”方向保留。

### 中期：从 Skill 到 Tool

skill 适合写流程，但复杂检查应该逐步工具化。

建议沉淀的 TableClaw tools：

| Tool | 来源灵感 | 作用 |
| --- | --- | --- |
| `table_inspect` | Kimi inspect + Codex inspect | 输出 sheets、维度、表头、合并单元格、样例行 |
| `table_query` | 当前 xlsx skill + openpyxl | 根据 period/metric/filter/rank 精确查询 |
| `table_formula_check` | Kimi recheck + Anthropic recalc | 检查公式错误和公式缓存 |
| `table_reference_check` | Kimi reference-check | 检查异常公式引用 |
| `table_render_preview` | Codex render | 生成可视化预览，用于编辑/交付前检查 |
| `table_pivot_create` | Kimi pivot | 后续支持 PivotTable |

### 长期：Skill 分层

不建议一开始拆太细，但长期可以分层：

```text
tableclaw-table          # 通用表格 QA/读取/计算
tableclaw-table-edit     # 编辑、写公式、保持格式
tableclaw-table-visual   # 图表、dashboard、render QA
tableclaw-table-pivot    # 透视表
tableclaw-finance-model  # 财务模型规范
```

这样模型可以按任务选择更小、更相关的 skill，减少每轮 token，也降低误用概率。

## 推荐的下一步

1. 继续保留 `xlsx` 与 `anthropic-xlsx` 两条 builtin 参考路线，用不同配置做对照。
2. 为 Hermes 类 artifact 任务补标准 eval：文件存在、sheet/公式/格式/关键值、LibreOffice 重算、截图/渲染检查。
3. 写 `nanobot/nanobot/skills/tableclaw-table/SKILL.md` v0，面向 QA / 抽取 / 验证。
4. 写 `nanobot/nanobot/skills/tableclaw-workbook/SKILL.md` v0，面向清洗 / 编辑 / 公式 / artifact。
5. v0 内容不要照搬三家全文，只保留 TableClaw 当前需要的表格工作流，并把复杂稳定逻辑下沉为 tools。
