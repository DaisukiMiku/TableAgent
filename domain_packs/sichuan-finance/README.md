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
├── knowledge/
│   └── tableclaw_industrial_finance.json
└── skills/
    └── sichuan-finance/
        └── SKILL.md
```

## Runtime Mounting

`./start.sh` syncs this pack into the local runtime workspace:

```text
workspace/skills/sichuan-finance/SKILL.md
workspace/domain_knowledge/tableclaw_industrial_finance.json
```

The `tableclaw_domain_knowledge` tool reads the workspace copy first, then falls back to this committed pack.

## Development Rule

Do not put Sichuan-specific business facts into generic tools such as `rank`, `filter`, `extract_matrix`, or `time_series`.

The intended loop is:

```text
bad case / trace
-> update memory, domain knowledge, or skill
-> targeted eval
-> full40 / badcase regression
-> decide whether to keep it in the domain pack or generalize into tools
```
