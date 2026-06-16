# TableClaw 开发日志

> 最后更新：2026-06-16
>
> 本文件记录最近关键决策和上下文恢复信息。旧版千行流水日志已从主线文档中清理，历史细节可从 git 恢复。

## 2026-06-16

### V3 Final Eight-Way Eval + Gold-Issue Adjusted Metric

本轮在回退到 v3 主线后，完成 5 轮正式评测并归档：

- badcase122 x 2：`2026-06-16-final-v3-badcase-a/b`。
- query100 x 3：base、seed20260616、seed20260617。
- 追加稳定性复核：`2026-06-16-v3check-badcase-c`，以及 query100 seed20260618 / seed20260619。
- 新增 `gold_issue_flags` / `excluded_from_acc`：明显题面/gold 冲突、题面缺少年份但 gold 强行假设年份、残缺 query 不计入主 ACC。
- 8 轮合计：866 raw cases，排除 53 个 gold/task issue 后，813 scored cases official adjusted ACC 95.20%；保守 pre-scored ACC 92.50%。
- badcase122 official adjusted ACC 96.55%；query100 official adjusted ACC 94.19%。
- 正式归档：[2026-06-16-v3-final-gold-issue-adjusted](../实验评测/gold-cases/runs/2026-06-16-v3-final-gold-issue-adjusted.md)。

结论：当前版本已经能在四川财资 domain pack 主线上稳定接近 95%。后续重点不再是继续堆 domain JSON，而是做剩余错误的结构化归因：时间表达、指标别名、表族选择、sparse/reporting reconciliation。

### vnext Evaluation Stability

在 `baseline-v4rerun-20260616` tag 保存当前主线版本后，启动下一轮稳定性迭代：

- 新增低温评测配置：`nanobot/configs/tableclaw-bailian-dashscope-eval.json`，`temperature=0.2`。
- `eval_gold_parallel.sh` / `run_gold_parallel_eval.py` 默认使用低温评测配置；`start.sh` 仍使用交互配置，保留 `temperature=1.0`。
- 并行评测 session key 增加短 UUID，避免多 screen 同时启动时 session key 碰撞。
- 评测报告写入 agent config，便于后续区分交互配置和 benchmark 配置。

本轮原则：不继续追加业务 hardcode，不污染 generic table tools；先降低评测随机路径漂移，观察 badcase122 与 query100 的稳定性上限。

阶段性观察：

- 5 个 screen x 10 并发会触发 DashScope / DeepSeek `limit_burst_rate`，结果会被 429 runtime_error 污染；后续正式回归改为低并发。
- 新增 `eval_test/build_regression_subset.py`，用于从上一轮结果中抽取 failed / partial / runtime_error case，再混入少量 previously-correct case，形成快速迭代小集合。
- 新增 `eval_test/test_dataset/regression_badcase_vnext.jsonl`（22 条）与 `eval_test/test_dataset/regression_query_vnext.jsonl`（16 条），用于下一轮低并发快速回归。
- 修正四川财资 domain pack 中“一年以上应收账款排名”口径：同一表头组存在多个排名列时，必须绑定用户问题中的修饰语；问“一年以上应收账款 + 同比增幅 + 全省排名”时，使用“一年以上同比增幅”后的官方排名列，不能误用“一年以上占应收总额比”排名列。
- workflow eval prompt 增加 domain skill / domain knowledge 的优先使用规则，并要求命中 `mandatory_overrides` 时做 final reconciliation。

## 2026-06-15

### 文档口径收敛

本轮把根 README、docs 总览、实验评测入口、gold-cases 索引、TODO 和 domain pack 说明统一到当前口径：

- TableClaw 是 To C / 通用 Table Agent 能力栈，四川财资是第一个 domain pack 验证场景，不是项目边界。
- 对外定位不再把当前底座名字写成项目核心，避免后续底座替换时文档语义失真。
- 分层统一为 Core Agent / Runtime、Context / Storage Layer、Generic Table Tools、Domain Pack、Harness / Eval / Observability。
- Memory 被明确为上下文与存储层的一等能力，和 skill、domain knowledge 同层但定位不同。
- 长期展望可以包含更强的反馈和持续学习机制，但当前不把项目描述成已经完全自动自进化。

### Domain Overrides + Rank Filter 评测归档

已归档 `2026-06-15-domain-overrides-rank-filter`：

