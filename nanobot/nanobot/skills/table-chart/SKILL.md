---
name: "Table Chart"
description: "Use this skill when the task asks to create, choose, explain, or validate charts, dashboards, trend views, KPI visuals, or chart-ready summary tables from spreadsheet data."
---

# Table Chart

Use this skill when visual output or chart-ready data is required.

## Chart Selection

- Ranking comparison: horizontal bar chart.
- Time trend: line chart.
- Composition: stacked bar or 100% stacked bar.
- Distribution/outliers: box plot or sorted bar table.
- KPI dashboard: small summary cards plus chart-ready table.

## Workflow

1. Clean and validate the source data first.
2. Build a compact chart-ready table rather than charting raw wide sheets directly.
3. Use readable labels and units.
4. Avoid misleading axes, truncated scales, or mixed units in one axis.
5. If producing an `.xlsx`, keep source, calculation, and chart sheets separate.

## Output Contract

When no actual chart file is requested, describe:

- recommended chart type
- x-axis / y-axis
- series
- filters/exclusions
- why this chart fits the question
