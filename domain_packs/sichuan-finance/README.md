# Sichuan Finance Domain Pack

This domain pack is the current project-specific business layer for TableClaw.

It is intentionally separate from the generic Nanobot/TableClaw runtime:

- Nanobot remains the fixed agent framework.
- TableClaw tools remain generic spreadsheet workflow capabilities.
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
bad case -> update domain knowledge / skill -> targeted eval -> full40 eval -> decide whether to generalize into tools
```
