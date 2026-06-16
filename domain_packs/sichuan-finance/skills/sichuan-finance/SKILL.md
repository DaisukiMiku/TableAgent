---
name: "sichuan-finance"
description: "Use for Sichuan finance/industrial spreadsheet questions that mention 200亿省, 欠费, 小微ICT, 一年以上, 市州/全省排名, 营业收现率, 预收, 保证金, or ambiguous business metric names; retrieve domain knowledge before table extraction."
---

# Sichuan Finance Domain Skill

This is a domain-specific strategy skill for the current Sichuan finance/industrial spreadsheet workspace.

It is the orchestration layer, not the execution layer:

- Skill: decide strategy and when to retrieve domain context.
- Domain knowledge: provide structured business memory such as cohorts, metric aliases, table-family hints, ranking conventions, and bad-case experience.
- Generic TableClaw tools: execute table retrieval, schema inspection, extraction, ranking, filtering, and validation.

Exact values must still come from uploaded spreadsheets or deterministic calculation.

## When To Use

Read this skill, then call `tableclaw_domain_knowledge`, when the query mentions any of:

- `200亿省`, `200亿收入`, `主要大省`, `大省`
- `欠费`, `已列收`, `未列收`, `一年以上`, `小微ICT`
- `市州排名`, `全省排名`, `全国排名`
- `营业收现率`, `经营活动现金流入`, `预收`, `保证金`, `未认领`
- Metric names that may need synonyms or table-family mapping.

## Strategy Workflow

1. Identify whether the user query is a Sichuan finance/industrial spreadsheet task.
2. Call `tableclaw_domain_knowledge(query=...)` to get relevant business context from `workspace/domain_knowledge/` or the packaged fallback.
3. If `tableclaw_domain_knowledge` returns `recommended_plans`, use them first as structured routing guidance. They specify the recommended metric, rank source, table family, entity universe, and tool arguments.
4. If it returns `mandatory_overrides`, check whether `applies_when` matches the user query. If it matches and the uploaded table is sparse/blank/conflicting, reconcile these override facts into the final answer instead of answering "无法确定".
5. If it returns other `validation_overrides`, use them only as domain/reporting fallback when the uploaded table is sparse, official rank columns are blank, or deterministic extraction conflicts with documented reporting口径.
6. Use the returned cohort, indicator synonyms, table mappings, formulas, sparse-table warnings, and ranking direction as planning guidance.
7. Call `tableclaw_retrieve_tables` to choose candidate uploaded files.
8. Call generic table tools (`tableclaw_inspect`, `tableclaw_extract_matrix`, `tableclaw_rank`, `tableclaw_filter`, `tableclaw_time_series`) to validate exact sheets, rows, columns, and numeric values.
9. Produce a concise answer with values, units, scope, and the table/source path used.

## Important Rules

