# Table Schema Cache RFC

> 最后更新：2026-06-10

## 目标

`workspace/table_cache/` 是 TableClaw 的表格上下文缓存层。它把用户上传到 `workspace/uploads/` 的 xlsx/csv/tsv 解析成可复用 schema，减少模型反复写 openpyxl 脚本摸表头、sheet、列和样例值。

当前版本是 v0.1，重点是先支撑：

- `tableclaw_retrieve_tables` 基于 schema/header/sample 做更通用的召回。
- `tableclaw_inspect` 让模型在写计算脚本前先拿到结构化表格上下文。
- `tableclaw_catalog_tables` 复用 schema cache 生成 profile、virtual clean view 与 table description。
- 后续 `tableclaw_locate_column`、`tableclaw_extract_series`、`tableclaw_topk` 直接复用 cache。

## 缓存位置

```text
workspace/
├── uploads/                 # 用户上传表
├── table_index/
│   └── tables.jsonl         # 召回索引，引用 schema cache
└── table_cache/
    └── <table_id>_<sha>.schema.json
└── table_catalog/
    ├── catalog.jsonl
    ├── profiles/
    ├── clean_views/
    └── descriptions/
```

`workspace/` 是运行态目录，不进入 git。后续 Web 上传只需要把文件保存到 `workspace/uploads/`，再触发 inspect/retrieve 即可生成缓存。

## Schema 字段

每个 cache JSON 记录一张表：

```json
{
  "cache_version": 1,
  "table_id": "tbl_xxx",
  "filename": "example.xlsx",
  "path": "/abs/path/workspace/uploads/example.xlsx",
  "suffix": ".xlsx",
  "size_bytes": 12345,
  "mtime": 1780000000,
  "scope": "unknown",
  "subject": "unknown",
  "month": null,
  "sheets": [
    {
      "sheet": "Sheet1",
      "max_row": 100,
      "max_column": 20,
      "merged_ranges": ["A1:B1"],
      "header_candidates": [
        {"row": 1, "values": ["月份", "单位", "销售额"], "score": 3}
      ],
      "columns": [
        {
          "index": 1,
          "letter": "A",
          "header_values": ["月份"],
          "sample_values": ["202601", "202602"],
          "inferred_type": "text"
        }
      ],
      "sample_rows": [["202601", "成都", "123.4"]]
    }
  ]
}
```

## 失效策略

缓存通过以下字段判断是否新鲜：

- `cache_version`
- `size_bytes`
- `mtime`

如果任一字段不匹配，`tableclaw_inspect` 会重新解析并覆盖 cache。

## 工具接口

### `tableclaw_inspect`

用途：读取一张上传表，返回 schema 摘要，并写入/复用 `workspace/table_cache/`。

参数：

- `path`：绝对路径、workspace 相对路径，或 `workspace/uploads/` 下的文件名。
- `sheet`：可选 sheet 名；传入时只 inspect 该 sheet，不覆盖整表 cache。
- `rebuild_cache`：强制重建。

### `tableclaw_retrieve_tables`

用途：根据用户问题从 `workspace/uploads/` 召回候选表。

当前召回信号：

- 文件名、月份、业务 scope/subject。
- schema cache 中的 sheet 名、候选表头、列头、样例值。
- 如果 `workspace/table_catalog/catalog.jsonl` 已存在，也会使用 LLM/fallback 生成的 table description、can-answer、important metrics 等 catalog 信号。
- 少量当前工业表格业务词仍保留为加分项，但不再是唯一依据。

## 后续升级

- 增加 `tableclaw_locate_column(path, query/metric/period)`：在 cache 上定位候选 sheet/列。
- 增加 `tableclaw_extract_series`：直接抽取月份序列/指标序列。
- 增加 `tableclaw_topk`：对候选列做 Top-K/Bottom-K。
- 召回评测增加 Recall@k：gold table path 只给 evaluator，不进 prompt。
