# TableClaw Framework Comparison Design

Date: 2026-06-22
Status: design approved for planning

> 说明：后续 TableClaw 内部 spec 和 plan 默认使用中文；只有对外英文读者或上游框架引用需要英文时再切换。

## Purpose

This design defines a small, controlled benchmark to test whether the current Nanobot-based TableClaw runtime is limiting table-agent capability. The benchmark should compare agent frameworks while keeping the model, tools, data, prompt, workspace, domain pack, and judge as constant as possible.

The first-round model is fixed to the current TableClaw mainline model:

```text
answer model: deepseek-v4-pro
judge model: deepseek-v4-pro
provider: DashScope OpenAI-compatible API
temperature: use the existing low-temperature eval config unless a run explicitly says otherwise
```

The experiment should not mix `deepseek-v4-pro` results with earlier GPT-5.5 reference runs or any other answer-model plan.

## Questions

The benchmark should answer four concrete questions:

1. Does Nanobot's current implicit agent loop limit complex table workflow reliability?
2. Does an explicit state graph improve table grounding, repair, and long multi-step tasks?
3. Does a verifier or multi-agent pattern improve robustness on sparse, dirty, or ambiguous table cases?
4. If stronger frameworks do not improve results, are the remaining bottlenecks mainly in tools, domain knowledge, dataset quality, or evaluation?

## Current Repo Fit

The current repository already has most of the benchmark substrate:

- `eval_test/run_gold_parallel_eval.py` loads tasks, renders prompts, retries transient model failures, calls the judge, computes deterministic metrics, writes JSONL/JSON/Markdown outputs, and summarizes tool usage.
- `eval_test/run_eval.py::render_prompt()` contains the current compact workflow prompt and task wrapping.
- `nanobot/nanobot/agent/tools/tableclaw.py` contains the core TableClaw tools for domain knowledge, table catalog, retrieval, inspect, matrix extraction, series extraction, ranking, top-k, and filtering.
- Nanobot `Tool` objects already expose `name`, `description`, JSON-schema `parameters`, and async `execute()`, so they can be adapted to other frameworks without rewriting tool logic.
- `domain_packs/sichuan-finance/` and `workspace/domain_knowledge/` already separate domain knowledge from generic tools.

The smallest useful change is therefore a framework runner abstraction under the evaluator, not a Nanobot core rewrite.

## Non-Goals

This first round will not:

- replace Nanobot in the product path;
- rewrite `nanobot/nanobot/agent/runner.py` or `loop.py`;
- create a new benchmark dataset from scratch;
- evaluate Excel/WPS/Sheets plugins;
- judge chart visual quality beyond the current chart-data correctness policy;
- compare different answer models.

## Framework Groups

### Baselines

`nanobot-current`
: Current TableClaw Nanobot runner using the low-temperature eval config. This is the main baseline.

`nanobot-skill-off`
: Existing no-xlsx/table-skill config, used to separate framework behavior from skill/context contribution.

`tablepipeline-v2`
: 新版自研 TablePipeline baseline。它不是通用 agent framework，也不走 TableClaw tools；它是另一条自研表格问答 pipeline，包含意图识别、问题改写、表格召回、Python agent loop、结果汇总和报告生成。它用于回答“新版自研 pipeline 相比 Nanobot TableClaw 是否仍有优势/可迁移模块”，报告中必须单列为 self-developed pipeline baseline，不能和 OpenAI Agents SDK / LangGraph / AutoGen 的同工具集框架对比混为一谈。

### Framework Comparisons

`openai-agents-sdk`
: Lightweight mature single-agent loop. This tests whether a small production-grade runtime with built-in tool loop, sessions, guardrails, and tracing improves over Nanobot without introducing graph complexity.

`langgraph`
: Explicit state/workflow runtime. This tests the core hypothesis that durable state, graph structure, verifier edges, and repair loops improve table workflows.

`autogen`
: Multi-agent comparison. This tests whether Planner / Analyst / Verifier separation improves hard cases. AutoGen should be implemented after the single-agent adapters so multi-agent variables do not obscure first-round results.

PydanticAI is deferred to a second round. It is useful for typed-output experiments, but it is less directly aligned with the current question than OpenAI Agents SDK, LangGraph, and AutoGen.

## Architecture

Add a runner layer below the existing evaluator:

