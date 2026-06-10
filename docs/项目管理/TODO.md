# TableClaw TODO

> 用途：维护 TableClaw 的迭代计划与待办。完成项打勾不删，保留迭代轨迹。
>
> 分工说明：
> - 本文件只记 **要做什么 / 在做什么 / 做完打勾**。
> - 历史细节、决策原因、踩过的坑写到 [`development-log.md`](development-log.md)。
> - 完成一项时：本文件改 `- [ ]` → `- [x]`，并在 dev-log 里补一段说明，互相引用。
>
> 最后更新：2026-06-10

## 项目定位（不要忘）

TableClaw 是**表格专精 agent**，QA 只是其中之一。商用形态需要覆盖至少 4 类场景：

| 场景类 | 例子 |
| --- | --- |
| **QA / 分析** | 读表、按指标查询、筛选、排名、统计 |
| **编辑 / 修复 / 清洗** | 填公式、补数据、清重复行、修复类型、统一格式 |
| **表格转换 / 跨表合并** | CSV ↔ xlsx、多 sheet 拆合、纵转横、跨表 vlookup、多期合并 |
| **报表生成 / 从 0 建表** | 从多张表生成 dashboard / KPI 报表、含图表与条件格式；从零搭新业务表模型 |

设计每个 skill / tool / 评测题时，反复对照这 4 类，避免又退化回"只服务 QA"。

---

## 近 7 天进度

> 每周一扫一眼。`✅` 已完成、`🚧` 在做、`📅` 计划中。

- ✅ 整理目录结构与文档（回到主线 skill matrix）
- ✅ 修正项目定位 → **表格专精 agent**，覆盖 QA + 编辑 + 转换 + 报表 4 大场景
- ✅ 建立 TODO + dev-log 双文档分工
- ✅ git init + 修评分器
- ✅ 增加 6 个轻量 TableClaw workflow skills
- ✅ 扩展到 12-task eval（新增 2 个 workflow routing task）
- ✅ 跑 workflow skill-on/off 对照，观察多 skill sequence
- ✅ 清洗 `eval_test/eval_test.csv`，产出 165 条去重候选任务
- ✅ 把 uploaded-table workflow 接入 Nanobot 本体，10 tasks 跑通 retrieval tool + skill workflow
- ✅ schema cache / `tableclaw_inspect` v0 接入
- ✅ 导入人工 gold cases：40 条标准问答，默认全量评测
- ✅ gold cases 并行评测 runner：40 条 + DeepSeek LLM judge + numeric/entity F1
- ✅ 跑出 40 条 gold cases 第一版 baseline：ACC 40.00%，ranking 强、chart/trend/filter 弱
- ✅ 确认 cache 机制已进入主流程：retrieval 使用 schema index，inspect 读写 `workspace/table_cache/`，provider cached tokens 约 72.8%
- 🚧 下一版主线：column locator / series extractor / top-k / filter 已接入，正在跑 40-case 复测；下一步补 chart-data + Recall@k eval

---

## 下一版：v0.2 工具化闭环（当前优先级）

> 目标：不再让模型每题临时写大段 openpyxl 探索脚本，而是把高频表格操作沉淀成可复用 tool。优化后仍用 40 条 gold cases 复测，看 ACC、F1、token、耗时和 tool step 是否改善。

### P0：把 40-case 失败高频点工具化

- [x] **`tableclaw_locate_column`**：输入 `path + period + metric + scope/group`，返回精确 sheet、header row、column index、匹配证据。优先解决“月份/指标列找错”和多级表头问题。
- [x] **`tableclaw_extract_series`**：输入实体/指标/月份范围，返回 12 个月或指定区间的时序数据。优先解决 `trend_table` 0% 的问题。
- [x] **`tableclaw_topk`**：输入指标列、排序方向、k、排除合计行，返回排序结果和引用行列。优先巩固 `ranking_qa`，减少模型手写排序脚本。
- [x] **`tableclaw_filter`**：支持多条件 conjunction / threshold / range，返回命中行与数量。优先解决 `filter_qa` 0% 的问题。
- [ ] **`tableclaw_chart_data`**：先只生成图表底层数据 JSON，不评判图像美观。优先解决 chart tasks 里“图画出来但底层数据错”的问题。

