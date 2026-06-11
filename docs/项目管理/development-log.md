# TableClaw 开发日志

> 用途：记录 TableClaw 二次开发过程中的关键决策、配置、验证结果和待办，方便后续切换模型、切换上下文或继续开发时快速恢复现场。

---

## 2026-06-11

### Rank Tool 与 Case001 对比实验

背景：case001 中，四川省 2024 年 3 月应收占收比排名需要先处理表内百分比混合编码。表中同一占比类字段同时存在 `0.0902`（业务含义 9.02%）和 `7.33`（业务含义 7.33%）。如果直接按原始数值排序，会把四川排名算错。

新增/修改：

- `nanobot/nanobot/agent/tools/tableclaw.py`
  - 新增/接入 `tableclaw_rank`。
  - 支持实体排名、从低到高/从高到低排序、cohort 排名。
  - 对占比/比率/率等百分比语义指标执行归一化：`0 < abs(value) <= 1` 时按 `value * 100` 参与排序。
  - 支持通过 `cohort_metric` 和阈值识别 `200亿省` 这类子集。
- `eval_test/run_eval.py`
  - 将 `tableclaw_rank` 纳入 TableClaw 工具调用统计。

case001 单条验证：

- 早期失败基线：找对表和四川数值，但用原始数值排序，导致应收占收比全国/200亿省排名、产数应收占收比全国/200亿省排名错误。
- 当前 TableClaw 复测：correct，耗时 102.777s，token 210,649。
- 当前 TeleClaw 冷启动复测：correct，耗时 582.0s，token 787,930。
- 对比报告：`docs/实验评测/gold-cases/runs/2026-06-11-case001-tableclaw-teleclaw-comparison.md`。

关键观察：

- TeleClaw 路径主要是强基模自主探索：读取目录，使用 pandas/openpyxl，检查排名列、number_format、公式，并自行归一化排序。
- TableClaw 路径是工具化执行：模型识别“抽值 + 排名 + cohort 排名”意图后，由 `tableclaw_rank` 处理百分比归一化、排序和 200亿省重排。
- 这不是单纯基模能力或单纯工具能力问题，而是 trade-off：临场探索适应未知问题，稳定工具降低高频路径成本。

沉淀到项目 README 的核心开发思想：

```text
通用探索能力兜底
+
稳定工具加速高频路径
+
skill/memory 承接半结构化经验
+
评测闭环决定什么该固化、什么该保持开放
```

### Rank Tool Full40 Benchmark

运行：

```bash
./eval_gold_parallel.sh --concurrency 4
```

报告：

- `docs/实验评测/gold-cases/runs/2026-06-11-v6-rank-tool-full40.md`
- `eval_test/results/gold_cases/parallel/runs/2026-06-11-v6-rank-tool-full40_summary.json`
- `eval_test/results/gold_cases/parallel/runs/2026-06-11-v6-rank-tool-full40_results.jsonl`

结果：

- 总数：40。
- ACC：45.00%（18 correct / 10 partial / 12 incorrect）。
- Avg judge score：0.5800。
- Numeric F1：0.4232。
- Entity F1：0.6649。
- Avg elapsed：201.53s / case。
- Total answer tokens：16,970,759。
- Retrieval tool call rate：100.00%。
- Inspect tool call rate：90.00%。
- Skill selection rate：5.00%。

按任务类型：

- `ranking_qa`：11 条，ACC 81.82%，仍是最强项。
- `chart_generation`：22 条，ACC 31.82%，仍是主要短板。
- `filter_qa`：2 条，ACC 0.00%，多条件筛选和口径判断仍不稳。
- `table_qa`：3 条，ACC 33.33%。
- `trend_table`：2 条，ACC 50.00%。

TableClaw 工具调用：

- `tableclaw_retrieve_tables`：40 cases。
- `tableclaw_inspect`：36 cases。
- `tableclaw_locate_column`：16 cases。
- `tableclaw_extract_series`：11 cases。
- `tableclaw_topk`：8 cases。
- `tableclaw_rank`：11 cases。
- `tableclaw_filter`：12 cases。
- `tableclaw_catalog_tables`：1 case。

相对上一轮 structured retrieval：

- ACC 从 52.50% 回落到 45.00%。
- 平均耗时从 265.26s 降到 201.53s。
- ranking_qa 保持 81.82%，case001 已修复。
- 回归主要来自 chart/filter/table 内结构理解：例如 200亿省口径误判、2025年12月表内缺失/合并/排名列处理、图表底层数据范围不稳。

结论：

- `tableclaw_rank` 对 case001 这类“百分比归一化 + cohort 排名”问题有效，但 rank 工具不是万能解。
- 后续不应继续把单点规则硬塞进工具，而要保留通用探索兜底，并加强 skill/memory 与评测闭环。
- 下一步优先方向：
  1. `chart_data` 工具：先稳定输出图表底层数据表，再谈图像呈现。
  2. `filter` 口径校验：避免多条件筛选时误读 cohort 和指标方向。
  3. 表内结构 grounding：识别真实数据行、排除汇总行、处理合并单元格/空值/隐藏排名列。
  4. per-case budget：控制长尾探索，同时让模型在证据足够时尽快作答。
  5. memory/case bank：将失败样本沉淀为可检索经验，而不是只靠 prompt 或写死工具。

### Rank Tool Minimal Normalize Ablation

full40 结果说明 `tableclaw_rank` 对 case001 有效，但补丁可能偏强。为避免把多个变量混在一起，本轮收窄为最小可解释改动：`tableclaw_rank` 仍然只负责重算排序，唯一新增能力是对百分比/占比类指标做混合编码归一化。

保留：

- `tableclaw_rank` 会定位指标列、实体列和可选 cohort 列。
- 排序前通过 `_normalize_metric_number` 统一百分比量纲：
  - `0.0902 -> 9.02%`
  - `0.31 -> 31.00%`
  - `7.33 -> 7.33%`
  - `23.51 -> 23.51%`
- `tableclaw_topk` / `tableclaw_filter` 也复用同一归一化 helper。

暂不加入：

- 不读取或覆盖表内官方排名列。
- 不加入 `rank_source`、`official_rank`、`computed_rank` 对照。
- 不加入 cohort reliable warning。
- 不改变 `tableclaw_retrieve_tables` 对 rank/topk 的原有提示。
- 不处理 `200亿省` domain glossary；该问题后续单独做 domain knowledge 层。

点测重点：

- `2024年03月 + 应收占收比 + 四川 + 200亿省`：验证 case001 混合百分比归一化仍能得到四川总体第 1、200亿省第 1。
- 后续再跑小集合/全量评测，观察单独加入 normalize 是否能修 case001，同时减少对其他题目的额外干扰。

验证：

- `python3 -m py_compile nanobot/nanobot/agent/tools/tableclaw.py eval_test/run_eval.py` 通过。

## 2026-06-10

### Structured Retrieval Router v5

目标：在不把 `200亿省`、具体省份名单等业务规则硬编码进 prompt/core 的前提下，让召回先理解用户问题的结构，再做候选表过滤和排序。

新增/修改：

- `nanobot/nanobot/agent/tools/tableclaw.py`
  - `tableclaw_retrieve_tables` 输出版本升级为 `v5-structured-intent`。
  - 新增 query intent 解析：月份/年份、时间范围、粒度范围、省级/市州级 scope、指标族、任务类型、cohort term。
  - 新增 constraint score：对 period/scope/metric/task type 做确定性加减分，并在候选里返回 `fit` 与 `risks`，让模型知道“为什么像/哪里危险”。
  - 新增 table group discovery：对同模板月度表做分组，支撑趋势、全年、最近几个月这类多表问题。
  - 保留 catalog description 作为 rerank/解释信号，但不让 description 替代回源表证据。
- `scripts/run_v5_gold_eval.sh`
  - 复用现有 161 张表 catalog，不重建 LLM description。
  - 固定 run id：`2026-06-10-v5-structured-retrieval`。

本地验证：