- Gold40 A/B 平均 ACC：78.75%。
- Badcase122 A/B/C 平均 ACC：88.25%，单次最高 90.98%。
- 相比上一轮，badcase122 平均从 87.30% 提升到 88.25%，单次最高从 87.70% 提升到 90.98%。
- gold40 从 80.00% 略降到 78.75%，主要瓶颈仍是 2025-12 `200亿省` 图表族 sparse/reporting fallback、预收排名 reporting 冲突和多条件 filter 工具选择稳定性。

结论：本轮改动保留在 domain pack 和 generic rank/filter 的合理边界内，badcase 有收益，但不继续为了单个 reporting 冲突污染通用工具。

## 2026-06-13

### 文档主线清理

本轮对 docs 做了一次收敛：

- 删除早期半成品/展示型文档：
  - `docs/实验评测/skill-matrix/`
  - `docs/实验评测/uploaded-table-workflow/`
  - `docs/实验评测/workflow-routing.md`
  - `docs/实验评测/gold-cases/smoke-eval-summary.md`
  - gold-cases `runs/` 下大量早期长篇逐题报告
- 保留正式主线：
  - `docs/README.md`
  - `docs/功能开发/`
  - `docs/实验评测/gold-cases/`
  - `docs/架构/project-structure.md`
  - `docs/项目管理/TODO.md`
- 保留关键 run 报告：
  - DeepSeek 80.00%：`2026-06-12-current-full40-after-horizontal-series.md`
  - GPT-5.5 82.50%：`2026-06-12-gpt55-current-full40.md`

目的：让文档重新服务当前研发主线，而不是沉积每次临时演示和试验噪声。

### DeepSeek V4 Pro 连通

用户提供新的 DeepSeek / DashScope key 后，已切回 `deepseek-v4-pro` 配置并验证 OpenAI-compatible 调用可用。

当前启动链路：

- `./start.sh`
- config：`nanobot/configs/tableclaw-bailian-dashscope.json`
- model：`deepseek-v4-pro`
- workspace：`workspace/`

### 通用 / 专用分层确认

当前开发原则：

```text
通用探索能力兜底
+ 稳定工具加速高频路径
+ skill/memory 承接半结构化经验
+ 评测闭环决定什么该固化、什么该保持开放
```

分层边界：

- Nanobot 不为四川财资特例改主循环。
- TableClaw generic tools 只做跨领域表格能力。
- 四川财资业务知识进入 `domain_packs/sichuan-finance/`。
- Badcase 先进入 domain pack / skill / eval 观察；只有跨领域稳定模式才上升为 generic tool。

### Domain Pack 接入

已接入：

- `domain_packs/sichuan-finance/knowledge/tableclaw_industrial_finance.json`
- `domain_packs/sichuan-finance/skills/sichuan-finance/SKILL.md`
- `tableclaw_domain_knowledge` tool

`start.sh` 启动时会同步到：

- `workspace/domain_knowledge/tableclaw_industrial_finance.json`
- `workspace/skills/sichuan-finance/SKILL.md`

领域工具只返回 planning guidance、指标别名、表族建议、cohort/ranking 口径；精确数值仍必须从上传表读取。

### 当前风险点

- 本小节为 2026-06-13 当时的风险快照；其中 badcase 清洗、工具统计一致性和 DeepSeek 复测已在 2026-06-16 完成。
- 当前风险以本文件顶部 `V3 Final Eight-Way Eval + Gold-Issue Adjusted Metric` 和 [TODO](TODO.md) 为准。
- 仍需持续关注：query rewrite 下的时间表达、指标别名、表族选择、sparse/reporting reconciliation。

### 200亿省 Cohort 小步迭代

问题：

- DeepSeek V4 Pro A/B full40 稳定在 65.00% / 67.50%。
- `ranking_qa` 和 `trend_table` 已稳定，但 `chart_generation` 只有约 50%，`filter_qa` 仍为 0%。
- 多个 chart partial 的直接原因是 `200亿省` 口径多带了湖北；当前 gold/reporting 默认是 7 省：广东、江苏、浙江、上海、四川、安徽、湖南。

改动：

