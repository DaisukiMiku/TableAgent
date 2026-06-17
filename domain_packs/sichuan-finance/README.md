# Sichuan Finance Domain Pack

This domain pack is the current project-specific business layer for TableClaw.

It is intentionally separate from the generic TableClaw runtime:

- Core Agent / Runtime remains responsible for generic agent execution, session, workspace, trace, and harness behavior.
- Generic TableClaw tools remain domain-independent spreadsheet workflow capabilities.
- Context / Storage Layer mounts skill, domain knowledge, memory/RAG, artifacts, and tool traces as task context.
- This pack carries Sichuan finance business terminology, cohorts, ranking policies, table-family hints, formulas, and bad-case knowledge.

## Contents

```text
domain_packs/sichuan-finance/
├── README.md
├── manifest.json
├── knowledge_src/
│   ├── meta.json
│   ├── cohorts.json
│   ├── regions.json
│   ├── ranking_policy.json
│   ├── indicator_synonyms.json
│   ├── indicator_mappings.jsonl
│   ├── table_families.json
│   ├── formulas.json
│   ├── recommended_plans.jsonl
│   ├── validation_overrides.jsonl
│   ├── derived_metric_modifiers.json
│   └── experiences/
│       ├── code_generation.jsonl
│       └── question_decomposition.jsonl
├── knowledge/
│   └── tableclaw_industrial_finance.json
├── scripts/
│   ├── build_knowledge.py
│   └── validate_knowledge.py
└── skills/
    └── sichuan-finance/
        └── SKILL.md
```

## Knowledge Source and Compiled Artifact

`knowledge_src/` is the human-maintained source of truth. It is split by responsibility so future bad-case fixes can be reviewed without editing one large JSON file:

- `cohorts.json`: stable business cohorts such as `200亿省`.
- `regions.json`: province/city/county aliases.
- `indicator_synonyms.json`: canonical metric names and aliases.
- `indicator_mappings.jsonl`: indicator-to-table-family routing hints.
- `recommended_plans.jsonl`: structured task routing guidance.
- `validation_overrides.jsonl`: sparse-table/reporting fallbacks with source and priority.
- `experiences/*.jsonl`: migrated legacy TablePipeline experience snippets.

`knowledge/tableclaw_industrial_finance.json` is a compiled runtime artifact. Nanobot and `tableclaw_domain_knowledge` continue to read this single JSON for compatibility and speed.

Use the helper scripts when editing the pack:

```bash
python3 domain_packs/sichuan-finance/scripts/validate_knowledge.py
python3 domain_packs/sichuan-finance/scripts/build_knowledge.py
```

## Runtime Mounting

`./start.sh` syncs this pack into the local runtime workspace:

```text
workspace/skills/sichuan-finance/SKILL.md
workspace/domain_knowledge/tableclaw_industrial_finance.json
```

The `tableclaw_domain_knowledge` tool reads the workspace copy first, then falls back to this committed pack.

During sync, `scripts/sync_domain_pack.sh` validates `knowledge_src/`, rebuilds the compiled JSON if needed, then copies the compiled artifact into `workspace/domain_knowledge/`.

## Development Rule

Do not put Sichuan-specific business facts into generic tools such as `rank`, `filter`, `extract_matrix`, or `time_series`.

The intended loop is:

```text
bad case / trace
-> update memory, knowledge_src, or skill
-> validate and rebuild compiled domain knowledge
-> targeted eval
-> full40 / badcase regression
-> decide whether to keep it in the domain pack or generalize into tools
```