- `py_compile` 通过：`nanobot/nanobot/agent/tools/tableclaw.py`。
- smoke：
  - 省级 2025年5月问题 top1 命中 `全国各省份数据-通报应收总额_202505.xlsx`，市州表出现 `scope_mismatch` 风险。
  - 南充 2024年1月预收问题 top1 命中 `市州数据-市州应收账款情况表_202401.xlsx`。
  - 省级趋势问题优先返回 `全国各省份数据-通报应收总额` 表组。
  - 小微 ICT 欠费趋势优先返回 `市州数据-欠费数据_台账.xlsx` 表组。

40-case benchmark：

- 报告：`docs/实验评测/gold-cases/runs/2026-06-10-v5-structured-retrieval.md`
- 完整结果：
  - 主 run 结果：`eval_test/results/gold_cases/parallel/runs/2026-06-10-v5-structured-retrieval_results.jsonl`（39 条）
  - case21 单独重跑：`eval_test/results/gold_cases/parallel/case21_rerun/runs/2026-06-11-v5-case021-rerun-1_results.jsonl`
  - 合并结果：`eval_test/results/gold_cases/parallel/runs/2026-06-10-v5-structured-retrieval-combined_results.jsonl`
  - 合并 summary：`eval_test/results/gold_cases/parallel/runs/2026-06-10-v5-structured-retrieval-combined_summary.json`

结果：

- ACC：52.50%（21 correct / 8 partial / 11 incorrect），相对 v4 的 47.50% 提升 5 个点。
- Avg judge score：0.6250，相对 v4 的 0.5625 提升。
- Numeric F1：0.4164，低于 v4 的 0.4303，说明召回变稳不等于数值抽取已稳。
- Entity F1：0.6712，略高于 v4 的 0.6667。
- Avg elapsed：265.26s/case，高于 v4，说明长尾探索仍严重。
- by task type：
  - chart_generation：40.91%。
  - ranking_qa：72.73%。
  - table_qa：100.00%。
  - trend_table：50.00%。
  - filter_qa：0.00%。

重要现象：

- case 002 / 004 / 008 / 014 / 032 等较 v4 明显受益，说明 period/scope/metric group 和 table group 对“选对表/选对月/跨月”有效。
- case 021 主并发 run 卡住未落盘；单独重跑 3 分钟完成，但判 incorrect。错误不是召回，而是把 `南方省/北方省` 汇总行当成候选，并漏掉广东、江苏、浙江、上海、安徽、湖南等真实省份。
- case 031 同样是 2025年12月省级图表题，模型声称多数省份数据缺失，只给出四川，暴露 clean view / merged cell / hidden value / summary row 处理不足。
- case 040 从 v4 correct 退化为 incorrect，说明结构化召回不保证最终组合筛选/排名逻辑正确，需要 `chart_data` / `filter` 类确定性执行工具兜底。

结论：

- 这轮优化仍然是通用方向：结构化 intent、约束打分、table groups 都是表格任务通用能力，不是把某个业务规则写死。
- 下一步优先补 per-case timeout / max tool calls，避免单个 case 卡死全量评测。
- 召回之后的核心短板已经转向“表内 grounding”：如何稳定识别真实数据行、排除汇总行、处理 2025年12月这类疑似合并/空值/布局异常表，并直接输出 chart/filter 所需的底层数据 JSON。

### Table Catalog Layer v0

目标：把上传表从“只靠文件名/schema preview 临时召回”推进到“上传后生成可复用 table description”，让 TableClaw 在长对话里先知道每张表大概记录什么、适合回答什么问题，再进入 inspect/计算。

新增/修改：

- `nanobot/nanobot/agent/tools/tableclaw.py`
  - 新增 `tableclaw_catalog_tables(rebuild_catalog=False, describe_with_llm=True, model=deepseek-v4-pro, limit=None)`。
  - 新增运行态目录 `workspace/table_catalog/`：
    - `catalog.jsonl`
    - `profiles/*.profile.json`
    - `clean_views/*.clean_view.json`
    - `descriptions/*.description.json`
  - profile / clean view 由现有 schema cache 确定性生成，不修改源表。
  - description 优先调用 DashScope OpenAI-compatible API 的 `deepseek-v4-pro`；若未配置 `DASHSCOPE_API_KEY` 或 API 失败，安全降级为 deterministic fallback。
  - `tableclaw_retrieve_tables` 现在会自动合并 `workspace/table_catalog/catalog.jsonl`，把 `short_description / what_it_records / row_grain / important_metrics / can_answer / data_quality_notes` 纳入召回文本，并在候选结果里返回 description/profile/clean view 路径。
- `eval_test/run_eval.py`
  - 将 `tableclaw_catalog_tables` 纳入 `TRACKED_TABLECLAW_TOOLS`，后续评测能统计 catalog 工具调用。
- `docs/功能开发/table-catalog-layer-rfc.md`
  - 新增 RFC，明确 Catalog 是导航和规划上下文，不是最终答案证据。

设计判断：

- 不把 `200亿省` 这类业务规则写进 core prompt；Catalog 只做通用表格描述。
- LLM description 帮助选表、规划和长对话记忆；最终答案仍要回源表/clean view 读数和验证。
- `tableclaw_catalog_tables` 是显式工具，不在普通 retrieve 首次调用时自动对全部上传表跑 LLM，避免用户第一问被 161 张表的 description 生成拖慢。

本地验证：

- `py_compile` 通过：`nanobot/nanobot/agent/tools/tableclaw.py`、`eval_test/run_eval.py`、`eval_test/run_gold_parallel_eval.py`。
- Nanobot 自动工具注册已包含：
  - `tableclaw_catalog_tables`
  - `tableclaw_retrieve_tables`
  - `tableclaw_inspect`
  - `tableclaw_locate_column`
  - `tableclaw_extract_series`
  - `tableclaw_topk`
  - `tableclaw_filter`
- smoke：`tableclaw_catalog_tables(describe_with_llm=False, limit=2)` 可生成 catalog/profile/clean_view/description fallback。
- smoke：对 `全国各省份数据-通报应收总额_202512.xlsx` 定向生成 catalog entry 后，`tableclaw_retrieve_tables` 返回候选时可带出 `short_description`、`description_status`、`description_path`。

当前限制：

- 当前 shell 环境未设置 `DASHSCOPE_API_KEY`，smoke 使用 fallback；在 `./start.sh` / `./eval.sh` 这类注入 key 的环境中会使用 `deepseek-v4-pro`。
- Catalog v0 还没有自动 table group discovery；“全年趋势/最近三个月”仍需要后续识别同模板月度文件组。
- Description 还没有 confidence/evidence anchors；后续需要在 catalog-assisted retrieval eval 中量化收益。

### TODO Refresh for TableClaw v0.2

当前版本已经达到“主流程可跑 + 40 条 gold benchmark 有基线”的阶段，因此 TODO 从“先打通链路”切换到“针对失败点做工具化闭环”。

已确认完成并在 TODO 中打勾：

- `tableclaw_inspect` 已进入 Nanobot 主流程。
- `workspace/table_cache/*.schema.json` 已生成并由 inspect 复用。
- `tableclaw_retrieve_tables` 已从文件 preview 召回升级为 schema-based retrieval v0。
- 40 条 gold cases 并行评测已跑通，DeepSeek LLM judge、numeric/entity F1、trace/token 均已记录。
- 当前 cache 机制已实际生效：retrieval 用 schema index，inspect 用 schema cache；40-case baseline 中 provider cached tokens 占比较高。

下一版优先级：

1. `tableclaw_locate_column`：解决月份/指标/多级表头列定位不稳。
2. `tableclaw_extract_series`：解决 trend table 和跨月序列抽取。
3. `tableclaw_topk`：把排名类任务从临时脚本沉淀为稳定工具。
4. `tableclaw_filter`：解决多条件筛选和计数。
5. `tableclaw_chart_data`：先评估图表底层数据正确性，再评估图像呈现。
6. eval 侧补 cache hit/miss、exec/read_file/tool step、cached/non-cached 对照，确保优化能被量化。

