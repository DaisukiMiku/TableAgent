# Table Catalog Layer RFC

> 最后更新：2026-06-10

## 目标

Table Catalog Layer 是 TableClaw 的上传后表格理解层。它在用户提问前或首次使用时，把 `workspace/uploads/` 中的表格转成可复用 catalog，让 Agent 先知道“有哪些表、每张表大概记录什么、适合回答什么问题”，而不是每轮都从文件名和原始 schema 重新猜。

核心边界：

> Catalog 是导航和规划上下文，不是最终答案证据。最终数值仍必须回到源表或虚拟 clean view 读取并验证。

## 运行态位置

```text
workspace/
├── uploads/                     # 用户上传的源表，不修改
├── table_cache/                 # inspect/schema cache
├── table_index/
│   └── tables.jsonl             # 轻量召回索引
└── table_catalog/
    ├── catalog.jsonl            # 每张表一条 catalog 入口
    ├── profiles/
    │   └── <table_id>.profile.json
    ├── clean_views/
    │   └── <table_id>.clean_view.json
    └── descriptions/
        └── <table_id>.description.json
```

`workspace/` 是运行态目录，不进入 git。Catalog 可以随上传表刷新，也可以删除后重建。

## 三层产物

### 1. Profile：确定性事实层

`profile.json` 由 `openpyxl` 和现有 schema cache 生成，不调用 LLM。它记录：

- 文件名、路径、大小、mtime、table id。
- sheet 列表、行列数、merged ranges。
- header candidates、sample rows。
- entity column candidates。
- important columns：列号、列字母、逻辑列名、样例值、推断类型、单位候选、value type。
- clean view 摘要。

Profile 是后续 LLM description 的输入，也是计算阶段的低成本结构上下文。

### 2. Clean View：虚拟清洗层

`clean_view.json` 不修改源 Excel，只保存建议的逻辑视图：

- title rows。
- header rows。
- data start/end row。
- entity columns。
- normalized columns。
- merged header policy：当前为 `logical_fill_in_memory_only`。

后续工具可以基于 clean view 读取和计算，但源表始终是 source of truth。

### 3. Description：LLM 语义层

`description.json` 由 DashScope OpenAI-compatible API 的 `deepseek-v4-pro` 生成；如果未配置 `DASHSCOPE_API_KEY` 或 API 失败，会降级为 deterministic fallback。

结构字段：

- `short_description`
- `what_it_records`
- `row_grain`
- `time_coverage`
- `main_entities`
- `metric_groups`
- `important_metrics`
- `can_answer`
- `not_suitable_for`
- `data_quality_notes`
- `ambiguities`

这层用于召回、planner 和长对话记忆。例如用户问“12 月哪些大省收入下滑了”，模型可以先看 catalog description 判断哪张表是省份级、含收入同比、适合做筛选。

## 工具接口

### `tableclaw_catalog_tables`

用途：为 `workspace/uploads/` 中的表构建/刷新 catalog。

参数：

- `rebuild_catalog`：强制重建 profile/clean view/description。
- `describe_with_llm`：是否调用 LLM 生成语义描述；默认 true，失败自动 fallback。
- `model`：默认 `deepseek-v4-pro`。
- `limit`：可选，仅 catalog 前 N 张表，便于 smoke。

输出：

- catalog 文件路径。
- cataloged table 数量。
- 每张表的 short description、row grain、important metrics、can answer、profile/description/clean view 路径。

### `tableclaw_retrieve_tables`

已有召回工具现在会在读取 `workspace/table_index/tables.jsonl` 后，自动合并 `workspace/table_catalog/catalog.jsonl` 中的描述字段。

召回信号包括：

- 文件名、月份、scope、subject。
- sheet/header/sample schema。
- catalog description：short description、what it records、row grain、important metrics、can answer、data quality notes 等。

返回候选表时也会带上：

- `description_status`
- `short_description`
- `row_grain`
- `important_metrics`
- `can_answer`
- `description_path`
- `profile_path`
- `clean_view_path`

## 设计原则

- 不把 LLM description 当作事实证据；它只负责帮助选表和规划。
- 不修改用户源表；clean view 是派生 JSON。
- LLM 输入只使用 compact profile，不直接塞完整 workbook。
- Description 输出必须是结构化 JSON；解析失败或 API 不可用时 fallback。
- Catalog 是通用层，不写入特定业务规则；业务术语定义后续应放入 workspace/domain pack 或 term resolver。

## 后续升级

- 给 description 字段增加 confidence 和 evidence anchors。
- 自动发现 table groups，例如月度同模板文件组。
- `tableclaw_retrieve_tables` 增加 catalog-only / schema-only / hybrid 对照指标。
- eval 记录 catalog hit、description status、catalog-assisted reasons。
- 增加 `tableclaw_resolve_term` 和 `tableclaw_resolve_scope`，把“200亿省/大客户/重点门店”等术语从 core 中解耦。