### P0：让评测能证明优化有效

- [ ] **eval 记录 cache hit/miss**：从 `tableclaw_inspect` trace 中统计 `cache_hit=true/false`，写入 summary。
- [x] **eval 记录 TableClaw tool 调用**：gold 并行评测 summary 已统计各 `tableclaw_*` 工具覆盖 case 数。
- [ ] **eval 记录工具降本指标**：统计 `exec` 次数、`read_file(.xlsx)` 次数、cached tokens、elapsed，并与上一版 baseline 对比。
- [ ] **cached/non-cached 对照**：同一批 gold cases 跑冷启动和热缓存两版，对比 token、耗时、ACC。
- [ ] **错误类型自动汇总**：按 chart/ranking/trend/filter/table_qa 输出失败原因标签，避免只看总 ACC。

### P1：表格召回评估

- [ ] **gold table mapping**：给 40 条 gold cases 先标 `gold_table_id/table_path`（只给 evaluator，不进 prompt）。
- [ ] **Recall@k 评测**：评估 `tableclaw_retrieve_tables` 的 top1/top3/top5 命中率。
- [ ] **召回解释保存**：把每题 top-k 文件、score、reasons 写入结果，便于调 prompt/score。

### P1：Prompt / Skill 编排收敛

- [x] **改为宽松工具策略**：eval prompt 不再显式点名工具或强制流程，只提供上传目录、任务目标和输出约束，让 LLM 自主选择 skill/tool/code。
- [ ] **减少直接 `read_file` 读 xlsx**：优先通过 tool description / skill 文档自然引导，而不是在用户 prompt 中硬性规定流程。
- [ ] **技能选择与工具选择分工**：skill 负责“策略与流程”，tool 负责“确定性读算”，避免 skill 文档越来越像工具说明书。
- [ ] **保留 Codex xlsx skill 作为通用兜底**：下一版先不重写大 skill，优先验证工具化收益。

---

## 近期：本周完成（workflow 编排 + context 起步）

### 工程基线

- [x] **git init + 第一次 commit**：把当前整理后的状态作为基线。`.gitignore` 已就绪。
- [x] **修评分器（最小改动）**：`run_eval.py:_fact_matches` 里 `name=value`（value 是数字）改走 numeric tolerance；保留现有 evaluation 字段不变。已用脚本自测验证 `count=6` 不会误匹配 `16`。

### Workflow Skill v0

- [x] **新增轻量 table skills**：`table-read` / `table-clean` / `table-validate` / `table-report` / `table-formula-debug` / `table-chart`。
- [x] **skill-off 禁用全套 table skills**：`xlsx` + 6 个 TableClaw 轻量 skill，保证 ablation 干净。
- [x] **run_eval 记录 skill sequence**：除首个 skill step 外，报告完整 `skill_read_sequence`。
- [x] **新增 2 个 workflow task**：`tc_workflow_001` / `tc_workflow_002`，观察 read/clean/validate/report 的阶段选择。
- [x] **跑 workflow 对照**：`./eval.sh --case workflow`，记录 skill-on/off 的 skill sequence、token、耗时、正确性。
- [ ] **根据结果微调 skill description**：如果模型仍只读 `xlsx` 或完全不读 skill，优先改 description，不急着动 Nanobot 核心。

### Memory / Context / RAG v0

- [x] **写 schema cache RFC**：`docs/功能开发/table-schema-cache-rfc.md`，定义缓存 key、schema JSON、失效策略。
- [x] **实现 `workspace/table_cache/` schema cache**：缓存 sheet、行列数、候选表头、列 profile、样例行、merged ranges、mtime、size。
- [x] **schema cache 接入主流程**：`tableclaw_retrieve_tables` 用 schema index 做召回，`tableclaw_inspect` 复用/刷新 schema cache。
- [ ] **run_eval 加 cached/non-cached 对照**：同一 task 第二次运行优先使用 schema cache，观察 token 和耗时。
- [ ] **设计局部检索接口**：先关键词/列名检索，不急着接向量库。

### Raw Eval CSV / Retrieval Eval v0