判断：下一版暂时不重写 Codex xlsx 大 skill。先保留它作为通用兜底，把高频、可确定的表格读算动作沉淀为 TableClaw tools。这样更符合“skill 负责策略，tool 负责确定性执行”的架构边界。

### TableClaw Tools v0.2

完成 4 个确定性读算工具，接入位置仍为 `nanobot/nanobot/agent/tools/tableclaw.py`：

- `tableclaw_locate_column`：按 `metric / period / group / reference` 定位多级表头列，内部会填充 merged header。
- `tableclaw_topk`：按指标列做 top/bottom-k，支持排除合计行。
- `tableclaw_filter`：按多个条件筛选行，支持 `eq / contains / gt / gte / lt / lte / between / ne`。
- `tableclaw_extract_series`：按实体、指标、月份区间抽取跨期序列。

配套改动：

- `eval_test/run_eval.py` 的 workflow prompt 已引导模型优先使用 `locate/topk/filter/extract_series`，只有工具不足时再写短 Python 脚本。
- `eval_test/run_gold_parallel_eval.py` 已把新增工具纳入 trace，并在 markdown summary 里统计各 TableClaw tool 覆盖 case 数。

本地 smoke：

- `py_compile` 通过。
- Nanobot 工具注册列表已包含 `tableclaw_extract_series`、`tableclaw_filter`、`tableclaw_inspect`、`tableclaw_locate_column`、`tableclaw_retrieve_tables`、`tableclaw_topk`。
- 用 `市州数据-营业收现率台账.xlsx` 验证：
  - `locate_column(metric=营业收现率完成, period=202602)` 定位到 C 列。
  - `topk(metric=营业收现率完成, period=202602, k=3)` 返回达州、乐山、巴中。
  - `filter(metric=营业收现率完成, period=202601, lt 0.7)` 返回 6 个单位。
  - `extract_series(entity=达州, metric=营业收现率完成, periods=202601,202602)` 可返回两期值。

### Tool-Prompt Balance

40 条 gold cases 跑完后，v0.2 工具化版本的 ACC 为 37.50%，低于上一版 40.00%。虽然 `locate/topk/filter/extract_series` 被模型频繁调用，平均耗时略降，numeric/entity F1 略升，但 ranking 类准确率明显下降，skill 读取率也降到 7.50%。

结论：

- 工具应该作为模型可选能力暴露，不应该在 eval prompt 里显式规定“必须/优先”使用某些工具。
- Skill 负责策略，tool 负责可调用能力，LLM 基模负责 planner/controller。
- Prompt 只保留必要上下文：用户表格已上传到哪里、gold answer 不能假设、视觉题当前只评底层数据、最终需要说明使用了哪些表。
- 具体工具列表交给 Nanobot tool registry 和 tool description 自然暴露给模型。

已调整：

- `eval_test/run_eval.py:render_prompt` 不再显式列出 `tableclaw_*` 工具，也不再强制 `retrieve -> inspect -> locate/topk/filter/series` 流程。
- 后续复测目标：观察宽松工具策略能否恢复 ranking 准确率，同时保留部分速度和结构化工具收益。

### Gold Cases v3 Loose Tools Run

完成 v3-loose-tools 全量 40-case benchmark，并正式归档：

- 报告：`docs/实验评测/gold-cases/runs/2026-06-10-v3-loose-tools-acc40.md`
- 最新报告：`docs/实验评测/gold-cases/latest-parallel-eval-summary.md`
- 本地完整 JSON/JSONL：`eval_test/results/gold_cases/parallel/runs/2026-06-10-v3-loose-tools-acc40_*`

结果：

- ACC：40.00%（16 correct / 8 partial / 16 incorrect）。
- Avg judge score：0.5050，高于 v1/v2。
- Numeric F1：0.4154。
- Entity F1：0.6538，高于 v1/v2。
- Avg elapsed：221.85s / case，高于 v1/v2。
- Total answer tokens：17,096,327，高于 v1/v2。

解读：

- 宽松工具策略优于强制工具策略：ACC 回到 baseline，平均分和实体 F1 更好。
- 但模型探索更自由后，token 和耗时明显升高。
- 最大长尾是 case 39，耗时 805.18s；模型在 `小微ICT` / 欠费相关字段上反复搜索，说明需要 step/time budget 和更强的 field/range grounding。

下一步改进方向：

1. **加预算控制**：gold eval 增加 per-case max iterations / max elapsed / max tool calls，超限时让模型基于当前证据作答。
2. **召回升级**：为 40 gold cases 标注 gold table mapping，做 Recall@k；优先修 province/city 表召回混淆。
3. **字段定位增强**：不是在 prompt 强推工具，而是在 tool description/schema cache 中增强“200亿省”“排名列”“同比/占收比”等字段证据。
4. **错误类型专项**：优先 chart_generation 的省级范围和 filter_qa 的多条件判断；ranking 目前仍是相对优势能力。

### Curated Gold Cases Import

用户新增 `测试case抽样.xlsx`，包含 `问题` / `标准答案` 两列。虽然口头描述为 30 个 case，但实际文件含 40 条有效问答。

处理：

- 将原始 xlsx 归档到 `eval_test/test_dataset/source/测试case抽样.xlsx`。
- 新增 `eval_test/import_gold_cases.py`，导入为 `eval_test/test_dataset/gold_cases.jsonl`。
- `run_eval.py` 新增 `--gold-cases`，默认选择全部 40 条；如需子集可加 `--limit`。
- 新增 `eval_test/run_gold_parallel_eval.py` 与 `./eval_gold_parallel.sh`，用于并行跑 40 条 gold case，并用 DeepSeek `deepseek-v4-pro` 做 LLM judge。
- gold case 当前标记为 `gold_answer_reference`，标准答案只作为评测侧参考，不注入 prompt；自动判分暂标 `passed=None`，后续接 manual/LLM judge。

导入统计：

- 总数：40 条。
- `chart_generation`: 22。
- `ranking_qa`: 11。
- `table_qa`: 3。
- `filter_qa`: 2。
- `trend_table`: 2。

并行评测指标：

- LLM judge ACC：`passed / total`。
- judge score：LLM 给出的 0-1 分。
- numeric F1：答案与 gold 中抽取数字后的宏平均 F1，兼容百分比/小数表达。
- entity F1：核心省份、市州、指标实体的宏平均 F1。
- workflow trace：记录 retrieval、inspect、skill 选择率、token、耗时和 answer/gold 对照。

输出：

- `eval_test/results/gold_cases/parallel/latest_results.jsonl`
- `eval_test/results/gold_cases/parallel/latest_summary.json`
- `docs/实验评测/gold-cases/latest-parallel-eval-summary.md`

### Gold Cases Benchmark Baseline

完成 40 条 gold cases 的第一次有效全量 benchmark。

运行命令：

```bash
./eval_gold_parallel.sh --concurrency 8
```

结果：

- 总数：40 条。
- LLM judge ACC：40.00%（16 correct / 7 partial / 17 incorrect）。
- `ranking_qa`：81.82%，当前最强。
- `chart_generation`：27.27%，主要拖后腿。
- `table_qa`：33.33%。
- `trend_table`：0.00%。
- `filter_qa`：0.00%。
- Retrieval call rate：100%。
- Inspect call rate：100%。
- Skill selection rate：90%。
- Total answer tokens：14,187,768。
- Avg elapsed time：208.07s / case。

判读：

- 当前 TableClaw workflow 编排已经跑通；失败重点不在“没有调用工具”，而在表格 grounding、列定位、范围选择、`200亿省` 口径和图表底层数据抽取。
- 已新增 `docs/实验评测/gold-cases/gold-benchmark-protocol.md` 固化 prompt、workflow、judge 方法和本轮 baseline，后续优化后按同一命令复测并对比。

### Table Schema Cache + Inspect Tool v0

目标：把 uploaded-table workflow 从“业务词 + preview 召回”推进到“schema cache + inspect + schema-based retrieval”，提升通用性，并为后续 `locate_column` / `topk` / `extract_series` 做底座。

新增/修改：

