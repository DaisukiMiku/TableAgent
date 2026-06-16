# TableClaw 文档总览

> 最后更新：2026-06-16

本目录只保留 TableClaw 当前研发主线的统筹文档、功能设计和评测入口。早期 smoke、mentor demo、skill/no-skill 过拟合展示和过长逐轮日志已从主线文档中清理；如需追溯，可从 git 历史恢复。

## 当前定位

TableClaw 是通用 Table Agent 能力栈。当前路线是：

- Agent Core / Runtime：对话循环、工具协议、session、workspace、trace、harness。
- Context / Storage Layer：skill、domain knowledge、memory、RAG、artifacts、tool traces。
- Generic Table Tools：retrieve、inspect、catalog、schema cache、extract_matrix、rank、filter、time_series、validate。
- Domain Pack：行业/客户的业务口径、表族经验、cohort、sparse fallback、评测样本和必要专属工具。

当前用 `domain_packs/sichuan-finance/` 作为第一个领域包验证路线；它不是项目边界，只是当前工程验证场景。

## 快速入口

| 分类 | 文档 | 用途 |
| --- | --- | --- |
| 架构 | [项目目录结构](架构/project-structure.md) | 说明代码、workspace、domain pack、eval、docs 的边界。 |
| 功能开发 | [TableClaw 定位与 Workflow 设计](功能开发/tableclaw-positioning-and-workflow.md) | 对齐产品调研、workflow、memory/context/RAG、harness 与长期路线。 |
| 功能开发 | [Domain Knowledge Migration](功能开发/domain-knowledge-migration.md) | 说明四川财资领域知识如何迁移为 domain pack、workspace skill 和 `tableclaw_domain_knowledge`。 |
| 功能开发 | [Table Catalog Layer RFC](功能开发/table-catalog-layer-rfc.md) | 上传表 profile、virtual clean view、description 与 catalog-assisted retrieval 设计。 |
| 功能开发 | [Table Schema Cache RFC](功能开发/table-schema-cache-rfc.md) | `workspace/table_cache/`、`tableclaw_inspect` 与 schema-based retrieval 设计。 |
| 功能开发 | [Skill 模块设计](功能开发/skill-system.md) | builtin skill、workspace skill、domain skill 的加载和边界。 |
| 功能开发 | [参考 Spreadsheet Skills 分析](功能开发/reference-spreadsheet-skills.md) | Codex / Kimi / Claude 表格 skill 的取舍分析。 |
| 功能开发 | [Token Usage 统计](功能开发/token-usage.md) | usage 持久化、字段和查看方式。 |
| 实验评测 | [实验评测索引](实验评测/README.md) | 当前评测入口、运行命令和输出位置。 |
| 实验评测 | [Gold Cases Benchmark](实验评测/gold-cases/README.md) | gold40、badcase122、query100 的协议、历史 run 和最新结果。 |
| 项目管理 | [阶段进度报告](项目管理/2026-06-12-tableclaw-progress-report.md) | 当前最高 run、核心能力和问题边界。 |
| 项目管理 | [TODO 计划](项目管理/TODO.md) | 当前 P0/P1/P2 待办。 |
| 项目管理 | [开发日志](项目管理/development-log.md) | 最近关键决策、验证和上下文恢复。 |

## 当前项目状态

- 启动：`./start.sh`。
- 模型：DashScope OpenAI-compatible，默认 `deepseek-v4-pro`。
- 交互配置：`nanobot/configs/tableclaw-bailian-dashscope.json`，保留较高 temperature 以便探索。
- 评测配置：`nanobot/configs/tableclaw-bailian-dashscope-eval.json`，`eval_gold_parallel.sh` 默认使用低温配置以降低路径漂移。
- Workspace：`workspace/`，用户上传表放在 `workspace/uploads/`。
- 通用工具：`tableclaw_retrieve_tables`、`tableclaw_inspect`、catalog/schema cache、matrix/time-series/rank/filter 等。
- 领域层：`domain_packs/sichuan-finance/`，启动时同步到 `workspace/skills/` 和 `workspace/domain_knowledge/`。
- 主评测资产：
  - `eval_test/test_dataset/gold_cases.jsonl`：40 条人工 gold cases。
  - `eval_test/test_dataset/bad_cases.jsonl`：122 条 reviewed badcase。
  - `eval_test/test_dataset/query_variants_100*.jsonl`：query rewrite 泛化测试。
- 最新正式归档：`2026-06-16-v3-final-gold-issue-adjusted`。
  - 544 raw cases，排除 32 个明显 gold/task issue 后，512 scored cases。
  - all scored cases 主 ACC：95.70%。
  - badcase122 adjusted 平均 ACC：97.41%。
  - query100 adjusted 平均 ACC：94.28%。
- DeepSeek full40 历史稳定性参考：after-cohort-fix @4 平均 82.50%，单次最高 87.50%。
- 强基模参考上限：GPT-5.5 full40 82.50% ACC，仅作为轨迹和上限参考，不与 DeepSeek 主线混口径比较。

## 推荐阅读顺序

1. [项目目录结构](架构/project-structure.md)
2. [TableClaw 定位与 Workflow 设计](功能开发/tableclaw-positioning-and-workflow.md)
3. [Domain Knowledge Migration](功能开发/domain-knowledge-migration.md)
4. [Table Catalog Layer RFC](功能开发/table-catalog-layer-rfc.md)
5. [Table Schema Cache RFC](功能开发/table-schema-cache-rfc.md)
6. [Gold Cases Benchmark](实验评测/gold-cases/README.md)
7. [TODO 计划](项目管理/TODO.md)
8. [开发日志](项目管理/development-log.md)

## 文档维护规则

- 根目录只保留本总览。
- 功能设计放入 `docs/功能开发/`。
- 架构和目录职责变化更新 `docs/架构/`。
- 正式 benchmark 记录放入 `docs/实验评测/gold-cases/`。
- 阶段计划、开发日志、上下文恢复放入 `docs/项目管理/`。
- 临时展示、一次性 smoke、过拟合 demo 不进入主线文档；必要时只在 git 历史或本地运行产物中追溯。