- [x] **清洗 raw eval CSV**：`eval_test/eval_test.csv` -> `raw_eval_cleaned.jsonl` / `.csv` / 清洗报告。
- [x] **去重与标注**：835 raw rows -> 826 valid rows -> 165 dedup tasks；标注 `task_type`、facets、是否图表、是否适合当前数据表评测。
- [x] **图表任务边界标注**：144 条 chart tasks 保留，但标成 `requires_visual_artifact=true`，当前只评测底层数据表，不评测图形质量。
- [ ] **表格映射**：给 165 条 cleaned tasks 标注真实 `table_id` / `table_path`。
- [x] **导入人工 gold cases**：`测试case抽样.xlsx` -> `eval_test/test_dataset/gold_cases.jsonl`，当前 40 条，默认评测全量。
- [x] **gold cases judge 机制 v0**：`./eval_gold_parallel.sh` 并行跑 40 条，DeepSeek `deepseek-v4-pro` 做 LLM-as-judge，同时记录 numeric/entity F1。
- [x] **gold cases baseline v0**：8 并发跑完 40 条，ACC 40.00%，numeric F1 0.4131，entity F1 0.6004。
- [ ] **gold cases 人工复核字段**：对 LLM judge 的正确/错误样本抽查，沉淀人工核验状态，避免 judge 偏差变成最终结论。
- [x] **模拟用户上传 smoke**：把 `test_table/` 中 161 张可用表复制到 `workspace/uploads/`，保留 upload manifest。
- [x] **建立 table index v0**：抽取文件名、scope、subject、月份、前几行 preview 和 keyword，用于 top-k 召回。
- [x] **接入 Nanobot builtin retrieval tool**：`tableclaw_retrieve_tables` 从 `workspace/uploads/` / `workspace/table_index/` 召回候选表。
- [x] **统一 uploaded-table workflow eval**：通过 `./eval.sh --raw-cleaned --limit 10 --modes skill-on` 直接评测 Nanobot 主流程；删除独立 smoke runner。
- [x] **跑通 10 task workflow**：10/10 调用 retrieval tool，10/10 触发 skill read，报告写入 `docs/实验评测/uploaded-table-workflow/latest-eval-summary.md`。
- [ ] **正式 retrieval eval**：补 gold table mapping，评估 Recall@k、答案质量、耗时和 token。
- [x] **索引升级到 schema/RAG v0**：从文件级 preview 扩展到 sheet/列名/样例值级 index，减少全表搜索。
- [x] **沉淀表格 inspect 工具**：`tableclaw_inspect` 已接入，先返回 sheet、header candidates、columns、sample rows。
- [ ] **沉淀表格定位/计算工具**：继续做 `tableclaw_locate_column`、`tableclaw_extract_series`、`tableclaw_topk`，降低反复写 openpyxl 脚本的 token。
- [ ] **限制 `.xlsx` 直接 read_file 误用**：在 prompt/skill/tool 描述里引导模型先用 inspect/exec/tool，不把二进制表当纯文本读。
- [ ] **拆分图表评测**：先做 chart underlying data correctness，再补 visual artifact evaluator。

### Native xlsx Skill v0（暂缓但保留）

- [ ] **codex 原文备份到 `_archive/`**：`nanobot/nanobot/skills/_archive/codex-spreadsheets-original.md`，保留 1068 行原文不丢。
- [ ] **重写 `nanobot/nanobot/skills/xlsx/SKILL.md`**：≤200 行的 TableClaw native skill v0，作为宽能力入口；当前先用轻量分阶段 skills 探索编排。
- [ ] **跑 native skill vs codex 对照评测**：`./eval.sh` 全量 12 任务 × skill-on/off。

---

## 中期：1–2 周（覆盖 4 大场景的实验体系）

### Eval Dataset 规模化（核心阻塞项）

**目标**：从现在 12 题主线任务扩到 **80–150 题学术 benchmark 级**，覆盖 4 大场景 × 三档难度，能发 paper / 写技术报告 / 给客户看说服力。后续所有 skill 与 tool 的边际效果证明都依赖这套 dataset。

**规模分配（初拟，可调）**：