```text
task JSONL
  -> load_tasks()
  -> render_prompt(task)
  -> FrameworkRunner.run(prompt, task, run_context)
       -> NanobotRunner
       -> TablePipelineV2Runner
       -> OpenAIAgentsRunner
       -> LangGraphRunner
       -> AutoGenRunner
  -> judge_answer()
  -> deterministic_metrics()
  -> build_summary()
  -> JSONL / JSON / Markdown report
```

The existing `evaluate_one()` should call a runner interface rather than directly constructing `Nanobot`.

Suggested interface:

```python
class FrameworkRunResult(TypedDict):
    answer: str
    usage: dict[str, Any]
    elapsed_ms: int
    tools_used: list[str]
    tool_timeline: list[dict[str, Any]]
    retrieval_tool_called: bool
    inspect_tool_called: bool
    tableclaw_tools_used: list[str]
    skill_selected: bool
    selected_skills: list[str]
    framework_trace: dict[str, Any]

class FrameworkRunner(Protocol):
    name: str
    async def run(self, task: dict[str, Any], prompt: str, run_id: str) -> FrameworkRunResult: ...
```

The result shape should preserve fields already consumed by `build_summary()` and Markdown report generation.

`tablepipeline-v2` 的适配入口是外部目录 `/Users/glenxin/Desktop/TableAgent/tablepipeline-2/` 中的 `pipeline.TablePipeline`。该 runner 使用 `task["question"]` 作为输入，而不是 `render_prompt()` 后的 TableClaw workflow prompt，因为新版 pipeline 自带意图识别和 query rewriting；强行喂 TableClaw prompt 会污染它的分类器和问题改写。

## Tool Adapter

Introduce a `TableClawToolAdapter` that exposes the same underlying TableClaw tools to every framework.

Responsibilities:

- instantiate Nanobot `Tool` classes with a workspace-aware `ToolContext`;
- expose each tool's `name`, `description`, and JSON-schema `parameters`;
- validate and cast tool inputs with the existing `Tool.cast_params()` and `Tool.validate_params()`;
- call `await tool.execute(**params)`;
- record a normalized tool timeline event for every call;
- keep domain-specific behavior inside `tableclaw_domain_knowledge` and the domain pack, not in framework-specific wrappers.

First-round tools:

- `tableclaw_domain_knowledge`
- `tableclaw_retrieve_tables`
- `tableclaw_inspect`
- `tableclaw_extract_matrix`
- `tableclaw_time_series`
- `tableclaw_horizontal_series`
- `tableclaw_topk`
- `tableclaw_rank`
- `tableclaw_filter`

Optional fallback tools such as read-only file access or a constrained Python executor can be added only if every framework receives the same version.

## Prompt And Output Contract

Use the existing `render_prompt()` wording for first-round comparability. Do not force an identical fixed tool sequence; the point is to observe framework behavior under the same task goal and tool affordances.

Each framework should return a normal final answer string because the current judge evaluates the final answer. A structured sidecar trace should be recorded separately. Strict final JSON output is deferred unless a later run specifically measures schema compliance.

## LangGraph Design

The LangGraph runner should use explicit state:

```text
query
prompt
domain_guidance
retrieved_tables
inspected_tables
intermediate_results
candidate_answer
verification
final_answer
tool_timeline
errors
iteration_count
```

Minimal graph:

```text
Start
  -> domain_or_route
  -> retrieve
  -> inspect
  -> solve
  -> verify
  -> final
```

If `verify` finds missing table evidence, wrong scope, or an execution/tool error, it can loop back to `retrieve`, `inspect`, or `solve` with a small `max_repair_iterations` cap. The verifier should check evidence consistency and answer completeness; it should not receive gold answers.

## OpenAI Agents SDK Design

The OpenAI Agents SDK runner should be a single specialist agent with the same TableClaw tools. It should test whether a production-grade light runtime improves tool execution, tracing, sessions, or output stability without explicit graph state.

First-round behavior:

- one table analyst agent;
- same prompt;
- same TableClaw tools;
- optional instruction to list used tables and completion status;
- no separate verifier agent in the first pass, so it remains a lightweight baseline.

## AutoGen Design

The AutoGen runner should start with a minimal multi-agent team:

