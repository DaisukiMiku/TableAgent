# Domain Knowledge Migration

> Updated: 2026-06-12

## Goal

Migrate useful business knowledge from the legacy `tablepipeline` implementation without hard-coding it into generic TableClaw algorithms.

The migration follows the project principle:

- General exploration remains available as fallback.
- Stable tools accelerate high-frequency spreadsheet paths.
- Skill/domain knowledge carries semi-structured business experience.
- Evaluation decides what should be solidified and what should stay open.

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

The next TableClaw architecture treats domain support as a pluggable layer above generic spreadsheet execution:

```text
Nanobot framework
  -> domain skill / strategy layer
  -> domain knowledge / memory / future RAG
  -> generic TableClaw table tools
  -> eval and bad-case feedback loop
```

Responsibilities:

| Layer | Responsibility | Boundary |
| --- | --- | --- |
| Domain skill | Decide when this domain applies and tell the model to retrieve domain context before extraction. | It is not an answer bank and should not contain final numeric answers. |
| Domain knowledge | Return structured business context: cohorts, aliases, table-family hints, ranking policy, sparse-table warnings, and bad-case memory. | It provides planning context, not final evidence. |
| Generic tools | Execute deterministic table operations: retrieval, inspect/schema cache, matrix extraction, ranking, filtering, time series, validation. | They should remain domain-independent and should not hard-code Sichuan finance rules. |

In short: skill is the strategy manual, domain knowledge is business memory, and TableClaw tools are executors.

## Injection Design

The committed domain pack is stored outside the generic Nanobot/TableClaw runtime:

```text
domain_packs/sichuan-finance/
├── knowledge/tableclaw_industrial_finance.json
└── skills/sichuan-finance/SKILL.md
```

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

## Promotion Principle

```text
generic exploration -> repeated pattern -> domain skill/domain knowledge or generic tool -> eval validation
```

Business knowledge should be promoted carefully:

- Put stable customer-specific facts in the domain pack.
- Put reusable spreadsheet procedures in skills.
- Put deterministic, domain-independent operations in generic tools.
- Keep the base agent framework unchanged unless the need is framework-level.

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