- `domain_packs/sichuan-finance/knowledge/tableclaw_industrial_finance.json`：将 `200亿省` 默认 cohort 调整为 7 省，湖北保留为历史/动态阈值候选。
- `domain_packs/sichuan-finance/skills/sichuan-finance/SKILL.md`：明确当前 gold/reporting 默认不加入湖北。
- `tableclaw_extract_matrix`：当传入 `cohort="200亿省"` 且没有显式动态阈值参数时，优先从 domain knowledge 展开实体名单；只有显式给 `cohort_metric/cohort_min` 时才走动态阈值。
- `eval_gold_parallel.sh`：默认 key 与 `start.sh` 对齐到当前 DeepSeek V4 Pro key，避免 targeted eval 误走旧 key。

验证：

- targeted 6 case（5/19/20/22/29/40）在修正 cohort 后：4 correct / 1 partial / 1 incorrect。
- case19、case22、case29 从“多湖北导致 partial”变为 correct。
- case20 在 `extract_matrix` 自动解析 domain cohort 后，单条从 partial 变 correct。
- case40 从 incorrect 变 correct，说明 7 省 cohort 也改善了“两个指标同时前三”的交集判断。
- case5 仍 incorrect，原因是 2025-12 表内基础业务收入同比增幅对多省数值稀疏，gold 需要安徽/上海负增长；这不是单纯 cohort 能解决，后续需要 2025-12 sparse / 业务补全机制或 badcase/domain 进一步沉淀。

### DeepSeek after-cohort-fix full40 @4

在 domain cohort 修复和 `extract_matrix` 自动展开 `200亿省` 后，启动 4 轮 DeepSeek V4 Pro full40 稳定性复测：

- Run A：77.50%（31 correct / 4 partial / 5 incorrect）
- Run B：82.50%（33 correct / 3 partial / 4 incorrect）
- Run C：87.50%（35 correct / 2 partial / 3 incorrect）
- Run D：82.50%（33 correct / 3 partial / 4 incorrect）

@4 平均 ACC 为 82.50%，相较修复前 DeepSeek A/B 的 65.00% / 67.50% 明显提升。当前结论：

- `ranking_qa`、`table_qa`、`trend_table` 已较稳；
- `chart_generation` 提升明显，但 2025-12 sparse 表仍是长尾；
- `filter_qa` 是下一轮最优先优化类型；
- 领域知识进入 domain pack，再由工具读取，是目前最干净的“通用 + 专用”分层方式。

## 2026-06-12

### 当前最高 DeepSeek full40

归档 run：

- Run id：`2026-06-12-current-full40-after-horizontal-series`
- 报告：`docs/实验评测/gold-cases/runs/2026-06-12-current-full40-after-horizontal-series.md`

结果：

- ACC：80.00%（32 correct / 2 partial / 6 incorrect）
- Avg elapsed：110.45s / case
- Total answer tokens：12,906,668

结论：

- 工具返回可直接复用的底层数据表，是当前提升的核心。
- matrix/time-series/horizontal-series 比只返回低层 JSON 更容易让模型收口。
- ranking/table/trend 已较稳；filter 和复杂 chart 仍弱。

### GPT-5.5 full40 参考上限

归档 run：

- Run id：`2026-06-12-gpt55-current-full40`
- 报告：`docs/实验评测/gold-cases/runs/2026-06-12-gpt55-current-full40.md`

结果：

- ACC：82.50%
- Avg elapsed：56.44s / case
- Total tokens：7,019,124

定位：

- 用作强基模轨迹参考和上限估计。
- 不与 DeepSeek 主线指标直接混口径比较。

### 评测口径调整

用户确认图表题当前不应过度严格评判排版/画图质量。当前 judge 更关注：

- 底层数值是否正确。
- 实体范围是否正确。
- 口径/单位/排序是否正确。
- 是否能支持后续前端或 Python 图表渲染。

图形美观、颜色、布局和前端展示后置。

## 下一步恢复现场

1. 读 [TODO](TODO.md)，优先处理 P0。
2. 读最新评测归档：[2026-06-16-v3-final-gold-issue-adjusted](../实验评测/gold-cases/runs/2026-06-16-v3-final-gold-issue-adjusted.md)。
3. 对剩余错误做四类归因：`generic-tool` / `domain-knowledge` / `prompt-or-eval` / `gold-task-issue`。
4. 围绕 query rewrite 下的时间表达、指标别名、表族选择和 sparse/reporting reconciliation 做下一轮小步迭代。
5. 新增评测统一使用 `run_gold_parallel_eval.py` 当前口径，主 ACC 读取 `excluded_from_acc=false` 的 scored cases。
