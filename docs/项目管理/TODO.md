# TableClaw TODO

> 最后更新：2026-06-22
>
> 本文件只维护当前和下一阶段待办。旧版流水账已从主线文档中清理，必要时从 git 历史恢复。

## 当前工程边界

TableClaw 当前主线是 To C / 通用 Table Agent 能力栈。四川财资工业表格是第一个 domain pack 验证场景，已基本跑通高准确率评测闭环；下一阶段开始把能力迁移到更通用的表格上下游任务，包括复杂 workbook 清洗、对标分析、公式/图表/报告/PPT 上游 artifact。

分层边界：

- Core Agent / Runtime：尽量不为单一业务场景改底层循环、工具协议、session、workspace、trace 和 harness。
- Context / Storage Layer：skill、domain knowledge、memory、RAG、artifacts 和 tool traces 承接流程经验、业务知识、动态上下文和历史证据。
- Generic TableClaw Tools：召回、inspect、schema/cache、catalog、matrix、time-series、rank、filter 等保持领域无关。
- Domain Pack：四川财资业务口径、表族映射、固定 cohort、ranking policy、badcase 经验放在 `domain_packs/sichuan-finance/`。
- Eval / Harness：提供观察、回归和归因证据，帮助判断经验进入 memory、domain knowledge、skill、generic tool，还是保持开放探索。

## 已完成的主线能力

- [x] 一键启动：`./start.sh`。
- [x] DeepSeek / DashScope OpenAI-compatible 配置，当前默认 `deepseek-v4-pro`。
- [x] Workspace 固定在项目内：`workspace/`。
- [x] 表格上传模拟入口：`workspace/uploads/`。
- [x] `tableclaw_retrieve_tables`：上传表召回。
- [x] `tableclaw_inspect`：表结构 inspect + `workspace/table_cache/` schema cache。
- [x] Table Catalog Layer v0：profile、virtual clean view、description，辅助召回。
- [x] Gold cases benchmark：40 条人工标准答案 + 并行 runner + LLM judge + numeric/entity F1。
- [x] 图表题评测口径调整：当前优先评测底层数据正确性，不评判图形美观。
- [x] 关键工具路径：matrix/time-series/rank/filter 等表格读算工具。
- [x] DeepSeek 早期关键 full40 归档：80.00% ACC。
- [x] GPT-5.5 full40 归档：82.50% ACC，作为强基模上限和轨迹参考。
- [x] 四川财资 domain pack：知识 JSON + workspace skill + `tableclaw_domain_knowledge`。
- [x] 文档主线清理：移除早期 smoke/mentor/skill-matrix 过期文档，保留 gold benchmark 主线。
- [x] `200亿省` 当前 gold/reporting cohort 修正为 7 省，并让 `extract_matrix` 可从 domain pack 自动展开 cohort。
- [x] DeepSeek after-cohort-fix full40 @4：平均 ACC 82.50%，证明 domain pack + tool cohort 路线有效。
- [x] 2026-06-15 Domain Overrides + Rank Filter 归档：gold40 A/B 平均 78.75%，badcase122 A/B/C 平均 88.25%，单次最高 90.98%。
- [x] 2026-06-16 V3 Final Eight-Way Eval 归档：badcase122 x3 + query100 x5；排除明显 gold/task issue 后 all scored official ACC 95.20%，pre-scored ACC 92.50%，badcase adjusted avg 96.55%，query adjusted avg 94.19%。
- [x] Gold/task issue 排除口径：runner 写入 `gold_issue_flags` / `excluded_from_acc`，主 ACC 排除明显题面/gold 问题，同时保留 raw ACC。
- [x] `anthropic-xlsx` builtin skill：已放入 `nanobot/nanobot/skills/anthropic-xlsx/`，和 `table-read` 等内置 skill 平级。
- [x] `anthropic-xlsx-only` 配置：`nanobot/configs/tableclaw-bailian-dashscope-anthropic-xlsx-only.json`，用于隐藏小 table skills，测试大 spreadsheet skill 路线。
- [x] Hermes 通用 artifact smoke：完成长表标准化、奢侈品同行对标、2026-2030 财务预测模型三类 workbook 输出。

## P0：下一轮必须做