| 场景 | 题数 | simple | medium | hard |
| --- | ---: | ---: | ---: | ---: |
| QA / 分析 | 30–40 | 10–13 | 10–13 | 10–14 |
| 编辑 / 修复 / 清洗 | 20–30 | 7–10 | 7–10 | 6–10 |
| 表格转换 / 跨表合并 | 15–25 | 5–8 | 5–8 | 5–9 |
| 报表生成 / 从 0 建表 | 15–25 | 5–8 | 5–8 | 5–9 |
| **合计** | **80–120** | | | |

**难度二维（运算复杂度 × 表结构复杂度）**：

- 运算复杂度：simple（单步查询）/ medium（双步骤组合）/ hard（多步推理、跨期、聚合 + 排序）
- 表结构复杂度：flat（单 sheet、单层表头）/ nested（多级表头、merged cell）/ multi（多 sheet、跨表）
- 任务 `evaluation.complexity` 同时打两个维度的标签，方便后续做矩阵分析

**数据来源（混合策略）**：

- [ ] **来源 A — 现有 `test_table/`**：四川经营数据系列，估 20–30 题（多样性弱但 gold 容易核实）
- [ ] **来源 B — 公开 spreadsheet benchmark**：评估并部分引入
  - SpreadsheetBench（GitHub microsoft/...）
  - WikiTableQuestions
  - TabFact
  - FeTaQA
  - 估 30–50 题，注意 license 兼容
- [ ] **来源 C — 同学/朋友贡献真实业务表**：覆盖更多行业（财务/HR/营销/运营），估 20–30 题
  - 隐私清洗：删公司名、人名、ID 等敏感字段
  - 给同学发标准 jsonl 模板 + README，统一字段
- [ ] **来源 D — 合成**（兜底）：从公开数据集生成边界 case（极端值、空行、重复行、超大表），估 5–10 题

**协作方式（要找同学帮忙）**：

- [ ] 建一个 `eval_test/test_dataset/contributions/` 子目录，每人一个 jsonl 文件
- [ ] 写 `eval_test/test_dataset/CONTRIBUTING.md`：jsonl 字段说明、gold answer 核实流程、提交方式
- [ ] 一题一 GitHub issue 模板（如果项目托管），用 label 区分场景/难度/状态
- [ ] 每周一次 batch review，合入主 dataset

**Gold answer 流程**：

- [ ] 模型先答 + 提出题者人工核验
- [ ] hard 题至少二人交叉核验
- [ ] 数值用 tolerance（1e-6 或题目自定），文本用 fact match + LLM-as-judge 兜底（可选）

**Checkbox（前置决策完成后逐步展开）**：

- [ ] 写 `eval_test/test_dataset/CONTRIBUTING.md` 投稿规范
- [ ] 写 `eval_test/test_dataset/SCHEMA.md` 任务 jsonl 字段标准（含 complexity 二维标签、4 场景枚举）
- [ ] 评估 5 个公开 benchmark 的可引入性 + license，挑 2–3 个
- [ ] 招募 3–5 名同学，每人认领 10–20 题
- [ ] 写公开 benchmark 引入脚本（格式转换到 TableClaw jsonl schema）
- [ ] 扩 `run_eval.py` 支持非 QA 任务的判分：
  - [ ] 输出文件 sha 对比
  - [ ] 输出 cell 值 / 公式正确性比对
  - [ ] 行数列数维度比对
  - [ ] 公式错误扫描（#REF!/#DIV/0! 等）
- [ ] 跑通 baseline：在新 dataset 上跑当前 workflow skill v0，建立基线分

### 表格专用 Tool 系列（动 nanobot 本体，已许可）

**目标**：把模型反复在 exec 里写的 openpyxl 套路沉淀成 nanobot tools，让模型一次调用就拿结果，减少试错、降 token、稳定性翻倍。**接入位置**：`nanobot/nanobot/agent/tools/tableclaw/<name>.py`（建子目录避免污染上游 tool 文件夹）。

**命名规范**：

- 全部 `tableclaw_<动词>` 或 `tableclaw_<动词>_<对象>` 形式，snake_case
- 动词在前，对象明确，不重复 `table` 前缀
- 入参第一位永远是 `path`（表文件路径），其余按重要性排序
- 返回 dict 或 dataclass，包含 `data` + `meta`（含执行 sha、耗时、warnings）
- 失败抛 `TableclawError` 含详细原因，不让模型猜