- `nanobot/nanobot/agent/tools/tableclaw.py`
  - 新增 `tableclaw_inspect(path, sheet=None, rebuild_cache=False)`。
  - 新增 `workspace/table_cache/*.schema.json` schema cache。
  - `tableclaw_retrieve_tables` 改为基于 schema cache 构建 `workspace/table_index/tables.jsonl`。
- `eval_test/run_eval.py`
  - raw-cleaned workflow prompt 现在要求：先 `tableclaw_retrieve_tables`，再对候选表 `tableclaw_inspect`，避免直接 `read_file` 读取 `.xlsx`。
- `docs/功能开发/table-schema-cache-rfc.md`
  - 记录 cache 字段、失效策略、工具接口与后续升级方向。

本地验证：

- `py_compile` 通过。
- 对 `市州数据-营业收现率台账.xlsx` 调用 `tableclaw_inspect`，生成 schema；第二次调用命中 cache。
- 重建 161 张上传表索引后，`workspace/table_cache/` 生成 161 个 schema cache。
- 问题 `202602 营业收现率完成最高的单位` 的 top1 召回变为 `市州数据-营业收现率台账.xlsx`，说明 schema/header 信号已经参与召回。

当前边界：

- 仍保留少量当前工业表格领域词作为加分项，但召回不再只依赖这些词。
- schema 只做启发式候选表头和列类型判断，还不是严格的 semantic parser。
- 下一步优先做 `tableclaw_locate_column`、`tableclaw_extract_series`、`tableclaw_topk`，让模型少写 openpyxl 探索脚本。

## 2026-06-08

### Uploaded Table Workflow v0

目标：模拟用户已经把工业表上传到 TableClaw 工作区，验证 `workspace/uploads -> Nanobot 内置召回工具 -> 候选表选择 -> skill 选择 -> 工具执行 -> trace/token 记录` 的完整编排链路。

新增：

- `nanobot/nanobot/agent/tools/tableclaw.py`：新增 Nanobot builtin tool `tableclaw_retrieve_tables`。它从当前 workspace 的 `uploads/` 与 `table_index/tables.jsonl` 中召回候选表，不把 gold table path 注入 prompt。
- `eval_test/run_eval.py`：统一评测入口，新增 `--raw-cleaned --limit 10` workflow 模式；旧的独立 smoke runner 已删除。
- `docs/实验评测/uploaded-table-workflow/latest-eval-summary.md`：记录本次 10 case 的 retrieval tool、skill sequence、tool、token 和答案预览报告。

本次运行结果：

- 上传/索引表格：161 张。
- 任务：10 条 cleaned raw eval candidate（4 chart_generation + 3 table_qa + 3 ranking_qa）。
- 10/10 case 触发 `tableclaw_retrieve_tables`。
- 10/10 case 触发 skill read。
- 触发过的 skill：`xlsx`、`table-read`、`table-chart`、`table-validate`。
- 总 token：约 1,982,531；平均每题约 198,253。
- 平均耗时：约 325.0 秒。

观察：

- 编排链路已经并入 Nanobot 本体：用户问题不显式给表路径，模型先调用 `tableclaw_retrieve_tables`，再在候选表中判断、读取 skill、执行 openpyxl 分析。
- 这次是 workflow orchestration 测试，不是最终准确率 benchmark；当前轻量 fact matcher 只能做粗略自动检查。
- 模型仍经常直接 `read_file` 读取 `.xlsx`，失败后再写 openpyxl 脚本摸表头。下一步优先沉淀 `tableclaw_inspect`、`tableclaw_locate_column`、`tableclaw_extract_series`、`tableclaw_topk` 等工具，减少长脚本和 token。
- `workspace/uploads/` 作为未来 Web 上传目录的本地模拟；后续前端上传只需要对齐这个目录和 manifest/index 即可。

### Product Research Integration

整合了用户提供的产品调研材料到 `docs/功能开发/tableclaw-positioning-and-workflow.md`，把 Claude for Excel、Copilot in Excel、WPS AI、Gemini in Sheets、飞书/钉钉/腾讯文档、Airtable/Rows、通用 Agent 系统和 Spreadsheet Agent 论文系统统一放进 TableClaw 定位文档。

## 2026-05-28

### 已阅读的项目上下文

- 阅读了 `docs/架构/project-structure.md`，确认 TableClaw 当前以裁剪后的上游 `nanobot/` 为骨干。
- 阅读了 `nanobot/README.md`、`nanobot/CLAUDE.md`、`nanobot/.agent/design.md`、`nanobot/.agent/security.md`、`nanobot/.agent/gotchas.md`。
- 阅读了内置 skill 加载器 `nanobot/nanobot/agent/skills.py` 和内置 skills 摘要。
- 阅读了三个外部 spreadsheet skill：
  - `skills/anthropic_xlsx_skill/SKILL.md`
  - `skills/kimi_xlsx_skill/SKILL.md`
  - `skills/kimi_xlsx_skill/pivot-table.md`
  - `skills/codex/SKILL.md`

### 关键架构判断

- 新能力优先加在 `nanobot/nanobot/agent/tools/`、`nanobot/nanobot/skills/`、`nanobot/nanobot/channels/` 或 `nanobot/nanobot/providers/`。
- 尽量不动 `nanobot/nanobot/agent/loop.py` 和 `nanobot/nanobot/agent/runner.py`，除非问题确实发生在核心调度链路。
- 配置集中在 `nanobot/nanobot/config/schema.py`；JSON 使用 camelCase，Pydantic 支持 snake_case 兼容。
- Provider 注册入口是 `nanobot/nanobot/providers/registry.py`。
- DashScope provider 已内置，默认 API Base 是 `https://dashscope.aliyuncs.com/compatible-mode/v1`，并支持 `enable_thinking` 风格的思考开关。

### 百炼模型配置

新增本地运行配置模板：

- 文件：`nanobot/configs/tableclaw-bailian-dashscope.json`
- Provider：`dashscope`
- API Base：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- 当前 model：`deepseek-v4-pro`
- Reasoning：`high`
- Workspace：`/Users/hxy/Desktop/TableClaw/workspace`
- API Key：通过 `${DASHSCOPE_API_KEY}` 环境变量注入，避免明文写入项目文件

备注：用户描述为 “Kimi K2.6”，但提供的百炼文档内容是 DeepSeek 系列，示例模型为 `deepseek-v4-pro`。先按文档示例跑通；后续如确认 Kimi K2.6 的百炼 model id，再替换配置中的 `agents.defaults.model`。

### 待验证

- 使用上述配置启动 nanobot。
- 发送一次 `你好`。
- 等待模型返回，确认端到端调用链路可用。

### 验证结果

已跑通。

本地环境：

- 创建虚拟环境：`nanobot/.venv`
- 安装方式：在 `nanobot/` 目录执行 `.venv/bin/python -m pip install -e .`
- 配置文件：`nanobot/configs/tableclaw-bailian-dashscope.json`

验证命令：

```bash
cd /Users/hxy/Desktop/TableClaw/nanobot
DASHSCOPE_API_KEY="<百炼 API Key>" .venv/bin/python -m nanobot agent \
  --config configs/tableclaw-bailian-dashscope.json \
  --message "你好" \
  --no-markdown \
  --no-logs
```

实际返回摘要：

- nanobot 成功创建 `~/.nanobot/tableclaw-workspace` 下的模板与记忆文件。
- Git store 初始化成功。
- 模型返回了中文问候：“你好！我是 nanobot，你的个人 AI 助手。有什么我可以帮你的吗？”

### 后续切换模型

优先只改 `nanobot/configs/tableclaw-bailian-dashscope.json`：

- `agents.defaults.model`
- `agents.defaults.provider`
- `providers.<provider>.apiBase`
- `providers.<provider>.apiKey` 对应的环境变量名
- 如模型不支持思考模式，将 `agents.defaults.reasoningEffort` 改为 `"none"` 或删除该字段

如果后续确认 “Kimi K2.6” 的百炼 model id：

