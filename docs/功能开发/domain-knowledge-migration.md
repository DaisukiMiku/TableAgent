# Domain Knowledge Migration

> Updated: 2026-06-17

## Goal

Migrate useful business knowledge from the legacy `tablepipeline` implementation without hard-coding it into generic TableClaw algorithms.

The migration follows the current TableClaw layering principle:

- Core Agent / Runtime remains generic and should not absorb customer-specific business rules.
- Generic Table Tools handle cross-domain spreadsheet structure, extraction, ranking, filtering, time series, and validation.
- Skill, domain knowledge, and memory carry procedural guidance, stable business context, and task/user/session history.
- Eval and trace provide evidence for deciding what should stay in memory/domain pack, what should become a skill, and what is stable enough to become a generic tool.

## What Was Migrated

Source materials:

- `补充/业务经验.md`
- `补充/指标知识库.xlsx`
- `补充/tablepipeline/指标知识库1126.xlsx`
- `补充/tablepipeline/knowledge_data/experiences_excel/*.xlsx`
- `补充/tablepipeline/knowledge_data/query_rewriting/sichuan_county_region_units.json`

Migrated knowledge:

- Indicator-to-table-family mappings.
- Indicator synonym dictionary.
- Business cohort: `200亿省`.
- 四川 21 市州 list and county/region unit aliases.
- Ranking direction and summary-row filtering rules.
- 欠费台账 formulas and table-family hints.
- Historical decomposition/code-generation experiences.
- Derived metric modifiers such as `同比增幅`, `环比增幅`, and `排名列`.

## Layered Architecture

TableClaw treats domain support as a pluggable layer above generic spreadsheet execution:

```text
Agent Core / Runtime
  -> context assembly: skill / domain knowledge / memory / artifacts
  -> planning and domain strategy
  -> generic TableClaw tools and optional domain tools
  -> answer with evidence
  -> trace, eval, and memory candidates
```

Responsibilities:

| Layer | Responsibility | Boundary |
| --- | --- | --- |
| Skill | Tell the model how to approach a class of tasks, including when to retrieve domain context before extraction. | It is not an answer bank and should not contain final numeric answers. |
| Domain knowledge | Return structured business context: cohorts, aliases, table-family hints, ranking policy, sparse-table warnings, and stable bad-case knowledge. | It provides planning context, not final evidence. |
| Memory | Preserve working/session/long-term context such as active files, user confirmations, team preferences, and recent tool results. | It must have scope and provenance; it should not silently overwrite stable domain knowledge. |
| Generic tools | Execute deterministic table operations: retrieval, inspect/schema cache, matrix extraction, ranking, filtering, time series, validation. | They should remain domain-independent and should not hard-code Sichuan finance rules. |

In short: skill is the strategy manual, domain knowledge is stable business context, memory is dynamic task/user context, and TableClaw tools are executors.

## Injection Design

The committed domain pack is stored outside the generic TableClaw runtime:

```text
domain_packs/sichuan-finance/
├── knowledge_src/
│   ├── cohorts.json
│   ├── regions.json
│   ├── ranking_policy.json
│   ├── indicator_synonyms.json
│   ├── indicator_mappings.jsonl
│   ├── recommended_plans.jsonl
│   ├── validation_overrides.jsonl
│   └── experiences/
├── knowledge/tableclaw_industrial_finance.json
├── scripts/build_knowledge.py
├── scripts/validate_knowledge.py
└── skills/sichuan-finance/SKILL.md
```

`knowledge_src/` is the human-maintained source. `knowledge/tableclaw_industrial_finance.json` is the compiled runtime artifact kept for compatibility with `tableclaw_domain_knowledge`.

The build contract is:

```text
knowledge_src/* + skills/*
-> validate_knowledge.py
-> build_knowledge.py
-> knowledge/tableclaw_industrial_finance.json
-> sync_domain_pack.sh
-> workspace/domain_knowledge/tableclaw_industrial_finance.json
```

This keeps the high-accuracy runtime path unchanged while making the source knowledge reviewable by section.

At startup, `./start.sh` mounts this pack into the local runtime workspace:

```text
workspace/domain_knowledge/tableclaw_industrial_finance.json
workspace/skills/sichuan-finance/SKILL.md
```

The model accesses the JSON through a read-only tool:

```text
tableclaw_domain_knowledge
```

A lightweight workspace skill routes relevant questions to this tool:

```text
workspace/skills/sichuan-finance/SKILL.md
```

This keeps business facts outside `rank`, `filter`, `extract_matrix`, and other generic table algorithms. The tool returns planning guidance only; exact numeric answers still must be read from uploaded tables.

The `tableclaw_domain_knowledge` tool reads `workspace/domain_knowledge/` first, then falls back to the committed `domain_packs/sichuan-finance/` copy. This makes local customer/project overrides possible without changing generic code.

When editing domain knowledge, update files under `knowledge_src/`, then run:

```bash
python3 domain_packs/sichuan-finance/scripts/validate_knowledge.py
python3 domain_packs/sichuan-finance/scripts/build_knowledge.py
```

Do not edit the compiled JSON directly unless doing an emergency rollback.

## Promotion Principle

```text
trace / badcase
-> memory, domain knowledge, or skill candidate
-> targeted eval
-> wider regression
-> keep in domain pack or generalize into tools
```

Business knowledge should be promoted carefully:

- Put temporary user confirmations and session-specific constraints in memory.
- Put stable customer-specific facts in the domain pack.
- Put reusable spreadsheet procedures in skills.
- Put deterministic, domain-independent operations in generic tools.
- Keep the base agent runtime unchanged unless the need is framework-level.

## Usage Policy

- Use uploaded table values whenever the table has complete fields.
- Use domain cohort knowledge when the user uses business shorthand or the table has sparse cohort fields.
- If user explicitly provides a cohort list, use the user-provided list.
- If domain knowledge supplies the cohort or formula, mention that口径 briefly in the answer.
- Do not treat domain knowledge as final numeric evidence.

## Retrieval Behavior

`tableclaw_domain_knowledge` returns only the sections relevant to the query:

- matching cohorts such as `200亿省`;
- indicator synonyms such as `基础业务收入` -> `基础收入总额`;
- table-family mappings for matched canonical indicators;
- derived metric modifiers such as `同比增幅`;
- formulas and historical experiences when the query matches them;
- ranking policy and四川市州 lists when the question needs them.

The tool intentionally returns compact planning context. The next step is always a normal table workflow: retrieve candidate files, inspect structure, locate columns, extract/rank/filter values, and validate against uploaded tables.

## Next Evaluation

Run full40 after this migration and compare:

- Case 05 / 23 / 30 / 31: whether `200亿省` sparse-table cases improve.
- Case 06 / 37: whether欠费台账 questions use fewer ad hoc `exec` calls and produce more complete outputs.
- Overall accuracy and token cost against the previous GPT-5.5 warm-cache baseline.
