---
name: "Table Validate"
description: "Use this skill when the task needs to verify spreadsheet answers, check row/column counts, validate formulas or numeric outputs, compare computed results with source cells, produce evidence, or make an answer auditable."
---

# Table Validate

Use this skill before finalizing answers that involve spreadsheet calculation, filtering, ranking, aggregation, formula results, or generated reports.

## Validation Checklist

1. Re-state the analysis scope:
   - sheet
   - target periods/metrics
   - included/excluded rows
2. Verify the located columns by header labels, not just column letters.
3. Verify row counts after cleaning.
4. Recompute critical numbers from source cells.
5. For ranked outputs, check sort direction and tie handling.
6. For thresholds, check boundary operators (`<`, `<=`, `>`, `>=`).
7. For formulas, inspect formula text and computed values separately when possible.
8. Include concise evidence in the final answer: source sheet, row count, excluded rows, and calculation formula.

## Output Contract

Final answers should include a short validation note when useful:

- `已排除: ...`
- `有效记录数: ...`
- `指标列: ...`
- `校验: ...`