1. 先替换 `agents.defaults.model`。
2. 保持 provider 为 `dashscope` 试跑一次。
3. 如果百炼返回参数不兼容，再检查 `nanobot/nanobot/providers/openai_compat_provider.py` 中 Kimi thinking 参数映射是否需要为 DashScope 做特殊处理。

### 一键启动脚本

新增项目根目录脚本：

- 文件：`start.sh`
- 用途：直接进入 nanobot 交互聊天界面
- 运行方式：

```bash
cd /Users/hxy/Desktop/TableClaw
./start.sh
```

脚本行为：

- 自动定位项目根目录。
- 自动激活 `nanobot/.venv`，再使用该环境里的 `python`。
- 使用配置 `nanobot/configs/tableclaw-bailian-dashscope.json`。
- 自动设置 `DASHSCOPE_API_KEY`；如果外部环境已设置同名变量，则优先使用外部变量。
- 执行 `python -m nanobot agent --config ... --no-logs`，进入交互模式。

安全备注：为了满足“只执行 `./start.sh`，不再输入虚拟环境和参数”的需求，脚本内有本地默认 API Key。后续如果要提交到公开仓库或发给别人，先改成只从环境变量、`.env` 或系统钥匙串读取。

### 启动脚本交互修复

现象：在未手动 `source nanobot/.venv/bin/activate` 的 shell 中直接执行 `./start.sh`，nanobot 能进入交互界面但第一次会自动收到 EOF 并退出；手动激活 venv 后再执行正常。

处理：更新 `start.sh`，让脚本内部先 `source nanobot/.venv/bin/activate`，再执行 `python -m nanobot ...`。这样保留“一键启动”，同时让 prompt_toolkit/交互 CLI 拿到完整虚拟环境上下文。

### 工作区迁移到项目目录

问题：初始 workspace 位于 `~/.nanobot/tableclaw-workspace`，位置较深，不方便查看 `USER.md`、`SOUL.md`、会话历史、输出和调试文件，也会让 TableClaw 运行状态散落到用户全局目录。

处理：

- 将 `nanobot/configs/tableclaw-bailian-dashscope.json` 中的 `agents.defaults.workspace` 改为 `/Users/hxy/Desktop/TableClaw/workspace`。
- 将旧 workspace 内容从 `~/.nanobot/tableclaw-workspace/` 复制到项目内 `workspace/`。
- 保留旧目录不删除，避免误删已有本地状态。

后续查看重点：

- `workspace/USER.md`
- `workspace/SOUL.md`
- `workspace/AGENTS.md`
- `workspace/memory/MEMORY.md`
- `workspace/memory/history.jsonl`
- `workspace/sessions/`
- `workspace/skills/`

### 搭建第一版 eval_test/test_dataset

目标：先完成一个很小的评测数据集，用来验证 TableClaw 对 Excel 表格的基本读取、定位、筛选和排序能力。

输入表池：

- 原始目录：`test_table/`
- 本次选表：`test_table/市州数据-营业收现率台账.xlsx`

新增目录：

- `eval_test/README.md`
- `eval_test/test_dataset/README.md`
- `eval_test/test_dataset/manifest.json`
- `eval_test/test_dataset/tasks.jsonl`
- `eval_test/test_dataset/tables/市州数据-营业收现率台账.xlsx`

设计决定：

- 不把测试表放进 `workspace/`。
- `workspace/` 是 nanobot 运行态，存放 memory、sessions、用户级 skills 和临时输出。
- eval 数据集是项目资产，放在 `eval_test/test_dataset/`，并复制本次需要的表格，避免依赖全量 `test_table/`。

当前任务：

1. `tc_smoke_001`：问 202602 期间“营业收现率完成”最高的单位及数值。
   - Gold：达州，`1.08669577950616`。
2. `tc_smoke_002`：问 202601 期间“营业收现率完成”低于 `0.7` 的单位和数量。
   - Gold：6 个，分别为自贡、攀枝花、雅安、阿坝、甘孜、凉山。

后续方向：

- 加 eval runner：读取 JSONL，调用 `./start.sh --message ...` 或 SDK，记录模型答案。
- 加判分器：先做 structured exact/numeric tolerance，再考虑 LLM-as-judge。
- 网站上传文件时，建议进入单独的 upload/storage 目录，例如 `workspace/uploads/<session_id>/` 或服务端专用 `storage/uploads/<tenant>/<upload_id>/`；不要直接混入固定 eval dataset。

### 加入 xlsx skill 作为最小可演示 skill 选择机制

需求：希望看到当用户问题涉及表格时，框架可以选择 skill，再调用工具解决问题；并且 skill/no skill 行为有区别。

实现选择：不改 nanobot 核心，只新增用户级 workspace skill：

- `workspace/skills/xlsx/SKILL.md`

原因：

- nanobot 已经支持从 `workspace/skills/` 自动发现 skill。
- `nanobot/nanobot/templates/agent/skills_section.md` 已明确要求：要使用 skill，先用 `read_file` 读取对应 `SKILL.md`。
- 这种方式只改项目运行态/配置资产，不碰 agent loop/runner。

当前 `xlsx` skill 内容：

- 触发范围：`.xlsx`、`.xlsm`、`.xls`、`.csv`、`.tsv`，以及用户询问 spreadsheet/table 文件。
- 推荐流程：先 inspect workbook，再用 `exec` + Python + `openpyxl` 精确计算。
- 对 TableClaw eval 表格增加提示：两级表头、月份在第 1 行、指标在第 2 行、`市州合计` 为汇总行。

skill/no skill 对比建议：

- skill：默认 `./start.sh`。
- no skill：在配置里临时设置 `agents.defaults.disabledSkills = ["xlsx"]`，或者后续增加一份 no-skill config/runner 统一跑对照。

### Skill/no-skill 手动对照测试

该早期手动对照结果已合并到统一矩阵报告：

- `docs/实验评测/skill-matrix/xlsx-skill-selection-matrix.md`

结论简述：

- skill on：模型明确读取 `workspace/skills/xlsx/SKILL.md`，再读取表格，并用 Python/openpyxl 计算；答案正确。
- skill off：模型没有读取 skill，先尝试直接读取表格文本化输出，遇到截断后改用 Python；答案也正确，但过程更绕。
- 当前手动对照已能展示“表格任务触发 skill 选择 + 工具调用”的过程。

Token 统计补充：

- 早期曾新增单次 token 对照脚本，用于 skill-on/skill-off token 对照。
- 该能力后续已统一由 `eval_test/run_eval.py` 接管，旧脚本与旧结果快照已清理。
- 本次 hard prompt 结果：
  - skill on：35,562 total tokens。
  - skill off：57,234 total tokens。
  - no-skill 比 skill-on 多 21,672 tokens，约 +60.9%。
- 这一步先证明 skill/no-skill 的 token 差异；随后已把 usage 持久化接入 AgentLoop，见下一节。

### Token usage 运行时持久化

详见独立文档：

- `docs/功能开发/token-usage.md`

实现：

- 新增 `nanobot/nanobot/utils/usage_log.py`，用 JSONL + file lock 写入 usage。
- 修改 `nanobot/nanobot/agent/loop.py`，在每轮 AgentLoop 保存会话时同步记录 usage。
- 新增 `eval_test/summarize_usage.py`，用于汇总 `workspace/usage/usage.jsonl`。

输出位置：

- `workspace/usage/usage.jsonl`

记录内容：

- session、turn、model、provider、token usage、tools_used、stop_reason、latency_ms 等。

说明：

- 这是运行时能力，不再只依赖 eval 脚本。
- 正常 `./start.sh` 对话和 `./start.sh --message ...` 都会写入。
- 纯命令或未发生模型调用的轮次不会产生 usage 记录。

### 显示工具调用过程

需求：启动后能在终端看到 agent 是否读取 skill、是否调用工具，而不是只看到最终答案。

处理：

- 将 `nanobot/configs/tableclaw-bailian-dashscope.json` 的 `channels.sendToolHints` 改为 `true`。
- 保持 `nanobot/nanobot/templates/agent/skills_section.md` 的原生机制：模型如果决定使用 skill，会通过 `read_file` 读取对应 `SKILL.md`。