**第一批 5 个 tool（按依赖顺序）**：

- [x] `tableclaw_inspect(path, sheet=None)` — 返回 sheet 列表 / rows / cols / merge 范围 / 多级表头 / total 行 / blank 行
- [x] `tableclaw_locate_column(path, period, group, metric, sheet=None)` — 三元组定位列，处理 merged header；返回 column index + 上下文片段
- [x] `tableclaw_extract_series(path, entity, metric, period_start, period_end, sheet=None)` — 跨月/跨期抽取序列，返回每期值与引用行列
- [x] `tableclaw_topk(path, value_col, k=10, ascending=False, sheet=None, row_filter=None)` — Top/Bottom-K 排名，含 tie 处理与多列 tie-breaker
- [x] `tableclaw_filter(path, conditions, sheet=None)` — 阈值/范围/跨期 conjunction 过滤，conditions 是 list of {col, op, value}
- [ ] `tableclaw_chart_data(path, spec, sheet=None)` — 为图表任务抽取结构化底层数据，图形渲染另做

**Tool RFC（先文档后代码）**：

- [ ] 写 `docs/功能开发/tableclaw-tools-rfc.md`：每个 tool 的签名、入参、返回、错误码、典型用例。先 RFC 评审再写代码。
- [ ] 在 RFC 文档里和 nanobot `agent/tools/base.py` 的接口规范对齐

**验证三道关**（每个 tool 都要过）：

- [ ] **单元测试**：`nanobot/nanobot/agent/tools/tableclaw/tests/test_<name>.py`，覆盖：
  - 有/无 merge
  - 多 sheet / 单 sheet
  - 边界数据（空表、单行、全 None 列）
  - 类型异常（字符串混入数字列）
  - 大文件（300+ 列、200+ 行）
- [ ] **集成测试**：在现有 dataset（先 12 题，扩充后再跑全量）上跑，记录每个 tool 的：
  - 触发次数
  - 节省的 exec 步数
  - token 降幅
- [ ] **A/B 对比**：让模型 prompt 里看到 tool vs 看到等价的 SKILL.md，跑对照。要看到 tool 形态稳定胜出才合格。

**第一批跑通后再扩**（候选，按需）：

- `tableclaw_diff` — 跨期/跨表差异，输出 added/removed/changed
- `tableclaw_aggregate` — 按某列分组聚合，支持 sum/mean/max/min/count
- `tableclaw_pivot` — 纵转横、宽表 ↔ 长表
- `tableclaw_write_cell` / `tableclaw_write_formula` — 写入操作
- `tableclaw_validate` — 公式错误扫描
- `tableclaw_render_preview` — 渲染成图/HTML 供 verify pass

### 多家 Skill 横评（决定 TableClaw skill 路线）

**目标**：诚实测出 codex / kimi / anthropic / claude-code / TableClaw 自研在**同一任务集**上的边际效果，决定 skill 路线（继续优化自研、还是基于某家底改）。

**参评 skill（带依赖跑，真实路径）**：

- [ ] codex spreadsheets skill — 现有 `skills/codex/SKILL.md` 1068 行。需要：node + `@oai/artifact-tool`
- [ ] kimi xlsx skill — 现有 `skills/kimi_xlsx_skill/`。需要：python + pandas + openpyxl + `KimiXlsx` Linux ELF 二进制 → **docker 容器隔离**跑
- [ ] anthropic xlsx skill — 现有 `skills/anthropic_xlsx_skill/`。需要：python + openpyxl + pandas + LibreOffice + `scripts/recalc.py` + `scripts/office/` helpers（之前裁剪过，要补回）
- [ ] claude-code 自带 spreadsheet skill — 需要先弄到原文（从 claude.ai 安装包或在线版抓取）
- [ ] TableClaw 自研 v0 — 当前 `nanobot/nanobot/skills/xlsx/SKILL.md`（rewrite 后）
- [ ] （可选）copilot for excel 风格 skill — 如果能搞到 prompt 原文

**依赖隔离方案**：

