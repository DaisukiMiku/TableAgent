---
name: tc-bigtable-aggregate
description: "Use this skill when a wide multi-period spreadsheet has hierarchical area rows (e.g. 区县 layout: 第1层级 / 第2层级 / 第3层级 columns at the left) and the user asks for a result aggregated at a non-leaf level — for example 'sum by 市', 'rank cities by total 欠费', '按地市汇总 Top N'. The trap: the data rows are 区县-level (one row per leaf), so summing the column directly mixes provinces, cities, and counties; you must group by the correct level column first. Trigger on '按市汇总', '地市排名', '汇总到第二层级', '父级聚合', or whenever you've located numeric columns via tc-bigtable-header and now need a per-group total / delta / rank."
---

# tc-bigtable-aggregate — Hierarchical Area Aggregation

You have already located the value columns via **tc-bigtable-header**. Each data row is a leaf (typically a 区县). The user wants a result at a higher level (typically a 市). Use this exact pattern; do not loop and accumulate by hand without a `defaultdict`.

## Standard 区县 layout

In the 欠费 / 应收 family of tables, the leftmost columns at row 5 are:

```
col 1: 区域(第1层级-编码)   col 2: 区域(第1层级)   = 省
col 3: 区域(第2层级-编码)   col 4: 区域(第2层级)   = 市
col 5: 区域(第3层级-编码)   col 6: 区域            = 区县（叶子）
```

Data rows start at row 6. The last data row is `ws.max_row` (you may see trailing rows with values but no 区县 name — skip them with a `not city or not qx` guard).

## Aggregation template

```python
from collections import defaultdict

city_total_a = defaultdict(float)
city_total_b = defaultdict(float)
for r in range(6, ws.max_row + 1):
    city = ws.cell(r, 4).value          # 第2层级 = 市
    leaf = ws.cell(r, 6).value          # 区县 — guard against blank trailing rows
    if not city or not leaf:
        continue
    va = ws.cell(r, COL_A).value
    vb = ws.cell(r, COL_B).value
    if isinstance(va, (int, float)):
        city_total_a[city] += va
    if isinstance(vb, (int, float)):
        city_total_b[city] += vb
```

For a cross-period delta + ranking question:

```python
deltas = [(c, city_total_b[c] - city_total_a[c], city_total_a[c], city_total_b[c])
          for c in city_total_a if c in city_total_b]
deltas.sort(key=lambda x: -x[1])
top3 = deltas[:3]
```

## Output discipline

- Always print the per-city total and the delta with **at least 6 decimals** (`f"{x:.6f}"`); do not round to 4 decimals — the auto evaluator uses `1e-6` tolerance.
- When the user asks for "Top N 增长", report `(city, value_period_a, value_period_b, delta)` for every entry in the Top N, not just the city name.
- Do not include the province row, blank trailing rows, or the same city appearing twice — your `defaultdict` already de-dupes by city name; just verify the count matches the number of distinct cities (`print('distinct cities:', len(city_total_a))`).
