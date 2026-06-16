# Gold Case Benchmark Runs

> 每次正式 benchmark 需要保留指标摘要。`eval_test/results/**/parallel/**/latest_report.md` 是滚动结果，不作为唯一历史。

## Key Runs

| Run | Prompt / Workflow 特点 | ACC | Avg elapsed | Tokens | 结论 |
| --- | --- | ---: | ---: | ---: | --- |
| [V3 Final Five-Way Eval with Gold-Issue Exclusion](2026-06-16-v3-final-gold-issue-adjusted.md) | 回退到 v3 主线；badcase122 x2 + query100 x3；新 runner 排除明显 gold/task issue | all scored 95.70%; badcase avg 97.41%; query avg 94.28% | 见本地 adjusted reports | 见本地 adjusted reports | 当前最新主线口径：保留 raw ACC，同时用 `excluded_from_acc` 剥离题面/gold 问题。 |
| [Domain Overrides + Rank Filter](2026-06-15-domain-overrides-rank-filter.md) | rank filter 支持 + 202512 产数 Top3 fallback 加强 + 预收排名 reporting override；gold40 A/B 与 badcase122 A/B/C | gold40 avg 78.75%; badcase122 avg 88.25% | gold40 avg 131.97s; badcase avg 101.08s | gold40 avg 15,420,942; badcase avg 36,747,375 | badcase 平均小幅提升、单次最高 90.98%；gold40 略降，2025-12 200亿省图表族仍是主要短板。 |
| v1 baseline | retrieve + inspect + 按需 skill/code，不强推新增读算工具 | 40.00% | 208.07s | 14,187,768 | 第一版有效 baseline；ranking 强，chart/trend/filter 弱。 |
| v4 table catalog | 预先生成 catalog/profile/description，retrieve 融合 catalog 描述 | 47.50% | 229.85s | 18,784,002 | catalog 对召回有收益，但仍缺结构化意图和预算控制。 |
| v5 structured retrieval | 增加 intent、constraint score、table group discovery | 52.50% | 265.26s | 16,834,667 | 结构化召回继续提升，但长尾耗时明显。 |
| v7 rank official/header-path | rank tool、官方排名列、header path、百分比归一化 | 57.50% | 225.51s | 18,437,422 | chart/trend 改善，filter 仍弱。 |
| v9h answer markdown | matrix/time-series 返回可直接复制的 answer_markdown/chart table | 67.50% | 158.68s | 14,786,544 | 结构化底表直接输出显著提升 chart/table/trend。 |
| [current full40 after horizontal series](2026-06-12-current-full40-after-horizontal-series.md) | 在 answer_markdown 基础上增强横向序列/台账类底表输出 | 80.00% | 110.45s | 12,906,668 | DeepSeek 早期关键里程碑；ranking/table/trend 均 100%，chart 72.73%。 |
| [GPT-5.5 current full40](2026-06-12-gpt55-current-full40.md) | 当前代码接入 GPT-5.5，观察强基模上限、轨迹、耗时和 token | 82.50% | 56.44s | 7,019,124 | 强基模显著降低耗时和 token，可用于轨迹蒸馏；不与 DeepSeek 主线直接比较。 |
| v10 general fixes | 汇总行排除、half-up rounding、占比类排名、图表/跨期 prompt 约束 | 60.00% | 234.25s | 16,674,941 | 部分 chart 提升但 overall 回退，说明混合补丁需要拆成小步 A/B。 |
| [DeepSeek after cohort fix @4](2026-06-13-deepseek-v4pro-after-cohort-fix-at4.md) | 四川财资 domain pack + `200亿省` 7 省 cohort + `extract_matrix` 自动展开领域 cohort；4 次 full40 稳定性复测 | avg 82.50% | avg 172.61s | avg 15,566,046 | DeepSeek V4 Pro 达到 GPT-5.5 单次参考水平，且单次最高 87.50%；证明领域知识应通过可插拔 domain pack 进入工具链。 |
| [Mandatory overrides + judge v2](2026-06-14-mandatory-overrides-judge-v2.md) | `mandatory_overrides` 高优先级 domain fallback + `data-correctness-v2` judge；同时跑 gold40 A/B 和 badcase122 A/B | gold40 avg 80.00%; badcase122 avg 87.30% | gold40 avg 142.60s; badcase avg 105.13s | gold40 avg 17,004,866; badcase avg 36,224,218 | badcase 明显提升到约 87%；当前主要剩余问题集中在 2025-12 sparse 表、TOP 排序语义和少量疑似 gold/reporting 冲突。 |

## 记录规范

- 文件名建议：`YYYY-MM-DD-<run-id>.md`。
- 每份归档报告顶部必须说明 model、config、prompt strategy、tool exposure、skill behavior、main insight。
- 机器可读完整结果保存在 `eval_test/results/<dataset>/parallel/<run_group>/runs/<run_id>_results.jsonl` 和 `<run_id>_summary.json`。
- 旧长篇逐题报告不再全部放进 docs；只保留关键里程碑，避免文档目录被实验噪声淹没。
