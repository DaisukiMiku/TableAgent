---
name: "sichuan-finance"
description: "Use for Sichuan finance/industrial spreadsheet questions that mention 200亿省, 欠费, 小微ICT, 一年以上, 市州/全省排名, 营业收现率, 预收, 保证金, or ambiguous business metric names; retrieve domain knowledge before table extraction."
---

# Sichuan Finance Domain Skill

This is a domain-specific TableClaw skill for the current Sichuan finance/industrial spreadsheet workspace.

It should carry business terminology, cohort definitions, table-family hints, ranking conventions, and historical bad-case experience. It must not replace the generic TableClaw tools. Exact values still come from uploaded spreadsheets.

## When To Use

Read this skill, then call `tableclaw_domain_knowledge`, when the query mentions any of:

- `200亿省`, `200亿收入`, `主要大省`, `大省`
- `欠费`, `已列收`, `未列收`, `一年以上`, `小微ICT`
- `市州排名`, `全省排名`, `全国排名`
- `营业收现率`, `经营活动现金流入`, `预收`, `保证金`, `未认领`
- Metric names that may need synonyms or table-family mapping.

## Workflow

1. Call `tableclaw_domain_knowledge(query=...)` to get only relevant business context from `workspace/domain_knowledge/` or the packaged fallback.
2. Use the returned cohort, indicator synonyms, table mappings, formulas, and ranking direction as planning guidance.
3. Then call `tableclaw_retrieve_tables` and the normal table tools (`inspect`, `rank`, `filter`, `extract_matrix`, `time_series`) to validate exact files, rows, columns, and numeric values.
4. Do not treat domain knowledge as the numeric answer. Exact numbers must come from uploaded tables or explicit calculation.

## Important Rules

- If the user explicitly gives a cohort list, use the user's list.
- If the uploaded table has complete cohort fields and the query asks for threshold filtering, prefer dynamic filtering from the table.
- If a cohort field is sparse or many rows have only ranks/no values, use domain knowledge as a fallback planning source and say so briefly.
- For `200亿省` business-report questions, the legacy business cohort is: 广东、江苏、浙江、上海、四川、湖北、安徽、湖南. If a gold/reporting task uses a narrower displayed cohort, verify against the table and explain the口径.
- For 四川市州 ranking, limit the ranking universe to the 21 四川市州 and filter out summary rows such as 合计、市州合计、汇总、全省.
- Ranking direction is business-dependent. Risk/arrears/receivable ratios usually rank low-to-high; cash collection/prepayment/income type indicators usually rank high-to-low unless the table or user states otherwise.