预期展示：

- 当用户提出 xlsx/table 问题时，如果模型自然选择 `xlsx` skill，终端会显示读取 `nanobot/nanobot/skills/xlsx/SKILL.md` 的 tool hint。
- 由于 tool hints 已开启，终端也会显示执行 Python/openpyxl 等工具调用提示。

## 2026-05-29

### 整理 docs 文档结构

目标：把原先平铺在 `docs/` 下的文档整理成长期可维护的信息架构。

新增总索引：

- `docs/README.md`

分类目录：

- `docs/架构/`
- `docs/功能开发/`
- `docs/实验评测/`
- `docs/项目管理/`

移动结果：

- `docs/project-structure.md` -> `docs/架构/project-structure.md`
- `docs/token-usage.md` -> `docs/功能开发/token-usage.md`
- skill/no-skill 对照与后续 trace 统一收敛到 `docs/实验评测/skill-matrix/xlsx-skill-selection-matrix.md`
- `docs/development-log.md` -> `docs/项目管理/development-log.md`

新增功能文档：

- `docs/功能开发/skill-system.md`

该文档记录：

- nanobot skill 的 builtin/workspace 两类来源。
- workspace skill 优先覆盖 builtin skill 的加载规则。
- skill summary 如何进入 system prompt。
- 基模如何基于 name/description/path 自行选择并读取 skill。
- TableClaw 上线时核心 skill 内置化、业务 skill workspace 化的建议。
- 后续增加 skill router 的方向。

### 分析三个参考 Spreadsheet Skill

新增文档：

- `docs/功能开发/reference-spreadsheet-skills.md`

分析对象：

- `skills/codex/SKILL.md`
- `skills/kimi_xlsx_skill/SKILL.md`
- `skills/anthropic_xlsx_skill/SKILL.md`

结论：

- Codex skill 更偏高质量创建/编辑/渲染/验证 workbook artifact，适合吸收产物质量和 verify/render 闭环。
- Kimi skill 更偏 Excel 结构验证和 PivotTable 工具链，适合吸收 inspect、recheck、reference-check、validate、pivot 顺序。
- Anthropic/Claude skill 更贴近当前 TableClaw v0 的 Python/openpyxl 路线，适合吸收公式不硬编码、LibreOffice 重算、公式错误扫描、模板保持等规范。
- 三者都不建议整包搬入 nanobot；下一步应写 TableClaw Core Table Skill v0，吸收三者强项。

### 将 Codex Spreadsheet Skill 接入 nanobot builtin

目标：验证不依赖 workspace 用户级 skill 时，nanobot 主流程是否仍能通过 builtin skill 发现和调用表格能力。

处理：

- 新增 `nanobot/nanobot/skills/xlsx/SKILL.md`。
- 内容来自 `skills/codex/SKILL.md`，作为单文件 Codex Spreadsheets 参考版本先接入。
- 删除 `workspace/skills/xlsx/SKILL.md`。
- 保留 skill 名称为目录名 `xlsx`，这样 `nanobot/configs/tableclaw-bailian-dashscope-no-xlsx-skill.json` 里的 `disabledSkills: ["xlsx"]` 仍然有效。
- 后续由 `eval_test/run_eval.py` 统一识别旧 workspace 路径和新 builtin 路径。

当前加载验证：

- `SkillsLoader` 现在返回 `xlsx` 的 source 为 `builtin`。
- 路径为 `/Users/hxy/Desktop/TableClaw/nanobot/nanobot/skills/xlsx/SKILL.md`。

注意：

- 当前 builtin `xlsx` 是 Codex 参考 skill 原文，偏 workbook 创建/编辑/渲染/验证。
- 它不一定最适合 TableClaw 的表格 QA 场景，后续还需要测试模型是否会因 artifact-tool 依赖而绕路或受阻。
- 如果测试发现过重，应继续沉淀更轻的 `tableclaw-table` builtin skill。

验证结果：

- 运行 `./start.sh --message ... --session cli:builtin-xlsx-skill-smoke`。
- 模型读取了 `nanobot/nanobot/skills/xlsx/SKILL.md`。
- 模型最终答对：202602 期间最高单位为达州，值为 `1.08669577950616`。
- 本轮 usage：`total_tokens=91892`，`prompt_tokens=90451`，`completion_tokens=1441`，`cached_tokens=44800`。
- 后续已合并进统一矩阵报告：`docs/实验评测/skill-matrix/xlsx-skill-selection-matrix.md`。

观察：

- builtin skill 调用成功。
- 模型不是第一步就读 skill，而是先读表遇到截断后再读 skill。
- Codex skill 原文约 38KB，明显偏重；下一步更应该写 TableClaw 专用轻量表格 QA skill。

### 增加 Skill Selection Trace

目标：把“模型有没有选择 skill、什么时候选择、调用了哪些工具、token 消耗多少”做成可复现日志，方便后续评估和复查。

输出：

- `eval_test/results/skill_matrix/latest_eval.json`
- `docs/实验评测/skill-matrix/latest-eval-summary.md`
- `docs/实验评测/skill-matrix/xlsx-skill-selection-matrix.md`

本次复杂问题结果：

- 模型第 1 个工具调用就是读取 `nanobot/nanobot/skills/xlsx/SKILL.md`。
- 随后读取测试 xlsx 表，再用 Python/openpyxl 精确计算。
- 答案命中关键 gold facts：Top3 为达州、乐山、巴中，使用 `Sheet1`，排除 `市州合计`。
- usage：`total_tokens=61239`，`prompt_tokens=58921`，`completion_tokens=2318`，`cached_tokens=33152`。

随后补充 simple/complex × skill-on/skill-off 矩阵实验：

| Case | Mode | Skill selected | Skill step | Correct | Total tokens |
| --- | --- | --- | ---: | --- | ---: |
| simple | skill-on | true | 1 | true | 73,161 |
| simple | skill-off | false | - | true | 55,624 |
| complex | skill-on | true | 1 | true | 70,227 |
| complex | skill-off | false | - | true | 74,139 |

观察：

- skill-on 的 simple 和 complex 两个问题都在第 1 个 tool step 读取 builtin `xlsx` skill。
- simple 问题中，skill-on 比 skill-off 多 17,537 tokens（+31.5%），说明当前 Codex 原版 skill 对简单 QA 偏重。
- complex 问题中，skill-on 比 skill-off 少 3,912 tokens（-5.3%），说明复杂任务更能体现 skill 提前加载流程的价值。
- 这个结果支持下一步：保留 builtin skill 机制，但裁剪成更轻、更偏 TableClaw QA 的 `tableclaw-table` skill。

### 整理 eval_test 脚本

目标：把 `eval_test/` 从临时脚本整理为可持续迭代的评测模块。

新增统一入口：

- `eval_test/run_eval.py`

能力：

- 读取 `eval_test/test_dataset/tasks.jsonl`。
- 支持 `skill-on` / `skill-off` 两种配置。
- 记录答案预览、工具调用时间线、是否读取 xlsx skill、skill 读取 step、token usage、latency。
- 输出 `eval_test/results/skill_matrix/latest_eval.json` 和 `docs/实验评测/skill-matrix/latest-eval-summary.md`。

整理：

- 删除旧的单次 token 对照脚本，token 对照由 `run_eval.py` 统一承担。
- 清理 `eval_test/__pycache__/` 和旧结果快照。
- `summarize_usage.py` 保留，职责是汇总运行时长期 usage 日志 `workspace/usage/usage.jsonl`。

### 新增一键评测脚本

新增：

- `eval.sh`

用途：

- 在项目根目录直接运行 `./eval.sh` 即可调用 `eval_test/run_eval.py`。
- 自动激活 `nanobot/.venv`。
- 复用 `DASHSCOPE_API_KEY` 环境变量；如果外部未设置，则使用本地默认值。
- 参数会透传给 `run_eval.py`，例如 `./eval.sh --list-tasks`。

### 统一 eval task 集

