# TableClaw TODO

> 最后更新：2026-06-13
>
> 本文件只维护当前和下一阶段待办。旧版流水账已从主线文档中清理，必要时从 git 历史恢复。

## 当前开发原则

```text
通用探索能力兜底
+ 稳定工具加速高频路径
+ skill/memory 承接半结构化经验
+ 评测闭环决定什么该固化、什么该保持开放
```

分层边界：

- Nanobot framework：尽量不为单一业务场景改主循环。
- Generic TableClaw tools：召回、inspect、schema/cache、catalog、matrix、time-series、rank、filter 等保持领域无关。
- Domain pack：四川财资业务口径、表族映射、固定 cohort、ranking policy、badcase 经验放在 `domain_packs/sichuan-finance/`。
- Eval：决定经验进入通用工具、domain pack，还是保持开放探索。

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
- [x] 当前 DeepSeek 历史最高 full40 归档：80.00% ACC。
- [x] GPT-5.5 full40 归档：82.50% ACC，作为强基模上限和轨迹参考。
- [x] 四川财资 domain pack：知识 JSON + workspace skill + `tableclaw_domain_knowledge`。
- [x] 文档主线清理：移除早期 smoke/mentor/skill-matrix 过期文档，保留 gold benchmark 主线。
- [x] `200亿省` 当前 gold/reporting cohort 修正为 7 省，并让 `extract_matrix` 可从 domain pack 自动展开 cohort。
- [x] DeepSeek after-cohort-fix full40 @4：平均 ACC 82.50%，证明 domain pack + tool cohort 路线有效。

## P0：下一轮必须做

- [ ] **处理新 badcase 文件**：读取 `eval_test/300条badcase.xlsx`，清洗成可追踪的 badcase 数据集。
- [ ] **badcase 三分流**：每条错例标注为 `generic-tool` / `domain-knowledge` / `prompt-or-eval`，避免把业务知识写死到通用工具。
- [x] **Domain pack targeted eval v0**：case 5/19/20/22/29/40 小样本验证，cohort 修正后 19/22/29/40 有改善；case5 暴露 2025-12 sparse 短板。
- [ ] **Domain pack targeted eval v1**：扩展到 10-20 条四川财资业务 case，验证 `tableclaw_domain_knowledge` 是否稳定触发并改善答案。
- [x] **DeepSeek full40 复测**：after-cohort-fix @4 平均 ACC 82.50%，已超过 80.00% 历史归档 run。
- [ ] **filter_qa 专项**：当前 @4 只有 37.50%，优先增强多条件筛选、cohort 内筛选、缺值/排名列共存判断。
- [ ] **召回评估 gold mapping**：给 40 条 gold cases 补 `gold_table_id/table_path`，只给 evaluator，不进 prompt。
- [ ] **Recall@k 指标**：统计 `tableclaw_retrieve_tables` top1/top3/top5 是否命中 gold table。
- [ ] **工具一致性检查**：确认评测统计中的 `tableclaw_horizontal_series` 与当前代码实现一致；若工具已合并/改名，更新统计和文档。
- [ ] **领域知识版本号**：为 `domain_packs/sichuan-finance/knowledge/tableclaw_industrial_finance.json` 增加更新记录和 badcase 来源。

## P1：短期增强

- [ ] **省级/市州级表族选择**：减少“问四川省却误走市州合计”的路径漂移。
- [ ] **2025-12 sparse 表专项**：区分真实缺值、只有排名列、需要业务 cohort 的情况，不在通用工具层硬补答案。
- [ ] **欠费台账专项**：处理多 sheet、多级表头、多指标、多单位口径，降低模型 openpyxl 漫游成本。
- [ ] **filter/multi-condition 工具增强**：多条件筛选、阈值、排名、数量统计稳定化。
- [ ] **per-case budget**：为 gold runner 增加最大耗时、最大工具调用、最大 token 保护，避免长尾 case 拖垮评测。
- [ ] **cached / non-cached 对照**：冷启动与热缓存分别跑 targeted set，量化 schema/cache/catalog 降本。
- [ ] **错误类型自动汇总**：按召回、字段定位、实体口径、排序方向、数值格式、输出缺项等标签生成 summary。
- [ ] **domain skill 精简**：让 skill 负责流程和口径提醒，数值仍由 table tools 读取，避免 skill 变成答案库。

## P2：中期路线

- [ ] **扩展评测集到 80-150 题**：覆盖 QA、编辑/修复/清洗、表格转换/合并、报表生成。
- [ ] **引入多行业表格**：避免只对四川财资过拟合，验证通用层可迁移。
- [ ] **上传前端 / demo UI**：对齐 `workspace/uploads/`，前端只负责上传、展示 trace、展示图表和报告。
- [ ] **图表 artifact 评测**：在底层数据正确后，再评估图形渲染、排版和交互。
- [ ] **回滚 / diff / audit log**：面向真正表格编辑任务，记录修改前后差异和可回滚操作。
- [ ] **插件形态调研验证**：Excel/WPS/飞书等入口先保持设计研究，不急于工程实现。

## 文档维护 TODO

- [x] 清理早期半成品文档：skill-matrix、uploaded-table-workflow、workflow-routing、smoke summary、过长旧 run 报告。
- [x] 重写 docs 总览、实验评测索引、gold-cases 索引、runs 索引。
- [x] 精简开发日志与 TODO，保留当前上下文和下一步。
- [ ] 每次正式 full40 后，先在 `docs/实验评测/gold-cases/runs/` 归档带日期和语义的报告，再更新 `latest-parallel-eval-summary.md` 指针。
- [ ] 每次 domain pack 更新后，同步更新 `docs/功能开发/domain-knowledge-migration.md` 和 `domain_packs/sichuan-finance/README.md`。
