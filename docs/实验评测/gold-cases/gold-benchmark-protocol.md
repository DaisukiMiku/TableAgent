# Gold Cases Benchmark Protocol

> Last updated: 2026-06-14
> Dataset: `eval_test/test_dataset/gold_cases.jsonl`
> Runner: `./eval_gold_parallel.sh --concurrency 8`

## Purpose

This benchmark evaluates the current TableClaw workflow on 40 curated spreadsheet tasks with gold answers. It is intended as a repeatable baseline: after retrieval, skill, context, or tool improvements, rerun the same command and compare against the baseline below.

The benchmark checks the full workflow, not just answer generation:

1. User asks a question without an explicit table path.
2. Uploaded tables already exist in `workspace/uploads/`.
3. Nanobot retrieves likely tables with TableClaw tools.
4. Nanobot inspects candidate table schemas.
5. Nanobot chooses table skills and uses Python/openpyxl when needed.
6. The final answer is judged against `gold_answer`.

Gold answers are not included in the model prompt. They are used only after answer generation by the evaluator.

## Model Prompt

For each gold or badcase task, `eval_test/run_eval.py::render_prompt()` wraps the original user question with compact workflow instructions. The current prompt intentionally avoids forcing a fixed tool sequence; it asks the agent to choose reliable tools/skills/code, avoid reading all uploads into context, and report the tables used.

```text
用户问题：
{question}

这是 TableClaw workflow 评测。用户已将相关工业表上传到 workspace/uploads，但没有显式指定文件路径。

这是人工整理的 gold case。标准答案只给评测器使用，不能假设或引用标准答案。

执行要求：
1. 请自主选择最可靠的方式完成任务，可以使用可用工具、skill 或简短代码，但不要假设标准答案或 gold table path。
2. 不要把所有上传表完整塞入上下文；优先围绕问题中的时间、指标、地域/单位和表名线索选择相关表格。
3. 如果候选表不足或字段缺失，请明确说明，并基于最相关表格给出 best-effort 结果。
4. 如果这是画图/可视化类任务，本轮评测只要求输出可用于绘图的底层数据表，不需要真正生成图片文件。
5. 最后列出使用的表文件名，并说明是否成功完成。
```

For non-visual tasks, item 4 becomes:

```text
请直接回答问题，并说明使用了哪些上传表。
```

## Workflow Under Test

The benchmark uses the `skill-on` Nanobot config:

- Config: `nanobot/configs/tableclaw-bailian-dashscope.json`
- Answer model: `deepseek-v4-pro`
- Workspace: `workspace/`
- Upload directory: `workspace/uploads/`
- Table index: `workspace/table_index/tables.jsonl`
- Schema cache: `workspace/table_cache/*.schema.json`

Expected tool flow:

1. `tableclaw_retrieve_tables(query, top_k=8)` returns candidate spreadsheet paths, schema summaries, scores, and reasons.
2. `tableclaw_inspect(path)` returns sheet names, row/column counts, header candidates, column profiles, samples, and merged-cell hints.
3. The agent may read table/domain skills. In the current Sichuan finance run, `sichuan-finance` is synchronized from `domain_packs/sichuan-finance/` into `workspace/skills/`.
4. The agent executes spreadsheet analysis, usually through Python/openpyxl.
5. The evaluator records tool timeline, selected skills, token usage, elapsed time, and final answer.

## Judge Method

The judge is implemented in `eval_test/run_gold_parallel_eval.py`.

LLM judge:

- Model: `deepseek-v4-pro`
- API: DashScope OpenAI-compatible endpoint
- `temperature=0`
- `enable_thinking=false` when supported
- Prompt version: `data-correctness-v2-2026-06-14`
- Output schema:

```json
{
  "label": "correct|partial|incorrect",
  "passed": true,
  "score": 0.0,
  "reason": "short Chinese explanation",
  "missing": [],
  "extra_errors": []
}
```

Judge prompt summary:

```text
Question:
{question}

Gold answer:
{gold_answer}

Model answer:
{answer}

- Judge data correctness first: table/month/scope, entities, metric columns, values, units, filters, ranking direction, and required calculations.
- For chart/visualization tasks, judge only chart data correctness; do not penalize missing image rendering, Markdown layout, chart style, or narrative commentary.
- Ignore whether the answer used a particular tool, skill, code style, trace format, or long explanation.
- Accept equivalent unit conversions, percentage vs ratio notation, and reasonable rounding.
- `correct` means all core requested facts are present and correct.
- `partial` means some important facts are correct but one or more key rows/fields/orderings are missing or wrong; it does not count as passed.
- `incorrect` means wrong table/month/scope/metric, material cohort error, fabricated values, or missing the core result.
```

Deterministic metrics:

- `numeric_f1`: extracts numbers from answer and gold answer; tolerates small rounding differences and percent/decimal equivalence.
- `entity_f1`: extracts core province/city/metric terms and computes entity overlap.

Primary benchmark accuracy is `LLM judge ACC = count(passed=true) / total_cases`. `partial` cases are reported separately and are not counted as passed.

## Baseline Result

Run:

```bash
./eval_gold_parallel.sh --concurrency 8
```

Run metadata:

- Started: `2026-06-10T13:19:48+0800`
- Finished: `2026-06-10T13:43:11+0800`
- Cases: 40
- Answer model: `deepseek-v4-pro`
- Judge model: `deepseek-v4-pro`
- Runtime errors: 0

Overall:

| Metric | Value |
| --- | ---: |
| LLM judge ACC | 40.00% |
| Correct / Partial / Incorrect | 16 / 7 / 17 |
| Avg judge score | 0.4800 |
| Macro numeric F1 | 0.4131 |
| Macro entity F1 | 0.6004 |
| Retrieval call rate | 100.00% |
| Inspect call rate | 100.00% |
| Skill selection rate | 90.00% |
| Total answer tokens | 14,187,768 |
| Total judge tokens | 42,700 |
| Avg elapsed time | 208.07s |

By task type:

| Task type | Count | ACC | Main observation |
| --- | ---: | ---: | --- |
| `ranking_qa` | 11 | 81.82% | Strongest current capability; ranking/query tasks mostly work. |
| `chart_generation` | 22 | 27.27% | Weakest major group; often selects wrong table/scope or wrong province set. |
| `table_qa` | 3 | 33.33% | Mixed; missing fields and wrong aggregation scope still appear. |
| `trend_table` | 2 | 0.00% | Fails on complete 12-month series extraction. |
| `filter_qa` | 2 | 0.00% | Fails on multi-condition province filtering. |

Full per-case report:

- `eval_test/results/gold_cases/parallel/latest_report.md`
- `eval_test/results/gold_cases/parallel/latest_results.jsonl`
- `eval_test/results/gold_cases/parallel/latest_summary.json`

Note: the markdown `Case Comparison` table uses shortened previews for readability. Full `question` / `gold_answer` / `answer` / judge metadata are always preserved in `latest_results.jsonl`; newer markdown reports also include a `Case Details` section with full answers.

## Current Findings

The workflow orchestration is already active: all 40 cases called retrieval and inspect, and 90% selected at least one table skill. The main failure is not lack of tool invocation, but unstable table grounding and column/range selection.

Main error modes:

- Province-level tasks sometimes use city-level tables.
- “200亿省” scope is not consistently resolved to the correct province set.
- Chart tasks often output incomplete data tables or wrong ordering.
- Trend tasks fail to collect full 12-month series.
- Filter tasks miss conjunction logic across multiple metrics/ranks.
- Token cost is very high because the model repeatedly explores schema, reads result files, and writes custom openpyxl scripts.

## Next Comparison

After optimization, rerun:

```bash
./eval_gold_parallel.sh --concurrency 8
```

Compare at minimum:

- Overall LLM judge ACC
- `ranking_qa` ACC
- `chart_generation` ACC
- `trend_table` ACC
- `filter_qa` ACC
- Total answer tokens
- Avg elapsed time
- Retrieval / inspect / skill selection rates

Recommended next engineering targets before the next benchmark:

- stronger mandatory override reconciliation for sparse tables
- clearer `TOP/前N/最高` vs `最低/低风险` ranking semantics
- target-field checks for questions that provide values and ask for rank/conclusion
- gold-suspect annotations for reporting口径 conflicts
- lower-token extraction paths for long chart/trend tasks