目标：避免 `tasks.jsonl` 和 `skill_selection_matrix_tasks.jsonl` 分散维护。

处理：

- 删除 `eval_test/test_dataset/skill_selection_matrix_tasks.jsonl`。
- 将任务统一维护在 `eval_test/test_dataset/tasks.jsonl`。
- 当前任务数扩展到 10 个。
- 增加 `difficulty` 字段：`simple` / `medium` / `hard`。
- 保留 `case` 字段：`simple` / `medium` / `complex`，用于 skill-selection matrix 的 focused run。
- 更新 `eval_test/run_eval.py`，默认只读取统一的 `tasks.jsonl`。
- 新增筛选参数：
  - `--difficulty simple|medium|hard`
  - `--case simple|medium|complex`

当前任务覆盖：

- simple：直接最高值、阈值筛选、计数。
- medium：Top/Bottom 排名、跨期变化、阈值排序。
- hard：多期间 Top5 交集、连续两期阈值筛选、均值/最高/最低聚合。

说明：不维护一次性汇报文档；需要对外说明时，从实验评测和功能开发文档中提取即可。

### 完成 10-task skill/no-skill 对照评测

执行：

- `./eval.sh`

范围：

- 10 个统一评测任务。
- 每个任务分别跑 `skill-on` 与 `skill-off`，共 20 次模型调用。
- 表格统一为 `eval_test/test_dataset/tables/市州数据-营业收现率台账.xlsx`。

产物：

- 原始 JSON：`eval_test/results/skill_matrix/latest_eval.json`
- 自动报告：`docs/实验评测/skill-matrix/latest-eval-summary.md`
- 人工整理矩阵：`docs/实验评测/skill-matrix/xlsx-skill-selection-matrix.md`

结果摘要：

| Mode | Runs | Auto pass | Manual check | Skill reads | Total tokens | Avg tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| skill-on | 10 | 8/10 | 10/10 | 3/10 | 730,590 | 73,059 |
| skill-off | 10 | 7/10 | 10/10 | 0/10 | 712,548 | 71,254 |

观察：

- `skill-on` 并不等价于模型必然读取 skill；本轮 10 条中实际读取 `xlsx/SKILL.md` 的为 3 条。
- 实际读取 skill 的轮次均发生在第 3 个 tool step，说明模型常见路径是先看表或 tool-result，再决定补读 skill。
- `skill-off` 没有读取内置 skill，说明禁用配置生效。
- 自动评分的 false 多数来自模型输出四位小数而 gold 使用 `1e-6` 精度；人工核验排序、单位、数量和近似数值均正确。
- 当前 Codex 原版 spreadsheet skill 较重，整体 skill-on token 比 skill-off 多约 2.5%。后续如果要提高 TableClaw 的性价比，应裁剪为轻量、只服务表格问答的 TableClaw skill。

### 新增 TableClaw Skill Pipeline 可视化

新增：

- `docs/架构/tableclaw-skill-pipeline.svg`
- `docs/架构/tableclaw-xlsx-case-flow.svg`

用途：

- 用一张图展示 TableClaw 的核心链路：用户表格问题 -> nanobot agent -> skill registry -> 选择 `xlsx` skill -> 表格执行 -> 答案生成 -> trace/token usage。
- 用另一张具体案例图展示 `tc_hard_003` 从输入问题、选中 `xlsx` skill、执行 openpyxl 计算到输出答案的过程。
- 只保留 SVG 图片，便于直接用于演示材料或幻灯片。

表达边界：

- 图用于解释当前能力链路，不夸大为“skill 一定优于 no-skill”。
- 当前实验支撑点是：builtin `xlsx` skill 可以被 nanobot 选择，skill/no-skill ablation 可以记录选择时机、工具轨迹、答案质量和 token usage。

### 清理临时展示分支，回到 Codex xlsx skill 主线

本次清理展示用的合成内容，恢复到更适合继续研发的基线：

- 恢复活动内置 skill：`nanobot/nanobot/skills/xlsx/SKILL.md`
- 删除展示用小 skill：`table-structure`、`table-aggregation`、`table-ranking`
- 删除展示用合成任务、结果和文档。
- 删除展示 HTML 目录：`docs/展示/`
- `skill-off` 配置重新只禁用 `xlsx`
- `eval_test/run_eval.py` 重新只追踪 `xlsx` skill

后续研发继续沿用当前主线：Codex Spreadsheets skill 内置接入、10-task eval、skill/no-skill 矩阵、token usage 统计。

### 清理展示分支残留，回到主线

目标：让代码和文档只保留当前研发主线，避免临时展示任务、专用 runner、专用 skill、专用文档影响后续判断。

处理：

- 删除展示分支 runner、任务集、表格副本、配置和临时小 skill。
- 删除展示分支报告和同步材料。
- `eval_test/` 回到单一入口：`run_eval.py` + `tasks.jsonl` + `skill_matrix/` 输出。
- `docs/实验评测/` 回到单一主线索引：`skill-matrix/`。
- `run_eval.py` 继续只追踪 builtin `xlsx` skill。
- 修正 `_fact_matches`：`count=6` 等数字事实不再用字符串子串匹配，而是按完整数字匹配，减少自动评分误判。

后续研发继续沿用当前主线：Codex Spreadsheets skill 内置接入、10-task eval、skill/no-skill 矩阵、token usage 统计。

### 修正项目定位 + 建立 TODO/dev-log 双文档

定位：之前的文档把 TableClaw 当成"表格 QA agent"，过窄。明确修正为**表格专精 agent**，商用形态需要覆盖 4 大场景：

1. QA / 分析（当前主要做的）
2. 编辑 / 修复 / 清洗
3. 表格转换 / 跨表合并
4. 报表生成 / 从 0 建表

后续 skill / tool / 评测题设计都必须对照这 4 类，避免又退化回"只服务 QA"。

文档分工：

- 新增 `docs/项目管理/TODO.md`：维护近期/中期/长期待办，复选框格式，做完打勾不删，保留迭代轨迹。
- 现有 `docs/项目管理/development-log.md`：保留"做了什么 + 为什么"，**不再写计划**。
- 完成一项时：TODO 打勾 + dev-log 补一段说明，互相引用。
- `docs/README.md` 顶部索引补充 TODO 入口。

后续路径锁定为：先 git init 打基线 → 修评分器 → 写 native xlsx skill v0（4 大场景占位）→ 跑对照评测 → 拿数据对齐主推场景。具体见 [TODO.md](TODO.md)。

### 扩充 TODO 中期计划：dataset 规模化 + 专用 tool 系列 + 多家 skill 横评

为了让 TableClaw 真正走向商用 + 表格全场景定位，TODO 的中期段补了三件事：

1. **Eval Dataset 规模化到 80–150 题**：4 场景 × 三档运算难度 × 三档表结构复杂度，混合 4 类来源（test_table 现有 / 公开 benchmark / 同学贡献 / 合成），后续招募 3–5 名同学协作。本身需要先写 `CONTRIBUTING.md` + `SCHEMA.md` 才能开放认领。
2. **5 个专用表格 tool**：`tableclaw_inspect / locate_column / aggregate / filter / topk`，命名规范 `tableclaw_<动词>` snake_case，接入 `nanobot/nanobot/agent/tools/tableclaw/` 子目录。三道关卡验证：单元测试、集成测试、A/B vs SKILL.md 形态。先写 RFC 文档，code review 后再实现。
3. **多家 skill 横评 + 自研优化**：codex / kimi / anthropic / claude-code / 自研 v0 在同一 dataset 上跑，**带依赖跑（不降级）**，每家做 docker 隔离（kimi 跑 linux ELF / anthropic 装 LibreOffice）。新写 `run_multi_skill.py` harness，输出对比矩阵，最终在 `docs/实验评测/multi-skill/decision.md` 里决定 skill 路线。

这三件事是相互依赖的：dataset 扩了之后 tool 与 skill 才能在足够样本上做对照；tool 与 skill 横评结果反过来决定 dataset 还要补哪些边界 case。所以中期段并行推进，里程碑是"在 80+ 题 dataset 上拿到 5 家 skill × 全部场景的横评矩阵"。

