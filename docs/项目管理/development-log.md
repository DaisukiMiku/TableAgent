# TableClaw 开发日志

> 最后更新：2026-06-13
>
> 本文件记录最近关键决策和上下文恢复信息。旧版千行流水日志已从主线文档中清理，历史细节可从 git 恢复。

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

- `eval_test/300条badcase.xlsx` 已出现但尚未清洗。
- 需要确认评测统计里的 `tableclaw_horizontal_series` 与当前代码实现是否完全一致。
- Domain pack targeted eval 只有小样本验证，尚未完成 DeepSeek full40 复测。
- 2025-12 sparse 表、多条件 filter、欠费台账仍是主要短板。

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
2. 清洗 `eval_test/300条badcase.xlsx`。
3. 把 badcase 分为 generic-tool / domain-knowledge / prompt-or-eval 三类。
4. 跑 domain pack targeted eval。
5. 跑 DeepSeek full40，更新 latest summary 和必要的 run 报告。
