---
name: "Table Formula Debug"
description: "Use this skill when the task involves spreadsheet formulas, formula generation, formula repair, recalculation, reference errors, inconsistent formulas, or checking computed cells against formula logic."
---

# Table Formula Debug

Use this skill for formula tasks, not for ordinary value-only lookups.

## Workflow

1. Load workbook with `data_only=False` to inspect formulas.
2. Load a second copy with `data_only=True` to inspect cached computed values.
3. Identify formula cells, referenced ranges, and neighboring formula patterns.
4. Look for common issues:
   - `#REF!`, `#DIV/0!`, `#VALUE!`, `#N/A`
   - broken ranges after row/column insertion
   - inconsistent formulas across a column or row
   - formulas pointing to totals when detail rows are required
5. If editing formulas, preserve formatting and verify after save.

## Output Contract

Report:

- affected sheet/cells
- original formula
- issue category
- proposed fixed formula
- validation method
