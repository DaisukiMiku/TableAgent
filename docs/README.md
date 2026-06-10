# TableClaw 文档总览

> 最后更新：2026-06-10

本目录只维护 TableClaw 项目的统筹文档和分类索引。具体设计、实验、功能说明分别放入子目录，避免文档平铺后难以维护。

## 快速入口

| 分类 | 文档 | 用途 |
| --- | --- | --- |
| 架构 | [项目目录结构](架构/project-structure.md) | 说明 TableClaw、nanobot、workspace、eval、skills 等目录职责。 |
| 功能开发 | [Skill 模块设计](功能开发/skill-system.md) | 说明 nanobot skill 的加载、选择、调用逻辑，以及 TableClaw 上线时 builtin/workspace skill 的边界。 |
| 功能开发 | [TableClaw 定位与 Workflow 设计](功能开发/tableclaw-positioning-and-workflow.md) | 对齐产品调研、能力边界、TableAgent workflow、memory/context/RAG、harness 和 eval 路线。 |
| 功能开发 | [Table Schema Cache RFC](功能开发/table-schema-cache-rfc.md) | 说明 `workspace/table_cache/`、`tableclaw_inspect` 与 schema-based retrieval 的设计。 |
| 功能开发 | [参考 Spreadsheet Skills 分析](功能开发/reference-spreadsheet-skills.md) | 比较 Codex / Kimi / Claude 三个表格 skill，提炼适合 TableClaw 吸收的能力。 |
| 功能开发 | [Token Usage 统计](功能开发/token-usage.md) | 说明运行时 token usage 的写入位置、字段、查看方式。 |
| 实验评测 | [实验评测索引](实验评测/README.md) | 说明当前 12 任务 skill-on/off 主线评测与运行方式。 |
| 实验评测 | [xlsx Skill Selection Matrix](实验评测/skill-matrix/xlsx-skill-selection-matrix.md) | 原始 10 任务 simple/medium/hard × skill-on/off 对照（用 Codex 原文 xlsx skill）。 |
| 实验评测 | [Workflow Routing Eval](实验评测/workflow-routing.md) | 2 个新增 workflow task，用于观察多 skill 分阶段选择。 |
| 实验评测 | [Uploaded Table Workflow](实验评测/uploaded-table-workflow/latest-eval-summary.md) | 模拟用户已上传工业表，验证 Nanobot 内置表格召回工具、候选表选择、skill workflow 和 trace/token 日志。 |
| 实验评测 | [Gold Cases Smoke](实验评测/gold-cases/smoke-eval-summary.md) | 人工标准答案 case 的首条 smoke 结果；当前 gold_cases.jsonl 共 40 条。 |
| 项目管理 | [TODO 计划](项目管理/TODO.md) | 当前 / 近期 / 中期 / 长期待办，复选框格式，做完打勾。 |
| 项目管理 | [开发日志](项目管理/development-log.md) | 按时间记录关键决策、配置、验证结果和后续待办。 |

## 当前项目阶段

TableClaw 当前是一个基于 nanobot 的本地表格 Agent 原型，已经具备：

- 一键启动：`./start.sh`。
- 一键评测（12 任务矩阵）：`./eval.sh`。
- 一键 uploaded-table workflow 评测：`./eval.sh --raw-cleaned --limit 10 --modes skill-on`。
- 百炼 DashScope OpenAI 兼容接口模型配置（默认 `deepseek-v4-pro`）。
- 项目内 workspace：`workspace/`。
- builtin skill：`xlsx`（Codex Spreadsheets 原文）+ 6 个 TableClaw 轻量 workflow skills。
- 统一 eval dataset：`eval_test/test_dataset/tasks.jsonl`（12 任务，含 2 个 workflow routing 任务）。
- 原始评测清洗集：`eval_test/test_dataset/raw_eval_cleaned.jsonl`（165 条候选任务），当前 workflow 评测先抽 10 条。
- 人工 gold cases：`eval_test/test_dataset/gold_cases.jsonl`（40 条，`./eval.sh --gold-cases --modes skill-on` 默认全量）。
- Nanobot 内置表格工具：`tableclaw_retrieve_tables` 从 `workspace/uploads/` 召回候选表，`tableclaw_inspect` 生成/复用 `workspace/table_cache/` schema。
- 运行时 token usage 持久化：`workspace/usage/usage.jsonl`。

## 文档维护规范

- 根目录只放本总览，不继续平铺专题文档。
- 新的产品/工程功能文档放入 `docs/功能开发/`。
- 架构和目录职责变化更新 `docs/架构/`。
- 实验、评测、消融、benchmark 结果放入 `docs/实验评测/<线名>/`，由 `docs/实验评测/README.md` 索引。
- 开发过程、上下文恢复、阶段性待办放入 `docs/项目管理/`。
- 文档引用尽量使用相对链接，便于移动项目目录后继续可读。

## 建议阅读顺序

1. 先读 [项目目录结构](架构/project-structure.md)，理解当前代码和运行状态放在哪里。
2. 再读 [TableClaw 定位与 Workflow 设计](功能开发/tableclaw-positioning-and-workflow.md)，理解老师要求对应的产品与工程路线。
3. 再读 [Table Schema Cache RFC](功能开发/table-schema-cache-rfc.md)，理解上传表如何被缓存、召回和 inspect。
4. 再读 [Skill 模块设计](功能开发/skill-system.md)，理解 TableClaw 的核心能力扩展方式。
5. 如果要看产品级 skill 价值评估，读 [xlsx Skill Selection Matrix](实验评测/skill-matrix/xlsx-skill-selection-matrix.md) 并跑 `./eval.sh`。
6. 如果要看 workflow skill 编排，读 [Workflow Routing Eval](实验评测/workflow-routing.md) 并跑 `./eval.sh --case workflow`。
7. 如果要看“用户已上传多张表 -> Nanobot 自动召回表格 -> skill workflow 执行”，读 [Uploaded Table Workflow](实验评测/uploaded-table-workflow/latest-eval-summary.md) 并跑 `./eval.sh --raw-cleaned --limit 10 --modes skill-on`。
8. 如果要看人工 gold case 入口，读 [Gold Cases Smoke](实验评测/gold-cases/smoke-eval-summary.md) 并跑 `./eval.sh --gold-cases --list-tasks`。
9. 如果要看成本和调用统计，读 [Token Usage 统计](功能开发/token-usage.md)。
10. 如果要接着开发，读 [开发日志](项目管理/development-log.md) 恢复上下文。