## 2026-06-06

### 对齐 TableClaw 方案设计与老师要求

新增文档：

- `docs/功能开发/tableclaw-positioning-and-workflow.md`
- `docs/实验评测/workflow-routing.md`

这次把老师要求的四段内容收敛为一条研发主线：

1. 产品调研：Copilot in Excel、Gemini in Sheets、WPS AI、通用 Agent、SpreadsheetBench。
2. Eval 测试：从 10-task QA matrix 扩展到 12-task，新增 workflow routing 任务。
3. 能力边界：表格理解、操作、结果生成、workflow、context 五类边界。
4. TableClaw 方案：基于 Nanobot 做 TableAgent workflow，沉淀阶段化 table skills，后续补 memory/context/RAG、可插拔 harness、验证和回滚。

### 新增 TableClaw 轻量 Workflow Skills

新增 builtin skills：

- `nanobot/nanobot/skills/table-read/SKILL.md`
- `nanobot/nanobot/skills/table-clean/SKILL.md`
- `nanobot/nanobot/skills/table-validate/SKILL.md`
- `nanobot/nanobot/skills/table-report/SKILL.md`
- `nanobot/nanobot/skills/table-formula-debug/SKILL.md`
- `nanobot/nanobot/skills/table-chart/SKILL.md`

设计原则：

- 不替代 Codex 原文 `xlsx` skill，先作为轻量阶段化 skill 池。
- 每个 skill 都短，聚焦一个 workflow 阶段。
- 目标是让模型在单轮或多轮表格任务中按阶段读取不同 skill，例如 `table-read -> table-clean -> table-validate -> table-report`。

### 更新 Skill/no-skill Harness

修改：

- `eval_test/run_eval.py`
- `nanobot/configs/tableclaw-bailian-dashscope-no-xlsx-skill.json`

变化：

- `TRACKED_SKILLS` 从只追踪 `xlsx` 扩展到追踪 7 个 skill。
- 结果 JSON 增加 `skill_read_sequence`。
- Markdown summary 增加 `Skill sequence` 列。
- `--case` 支持 `workflow`。
- skill-off 配置禁用 `xlsx` 和 6 个 TableClaw 轻量 table skills，保证 ablation 干净。

### 新增 Workflow Routing Tasks

修改：

- `eval_test/test_dataset/tasks.jsonl`
- `eval_test/test_dataset/README.md`
- `eval_test/test_dataset/manifest.json`

新增：

- `tc_workflow_001`：读表结构 + 数据质量检查 + 判断是否适合跨期分析。
- `tc_workflow_002`：读表、清洗、两期低于阈值筛选、排序、管理建议、校验说明。

当前数据集从 10 题扩展到 12 题。

### 后续判断

下一步应先跑：

```bash
./eval.sh --case workflow
```

观察结果：

- skill-on 是否读取多个轻量 skill。
- skill-off 是否完全不读 table skills。
- skill-on 是否减少重复探索、提升报告结构、保留校验说明。
- token 是否因为读取多个 skill 增加，还是因流程清晰下降。

如果模型仍偏向只读 `xlsx` 或不读 skill，优先调整 skill descriptions；如果仍不稳定，再考虑在 Nanobot 上加显式 table workflow router 或把 inspect/clean/validate 下沉成 tools。

### 扩充外部产品调研文档

根据已有调研材料，重写并扩充：

- `docs/功能开发/tableclaw-positioning-and-workflow.md`

新增内容：

- 第一类：集成到既有表格 APP 内的插件类 Table Agent，例如 Claude for Excel、Copilot in Excel、Gemini in Sheets、WPS AI，以及飞书、钉钉、腾讯文档、Airtable、Rows 等表格/协作产品。
- 第二类：通用原生 Agent 系统中的 table 能力，例如 Claude Code、Codex、Kimi、GLM、Nanobot 等，重点分析文件读写、工具调用、Skill/MCP、context 压缩、日志和回滚。
- 第三类：专门的 Table Agent / Spreadsheet Agent 论文与 benchmark，例如 SpreadsheetBench、SheetAgent、SheetMind、TableTalk 等。
- 重新梳理 TableClaw 的两阶段路线：
  - 第一阶段：文件上传式 workflow agent。
  - 第二阶段：Excel / WPS / 飞书 / 钉钉插件化 table agent。
- 补充产品调研对 TableClaw 的启发：从 QA 转向 workflow，从读取转向结构理解，从长 prompt 转向 schema cache / RAG，从生成转向可验证执行。

本次只是文档层整合，没有改代码。

### 清洗 Raw Eval CSV

新增：

- `eval_test/clean_eval_csv.py`
- `eval_test/test_dataset/raw_eval_cleaned.jsonl`
- `eval_test/test_dataset/raw_eval_cleaned.csv`
- `eval_test/test_dataset/raw_eval_cleaning_report.md`

输入：

- `eval_test/eval_test.csv`

清洗结果：

- raw rows：835
- 有效 question + ground truth：826
- 按 exact question + ground truth 去重后：165 tasks
- chart-generation：144 tasks
- structured table QA：21 tasks

处理原则：

- 不覆盖 raw CSV，保留为源数据。
- 标准答案全部是 markdown table，因此先保留 `ground_truth_table` 结构化解析结果。
- 画图类任务不删除，而是标记 `requires_visual_artifact=true`。
- 当前图表任务只适合先评测“底层数据表是否正确”，不能直接评测图形质量。
- 因 raw CSV 没有 source workbook/table 映射，所有 cleaned tasks 暂时 `retrieval_eval_ready=false`。

后续：

1. 为 165 条任务补 `table_id` / `table_path`。
2. 将对应源表复制到 `workspace/uploads/`，模拟用户上传。
3. 为 workspace 表格建立 schema/table index。
4. 做 question -> table retrieval -> answer workflow 的召回评测。

### Gold Cases v4 Table Catalog Run

完成 v4-table-catalog 全量 40-case benchmark，并正式归档：

- 报告：`docs/实验评测/gold-cases/runs/2026-06-10-v4-table-catalog.md`
- 最新滚动报告：`docs/实验评测/gold-cases/latest-parallel-eval-summary.md`
- 本地完整 JSON/JSONL：`eval_test/results/gold_cases/parallel/runs/2026-06-10-v4-table-catalog_*`
- 日志：`logs/2026-06-10-v4-table-catalog.log`

本轮先通过 `tableclaw_catalog_tables(rebuild_catalog=True, describe_with_llm=True, model=deepseek-v4-pro)` 为 161 张上传表生成 catalog/profile/virtual clean view/description，再运行同一批 40 条 gold cases。源表未被修改，catalog 只作为检索和规划上下文。

结果：

- ACC：47.50%（19 correct / 8 partial / 13 incorrect）。
- Avg judge score：0.5625，为目前最高。
- Macro numeric F1：0.4303。
- Macro entity F1：0.6667，为目前最高。
- Retrieval / inspect 覆盖率：100% / 100%。
- Avg elapsed：229.85s，Total answer tokens：18,784,002，说明 catalog 提升准确率的同时仍放大长尾探索成本。

和前三版相比，v4 是目前最好的总分：v1 40.00% / 0.4800，v2 37.50% / 0.4650，v3 40.00% / 0.5050，v4 47.50% / 0.5625。

复盘判断：

- catalog layer 方向成立：欠费台账、市州应收等部分 case 因表描述和 profile 更容易定位，直接从 partial/incorrect 提升到 correct。
- 但 retrieve 仍不是可靠的通用 router：月份、粒度、省级/市州级、2025年12月基础业务字段等硬约束会被语义描述冲淡。
- 下一步不应继续堆 prompt，而应做结构化 query parser + deterministic candidate filtering + catalog rerank；同时补 gold table mapping / Recall@k，用召回指标定位问题。
- `gold_case_039` 单条耗时约 16 分钟、tokens 约 245 万，说明 per-case max iterations / max elapsed / max tool calls 是下一轮 P0。