- [ ] **通用迁移任务集 v0**：在四川财资以外，整理 5-10 个真实 workbook 上下游任务，覆盖清洗、公式、图表、报告、预测模型和 PPT 上游数据。
- [ ] **Hermes artifact eval**：为当前 Hermes 三个输出文件补自动检查脚本，验证 sheet、关键列、公式数量、关键值、文件可打开性、必要时 LibreOffice 重算。
- [ ] **通用 skill 可见性协议**：明确默认交互、领域业务评测、纯通用 artifact 评测三种配置的 `disabledSkills` / workspace skill 策略，避免通用任务被业务 skill 摘要污染。
- [ ] **Anthropic license review**：`anthropic-xlsx` frontmatter 标注 proprietary license；推送公开或公司仓库前确认授权边界，或改为内部实验资产。
- [ ] **badcase 三分流持续维护**：对剩余错误样本标注为 `generic-tool` / `domain-knowledge` / `prompt-or-eval` / `gold-task-issue`，避免把业务知识写死到通用工具。
- [x] **处理新 badcase 文件**：读取 `eval_test/test_dataset/source/300条badcase.xlsx`，清洗成 `eval_test/test_dataset/bad_cases.jsonl`。
- [x] **Domain pack targeted eval v0**：case 5/19/20/22/29/40 小样本验证，cohort 修正后 19/22/29/40 有改善；case5 暴露 2025-12 sparse 短板。
- [x] **Domain pack targeted eval v1**：已通过 badcase122 与 query100 五轮正式评测验证 domain pack 主线收益。
- [x] **DeepSeek full40 复测**：after-cohort-fix @4 平均 ACC 82.50%，已超过 80.00% 历史归档 run。
- [ ] **filter_qa 专项**：已有 rank/top 条件支持，但模型主动调用仍不稳定；继续增强多条件筛选、cohort 内筛选、缺值/排名列共存判断和 tool-selection guidance。
- [ ] **召回评估 gold mapping**：给 40 条 gold cases 补 `gold_table_id/table_path`，只给 evaluator，不进 prompt。
- [ ] **Recall@k 指标**：统计 `tableclaw_retrieve_tables` top1/top3/top5 是否命中 gold table。
- [x] **工具一致性检查**：主线文档已统一到当前 `TRACKED_TABLECLAW_TOOLS` 和 v5 judge 口径；旧 v4rerun 文档作为历史归档保留。
- [x] **领域知识工程化 v1**：拆分 `knowledge_src/`，新增 `manifest.json`、`build_knowledge.py`、`validate_knowledge.py`，保留编译后的运行时 JSON 以保证兼容。
- [ ] **领域知识 provenance v2**：为每条 `validation_override` / `recommended_plan` / badcase experience 补充稳定 `id`、来源 case、置信度和更新时间。

## P1：短期增强

- [ ] **TableClaw native skill 设计**：拆出 `tableclaw-table`（QA/抽取/验证）与 `tableclaw-workbook`（清洗/公式/图表/artifact）草案，吸收 Codex/Kimi/Anthropic 强项，但不整包依赖外部 skill。
- [ ] **Artifact 评测协议**：除了自然语言 ACC，新增 workbook-level 指标：文件存在、sheet/schema、关键值、公式错误、格式基本检查、图表/截图渲染、数据来源说明。
- [ ] **跨 artifact workflow**：验证表格 -> 报告 -> PPT 的上下游链路，先以本地生成文件和 trace 为主，不急于做完整前端。
- [ ] **省级/市州级表族选择**：减少“问四川省却误走市州合计”的路径漂移。
- [ ] **2025-12 sparse 表专项**：区分真实缺值、只有排名列、需要业务 cohort 的情况，不在通用工具层硬补答案。
- [ ] **预收排名 reporting 冲突专项**：明确表内重算、空排名列和 reporting override 的优先级，避免把单个客户口径写进通用 filter/rank。
- [ ] **欠费台账专项**：处理多 sheet、多级表头、多指标、多单位口径，降低模型 openpyxl 漫游成本。
- [ ] **filter/multi-condition 工具增强**：多条件筛选、阈值、排名、数量统计稳定化。
- [ ] **per-case budget**：为 gold runner 增加最大耗时、最大工具调用、最大 token 保护，避免长尾 case 拖垮评测。
- [ ] **cached / non-cached 对照**：冷启动与热缓存分别跑 targeted set，量化 schema/cache/catalog 降本。
- [ ] **错误类型自动汇总**：按召回、字段定位、实体口径、排序方向、数值格式、输出缺项等标签生成 summary。
- [ ] **domain skill 精简**：让 skill 负责流程和口径提醒，数值仍由 table tools 读取，避免 skill 变成答案库。

## P2：中期路线

- [ ] **扩展评测集到 80-150 题**：覆盖 QA、编辑/修复/清洗、表格转换/合并、报表生成。
- [ ] **引入多行业表格**：避免只对四川财资过拟合，验证通用层可迁移。
- [ ] **可插拔 domain pack manager**：从固定 `sichuan-finance` 同步，演进为可选择挂载不同 domain pack，支持干净通用 workspace。
- [ ] **上传前端 / demo UI**：对齐 `workspace/uploads/`，前端只负责上传、展示 trace、展示图表和报告。
- [ ] **图表 artifact 评测**：在底层数据正确后，再评估图形渲染、排版和交互。
- [ ] **回滚 / diff / audit log**：面向真正表格编辑任务，记录修改前后差异和可回滚操作。
- [ ] **插件形态调研验证**：Excel/WPS/飞书等入口先保持设计研究，不急于工程实现。

## 文档维护 TODO

- [x] 清理早期半成品文档：skill-matrix、uploaded-table-workflow、workflow-routing、smoke summary、过长旧 run 报告。
- [x] 重写 docs 总览、实验评测索引、gold-cases 索引、runs 索引。
- [x] 精简开发日志与 TODO，保留当前上下文和下一步。
- [ ] 每次正式 benchmark 后，先在 `docs/实验评测/gold-cases/runs/` 归档带日期和语义的报告；滚动机器结果保留在 `eval_test/results/<dataset>/parallel/<run_group>/`，不要只依赖 latest 指针。
- [x] 每次 domain pack 更新后，同步更新 `docs/功能开发/domain-knowledge-migration.md` 和 `domain_packs/sichuan-finance/README.md`。
