# Generic Table Tasks Eval

> 最后更新：2026-06-22

本目录维护 TableClaw 第二阶段的通用表格上下游任务评测。它和四川财资 `gold-cases/` 主线不同：这里不评估某个业务 domain pack 的拟合效果，而是观察 TableClaw 在不依赖业务知识时，能否通过通用 spreadsheet skill、inspect、代码执行和 artifact 验证完成真实复杂表格任务。

## 评测目标

通用 table task 不只看最终自然语言答案，而是看完整工作流：

```text
用户上传/指定真实 workbook
-> 模型识别这是通用表格任务
-> 选择并读取通用 spreadsheet skill
-> inspect workbook 结构
-> 使用 Python/openpyxl/pandas/LibreOffice 或 TableClaw tools 执行
-> 产出 xlsx / 图表 / 报告 / PPT 上游数据等 artifact
-> 记录 skill 选择、tool trace、耗时、token、输出文件和验证结果
```

## Skill 可见性原则

通用评测应避免加载四川财资业务知识：

- 禁用 `sichuan-finance` workspace/domain skill。
- 禁用早期手写的轻量 table skills：`table-read`、`table-clean`、`table-validate`、`table-report`、`table-formula-debug`、`table-chart`。
- 禁用旧的 `xlsx` 宽兜底 skill。
- 仅保留 `anthropic-xlsx` 作为主要 spreadsheet skill，用于观察大通用表格 skill 能否覆盖复杂 workbook artifact 任务。

当前配置：

```text
nanobot/configs/tableclaw-bailian-dashscope-anthropic-xlsx-only.json
```

## 当前 Runs

| Run | 任务 | 配置 | 结果 |
| --- | --- | --- | --- |
| [Hermes Anthropic XLSX Skill Eval](hermes-anthropic-xlsx-20260622.md) | Hermès 20 年长表清洗、奢侈品同行对标、2026-2030 财务预测模型 | `anthropic-xlsx-only` | 成功产出 3 个 workbook artifact，并归档日志、token、tool trace 和预览图 |

## 当前 Artifact 评测口径

本目录当前是 v0 smoke/eval，先评估以下内容：

- 是否正确识别并读取通用 spreadsheet skill。
- 是否避免调用四川财资 domain knowledge。
- 是否能 inspect 原始 workbook，并恢复真实 sheet/section 结构。
- 是否产出用户要求的文件。
- 输出 workbook 是否包含合理 sheet、关键字段和公式。
- 是否记录工具轨迹、耗时、token、日志和中间判断。

后续需要补充自动化指标：

- 文件可打开性。
- LibreOffice 重算和公式错误扫描。
- 关键单元格/关键公式断言。
- 渲染截图检查：标题、表格、图表是否可读。
- 数据来源校验：外部 peer 数据是否有来源或明确标注为估算。
- 与 small-skill / no-skill / 其他模型的 A/B 对比。

## 维护规则

- 每个通用任务一个独立 run 文档。
- 产物归档到 `artifacts/<run-id>/`，包括 xlsx、日志、usage、tool-results 和预览图。
- 不把 `workspace/` 作为正式归档来源；workspace 只是运行态目录。
- 正式通用评测要写清楚 skill 可见性，避免和四川财资 domain pack 结果混淆。