- [ ] 每家做一份 `docker-compose.<vendor>.yml`，跑 multi-skill harness 时拉对应 image
- [ ] kimi 的 `KimiXlsx` 路径写死 `/app/.kimi/...` 在 docker 里可以模拟
- [ ] anthropic 的 `scripts/office/` helper 从原仓库或社区找回，docker image 装 LibreOffice
- [ ] 不可用时**明确报失败**，**不降级**，避免数据失真

**Harness 改造**：

- [ ] `eval_test/run_multi_skill.py`：接受 skill 集合参数，对每家分别跑一遍同一 dataset
- [ ] 配置形式：`nanobot/configs/tableclaw-multiskill-<vendor>.json`，每家一份 disabledSkills + 依赖检查
- [ ] 输出：`eval_test/results/multi_skill/<vendor>/run.json`，统一格式方便横比
- [ ] 报告生成器：`docs/实验评测/multi-skill/comparison.md`，矩阵表（vendor × 场景 × 难度 × 指标）

**评测维度**：

- token（total / prompt / completion / cached）
- 正确率（auto pass + 人工核验）
- skill 读取率（这家 skill 真的被模型读到了几次）
- 步数（tool steps）
- 答案精度（数值小数位、文本完整性）
- **鲁棒性**：每题跑 N 次（建议 N=3 或 5），取分布而不是单次结果

**Checkbox**：

- [ ] 写 RFC：`docs/功能开发/multi-skill-eval-rfc.md`，定 harness 接口、依赖隔离、指标定义
- [ ] 给每家做依赖 dockerfile（5 份）
- [ ] claude-code skill 原文获取（待你确认渠道）
- [ ] `run_multi_skill.py` 实现 + multi-seed 跑
- [ ] 横评报告（先在 12 题上跑通，dataset 扩到 80+ 后再跑大版本）
- [ ] 写 `docs/实验评测/multi-skill/decision.md`：基于横评结果决定 TableClaw skill 路线（自研继续优化 / 基于某家底改 / 多家组合）

### Skill 拆分（等路线对齐后启动）

- [ ] **依据反馈 + 横评结果，把 v0 入口 skill 拆成多个子 skill**，可能形态：
  - `tableclaw-table-qa`
  - `tableclaw-table-edit`
  - `tableclaw-table-transform`
  - `tableclaw-table-report`
- [ ] **建立 skill 选择实验**：每个子 skill 单独 disable 测试边际贡献。

---

## 长期：1–2 个月（产品原型走向商用）

### 模型 / 部署

- [ ] **多模型适配**：除 dashscope/deepseek 外至少跑通：
  - [ ] anthropic 一份 config（claude-sonnet/opus）
  - [ ] openai 一份 config（gpt-4 / gpt-4o）
- [ ] **本地小模型可选项**：是否要在 ollama / llama.cpp 上跑通一份，覆盖隐私敏感场景。

### 对外接口

- [ ] **OpenAI 兼容 HTTP API 启用**：nanobot 自带 `/v1/chat/completions`，需要测一遍 + 写示例调用文档。
- [ ] **WebUI 演示页**：选其一
  - [ ] 启用 nanobot 自带 webui（gateway）
  - [ ] 独立小页面读 `eval_test/results/` 做 timeline + token 可视化

### 安全 / 上线

- [ ] **API key 治理**：当前按项目验证需要保留本地默认 key；生产化前再把 `start.sh` / `eval.sh` / `run_eval.py` 的默认 key 迁移到 env / .env。
- [ ] **配置鉴权**：对外 API 加最简 token / IP 白名单。
- [ ] **打包发布**：决定是 docker image 还是 pip 包，写 README + 一键部署脚本。

### 文档化

- [ ] **写 TableClaw README.md**（项目根，目前只有 nanobot 的 README）：定位、4 大场景、quick start、架构图。
- [ ] **重画 skill pipeline svg**：之前删过的 `tableclaw-skill-pipeline.svg`、`tableclaw-xlsx-case-flow.svg` 后续要补回，对应商用版能力。

---

## 已完成

> 完成项移到这里，不删。日期格式 `YYYY-MM-DD`。

### 2026-05-28
- [x] 跑通 nanobot + 百炼 dashscope 配置 — 见 dev-log
- [x] 一键启动脚本 `start.sh`
- [x] workspace 迁到项目内 `workspace/`
- [x] 搭第一版 `eval_test/test_dataset/`（2 任务 smoke）
- [x] 接 codex xlsx skill 作为最小可演示 skill 选择机制
- [x] Token usage 运行时持久化（`workspace/usage/usage.jsonl`）