- If the user explicitly gives a cohort list, use the user's list.
- If the uploaded table has complete cohort fields and the query asks for threshold filtering, prefer dynamic filtering from the table.
- If a cohort field is sparse or many rows have only ranks/no values, use domain knowledge as a fallback planning source and say so briefly.
- For current TableClaw gold/reporting questions, the default `200亿省` / `200亿收入省` / `主要大省` business-report cohort is: 广东、江苏、浙江、上海、四川、安徽、湖南. Do not add 湖北 unless the user explicitly requests it or a complete income-threshold column dynamically verifies it.
- Older templates sometimes included 湖北 as a historical/dynamic-threshold candidate. Treat it as contextual, not part of the current default chart/reporting cohort.
- For 四川市州 ranking, limit the ranking universe to the 21 四川市州 and filter out summary rows such as 合计、市州合计、汇总、全省.
- Ranking direction is business-dependent. Risk/arrears/receivable ratios usually rank low-to-high; cash collection/prepayment/income type indicators usually rank high-to-low unless the table or user states otherwise.
- If the user explicitly says `TOP`, `Top`, `前N`, `最高`, `最大`, or asks for the top list of a metric, default to high-to-low ordering even for ratio metrics such as 应收占收比. Only use low-to-high when the user says `最低`, `最小`, `风险低`, `低到高`, or asks for best/low-risk ranking.
- For 全省排名/市州排名, prefer the official ranking column in the same metric group when it exists. Do not recompute from a neighboring amount,同比, or ratio unless no official rank column is available.
- For 预收账款排名, the business default is usually 预收占收比排名. Use the official `预收占收比-排名` column when available; do not rank by 预收账款绝对值 unless the user explicitly says amount ranking.
- If a matching `validation_override` gives official/reporting ranks for a city prepayment task, use that override to reconcile the final rank after raw extraction. Do not let a freshly recomputed `tableclaw_rank` result override a matching high-priority reporting override.
- For 一年以上应收账款排名, bind the rank to the requested modifier in the same header group. If the question asks 一年以上应收账款 + 同比增幅 + 全省排名, use the official rank column immediately after `一年以上同比增幅`. If the question explicitly asks 一年以上占应收总额比 / 长账龄占比排名, use the ratio rank column. Do not cross from the 同比 rank column to the 占比 rank column or vice versa.
- `产数业务总收入` is an income metric. Do not substitute `产数应收总额` / `产数应收账款` for it.
- When a recommended plan gives a `rank_metric`, pass that metric into `tableclaw_rank` or extraction tools instead of the raw phrase from the user. Example: for `预收账款全省排名`, use `预收占收比` / `预收占收比排名`; for `产数业务总收入TopK`, sort by `产数收入` and include `产数应收占收比` only as a companion metric.
- `基础应收账款` / `基础应收总额` / `基础应收占收比` must stay inside the `基础业务应收总额情况` header group. Do not use the broader `应收总额情况` group as a substitute.
- `累计基础收入同比增幅` means `基础业务应收总额情况-基础业务收入同比增幅`; do not use `应收总额情况-收入同比增幅` or a 营业现金比率 table.
- For sorted chart/table requests with two metrics, follow the TablePipeline rule: first sort by the requested sorting metric, then return companion metrics for that ordered entity set. Do not sort by the companion amount unless the user explicitly asks.
- 2025年12月 province files may be sparse. Do not silently fall back to 2025年11月. If only part of a requested cohort has values, report missing entities and continue checking same-table sections or domain knowledge.
- For 2025年12月 200亿省 chart/table tasks about 应收占收比、产数应收占收比、基础业务应收占收比, and 同比增量/同比PP, uploaded province files may only expose 四川 or rank-like fragments. If `tableclaw_domain_knowledge` returns a matching sparse-table fallback, use it to complete the 7-province reporting table after checking the upload.
- For 2025年4月/5月/7月/8月 200亿省 prepayment chart/table tasks that ask for `预收账款/预收款项 + 预收占收比`, use the corresponding domain fallback when non-Sichuan rows are sparse or blank. Do not answer that only 四川 is available before reconciling the fallback.
- For current gold/reporting tasks, a yearless `全省1-12月小微ICT欠费趋势/图表` query should be interpreted as the 2025 monthly series unless the session or user explicitly states another year.
- For current gold/reporting tasks, a yearless `2月/二月 21市州 预收账款 + 预收占收比` chart query should use the latest uploaded February city workbook, currently `202602`, unless the session or user explicitly states another year.
- In current reporting chart tasks, phrases like `应收账款绝对值与收入同比增幅放在同一张图` may refer to the standard two-growth-rate chart: `应收总额同比增幅 + 收入同比增幅`. Check domain knowledge/table headers before choosing the absolute amount column.
- If a validation override applies, do not ignore it after doing a raw spreadsheet calculation. Use it to reconcile the final answer and briefly state that a domain/reporting fallback was used because the table ranking/value field was sparse or blank.
- If `mandatory_overrides` applies, it is stronger than a plain warning: after checking the uploaded table, use the override facts for final reconciliation when the sheet is sparse, blank, or inconsistent with the documented reporting口径. Do not answer "无法确定" from sparse cells alone.
- Do not use this skill as an answer bank. It can provide口径 and strategy, but final numbers require table evidence.
- Do not ask generic tools to infer business semantics from scratch when domain knowledge has already returned structured context; pass the relevant entities, metrics, and table-family hints into the tools.
