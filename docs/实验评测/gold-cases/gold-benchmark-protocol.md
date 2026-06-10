# Gold Cases Benchmark Protocol

> Last updated: 2026-06-10  
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

For each gold case, `eval_test/run_eval.py::render_prompt()` wraps the original user question with the following workflow instructions:

```text
用户问题：
{question}

这是 TableClaw workflow 评测。用户已将相关工业表上传到 workspace/uploads，但没有显式指定文件路径。

这是人工整理的 gold case。标准答案只给评测器使用，不能假设或引用标准答案。

执行要求：
1. 如问题涉及表格，请先调用 `tableclaw_retrieve_tables(query=用户问题, top_k=8)` 从上传表中召回候选表。
2. 对最相关候选表调用 `tableclaw_inspect(path=候选表路径)` 查看 sheet、表头、列和样例值；不要直接 `read_file` 读取 `.xlsx` 二进制表。
3. 再按需读取合适的表格 skill，例如 xlsx、table-read、table-chart、table-clean、table-validate。
4. 这是快速 workflow 评测，不追求本轮答案 100% 准确。最多检查召回结果里的前三个候选表；不要扫描整个 uploads 目录。
5. 如果前三个候选表不足以完成任务，请明确说明“候选表不足/字段缺失”，然后基于最相关候选表给出 best-effort 结果。
6. 使用召回到的候选表路径读取表格并完成分析；不要假设标准答案或 gold table path。
7. 如果这是画图/可视化类任务，本轮评测只要求输出可用于绘图的底层数据表，不需要真正生成图片文件。
8. 最后列出使用的表文件名，并说明是否成功完成。
```

For non-visual tasks, item 7 becomes:

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
3. The agent may read table skills such as `xlsx`, `table-read`, `table-chart`, `table-clean`, and `table-validate`.
4. The agent executes spreadsheet analysis, usually through Python/openpyxl.
5. The evaluator records tool timeline, selected skills, token usage, elapsed time, and final answer.

## Judge Method

The judge is implemented in `eval_test/run_gold_parallel_eval.py`.

LLM judge:

- Model: `deepseek-v4-pro`
- API: DashScope OpenAI-compatible endpoint
- `temperature=0`
- `enable_thinking=false` when supported
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

Judge prompt:

```text
Question:
{question}

Gold answer:
{gold_answer}

Model answer:
{answer}

Evaluation notes:
- For chart tasks, judge only whether the underlying data values, labels, units, and conclusions match the gold answer. Do not penalize missing image aesthetics if the answer provides the data needed for the chart.
- For table QA tasks, judge semantic correctness against the gold answer.
- Accept equivalent unit conversions, formatting differences, and reasonable rounding.
- Mark partial if some key numbers/entities are correct but important fields are missing or wrong.
- Mark incorrect if the answer uses the wrong table/month/scope, fabricates values, or misses the core requested result.
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

- `docs/实验评测/gold-cases/latest-parallel-eval-summary.md`
- `eval_test/results/gold_cases/parallel/latest_results.jsonl`
- `eval_test/results/gold_cases/parallel/latest_summary.json`

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

- `tableclaw_locate_column`
- `tableclaw_extract_series`
- `tableclaw_topk`
- `tableclaw_filter`
- `tableclaw_chart_data`
- stronger “200亿省” / province-vs-city scope handling