### 2026-05-29
- [x] 整理 `docs/` 文档结构（架构 / 功能开发 / 实验评测 / 项目管理）
- [x] 把 codex skill 接入 nanobot builtin
- [x] 增加 skill selection trace + 10 任务统一 eval（`run_eval.py`、`./eval.sh`）
- [x] 写参考 spreadsheet skills 分析（`reference-spreadsheet-skills.md`）
- [x] 删除临时展示分支，回到 10-task skill matrix 主线
- [x] 删除 `trace_skill_selection_matrix.py` wrapper、加 `.gitignore`
- [x] 清空 workspace 运行态（保留 USER/SOUL/AGENTS/HEARTBEAT/MEMORY 模板）
- [x] 同步 docs/README、docs/架构、docs/功能开发、docs/项目管理 全部到新结构
- [x] 修正定位：TableClaw 是**表格专精 agent**，覆盖 QA + 编辑 + 转换 + 报表 4 大场景
- [x] 建立 TODO + dev-log 双文档分工
- [x] 初始化 Git 仓库并推送到 GitHub
- [x] 修正 `run_eval.py` 数字事实匹配逻辑

### 2026-06-06
- [x] 写 TableClaw 定位与 workflow 设计文档（产品调研 / 能力边界 / memory-context-RAG / harness）
- [x] 新增 6 个 TableClaw 轻量 workflow skills
- [x] 扩展 `run_eval.py` 追踪多 skill sequence
- [x] 将 skill-off 配置扩展为禁用 `xlsx` + 全部 TableClaw table skills
- [x] 新增 2 个 workflow routing tasks，数据集从 10 题扩到 12 题
- [x] 新增 `docs/实验评测/workflow-routing.md`
- [x] 跑通 `./eval.sh --case workflow`，观察到 skill-on 首步命中 `table-read`，报告任务命中 `table-read -> table-clean`
- [x] 清洗 `eval_test/eval_test.csv`，生成 165 条候选 retrieval/eval tasks，并记录 144 条图表任务的评测边界

### 2026-06-08
- [x] 把 workspace 上传表召回接入 Nanobot builtin tool：`tableclaw_retrieve_tables`
- [x] 删除独立 uploaded-table 冒烟脚本，统一到 `./eval.sh --raw-cleaned --limit 10 --modes skill-on`
- [x] 跑通 10 条 uploaded-table workflow eval，记录 retrieval tool、skill sequence、token、耗时和答案预览

### 2026-06-10
- [x] 新增 `tableclaw_inspect`，生成/读取 `workspace/table_cache/*.schema.json`
- [x] 将 `tableclaw_retrieve_tables` 升级为 schema-based retrieval v0，召回信号扩展到 sheet/header/column/sample
- [x] `run_eval.py --raw-cleaned` prompt 已要求 retrieve 后先 inspect，再分析表格
- [x] 导入 `测试case抽样.xlsx` 为 `gold_cases.jsonl`，新增 `./eval.sh --gold-cases` 入口
- [x] 新增 `./eval_gold_parallel.sh`，8 并发跑完 40 条 gold cases，并记录 DeepSeek LLM judge、numeric/entity F1、trace/token
- [x] 文档确认当前 cache 使用状态：161 个 schema cache，retrieval/inspect 均进入主流程，provider cached tokens 在 40-case baseline 中占约 72.8%
- [x] 新增 4 个 TableClaw 确定性读算工具：`tableclaw_locate_column`、`tableclaw_extract_series`、`tableclaw_topk`、`tableclaw_filter`
- [x] 更新 gold 并行评测报告，统计 TableClaw tool 覆盖 case 数

---

## 维护规则

- 新 TODO 加在对应时间段（近期 / 中期 / 长期）下、合适的主题分组里。
- 完成一项：复选框打勾、日期写完成日、移到"已完成"段落。
- 计划变更：删除 TODO 时在 dev-log 里说明原因，避免 TODO 静悄悄消失。
- 时间段不是死的：近期可以跨周，但每周扫一眼"近 7 天进度"小节做节奏校准。