- Planner: interprets the question and chooses table/domain strategy.
- Analyst: calls TableClaw tools and performs spreadsheet reasoning.
- Verifier: checks whether the answer cites the right table/month/scope/metric and asks for one repair when needed.

To control cost and noise:

- cap total turns;
- cap repair attempts;
- record agent-message trace;
- keep the same tool set as other frameworks;
- do not let the Verifier see gold answers.

## Dataset Plan

Use existing datasets first:

1. Smoke: 10 cases from `bad_cases.jsonl`.
2. Focused: 20-30 cases balanced across `ranking_qa`, `chart_generation`, `trend_table`, `filter_qa`, and `table_qa`.
3. Stability: repeat the focused set at least three times for each framework at the same concurrency setting.

The 5-level difficulty dataset proposed in the external guidance is useful later, but it should not block the first framework comparison.

## Metrics

Reuse existing metrics:

- judge ACC over scored cases;
- raw ACC including gold/task issue cases;
- numeric F1;
- entity F1;
- elapsed time;
- token usage when available;
- runtime error rate;
- retrieval and inspect call rates;
- TableClaw tool usage counts;
- selected skill rate for Nanobot baselines.

Add framework comparison metrics:

- repair-loop count;
- verifier rejection count;
- verifier repair success rate;
- max-iteration hit rate;
- average framework steps;
- tool validation error count;
- trace completeness rate.

## Reporting

Write framework comparison outputs under:

```text
eval_test/results/framework_comparison/<dataset>/<run_group>/
```

Suggested files:

- `latest_results.jsonl`
- `latest_summary.json`
- `latest_report.md`
- `runs/<run_id>_results.jsonl`
- `runs/<run_id>_summary.json`
- `traces/<run_id>/<framework>/<task_id>.json`

Archive human-readable milestones under:

```text
docs/实验评测/gold-cases/runs/YYYY-MM-DD-framework-comparison-<label>.md
```

The report must state:

- answer model and judge model;
- framework versions;
- dataset file and case selection rule;
- prompt version;
- tool set;
- concurrency;
- whether caches were warm or cold.

## Interpretation Rules

Use these rules to interpret outcomes:

- If LangGraph improves hard cases or reduces repair/runtime failures, Nanobot's implicit state and workflow control are likely a bottleneck.
- If OpenAI Agents SDK matches LangGraph, the bottleneck is probably not graph structure; focus on tool schemas, prompt, trace, and output constraints.
- If AutoGen improves sparse or ambiguous cases but costs much more, consider adding a verifier step to TableClaw rather than adopting full multi-agent runtime.
- If Nanobot remains competitive, prioritize table tools, domain knowledge, retrieval gold mapping, and evaluator cleanup before framework replacement.
- If all frameworks fail on the same cases, classify those cases as tool/domain/eval/data issues rather than framework issues.

## Security And Hygiene

Before publishing results or sharing the repo, remove hardcoded API-key fallbacks from shell scripts and require `DASHSCOPE_API_KEY` from the environment. Do not print or archive secrets in traces.

Framework traces should store reasoning summaries, tool names, arguments, outputs, errors, and state transitions. They should not store raw provider secrets or unrelated workspace files.

## Implementation Phases

Phase 0: hygiene and baseline preservation
: Remove API-key fallbacks, preserve current Nanobot result compatibility, and add a CLI option such as `--framework`.

Phase 1: runner abstraction
: Extract the current Nanobot call path into `NanobotRunner` and prove identical output shape against the existing evaluator.

Phase 2: tool adapter
: Wrap TableClaw tools once and reuse them across all non-Nanobot runners.

Phase 3: OpenAI Agents SDK runner
: Implement the lightweight single-agent comparison.

Phase 4: LangGraph runner
: Implement explicit state, verifier, and capped repair loop.

Phase 5: AutoGen runner
: Implement the minimal Planner / Analyst / Verifier team.

Phase 6: comparison report
: Run smoke, focused, and stability sets; write a milestone report with the interpretation rules above.

## Success Criteria

The first round is complete when:

- all selected frameworks can run the same task subset with `deepseek-v4-pro`;
- every run writes the existing result fields plus framework trace fields;
- Nanobot baseline results remain comparable to the current runner;
- at least one smoke and one focused comparison report are archived;
- the report makes a clear call on whether the evidence points to framework bottleneck, tool/domain bottleneck, or inconclusive results.
