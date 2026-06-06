# Workflow Routing Eval

> 最后更新：2026-06-06

## 目的

这份评测补充在原 10-task skill matrix 之上，观察 TableClaw 是否能在一个表格任务的不同阶段选择不同 skill。

当前不是为了证明某个 skill 一定优于 no-skill，而是为了让 workflow 可观测：

- 哪些 skill 被读取。
- 第几个 tool step 读取。
- 是否出现多 skill sequence。
- skill-on/off 在 token、耗时、工具步数、答案质量上的差异。

## 新增 Skill 池

| Skill | 阶段 |
| --- | --- |
| `table-read` | 读表结构、sheet、表头、指标列 |
| `table-clean` | 清洗口径、空行、合计行、缺失值 |
| `table-validate` | 校验行数、列数、数值、口径 |
| `table-report` | 输出管理摘要、建议和证据 |
| `table-formula-debug` | 公式排错 |
| `table-chart` | 图表/看板 |
| `xlsx` | Codex 原文大 spreadsheet skill，当前兜底 |

## 新增任务

| Task | Case | 目标 |
| --- | --- | --- |
| `tc_workflow_001` | `workflow` | 读表结构 + 数据质量检查 + 是否适合跨期分析 |
| `tc_workflow_002` | `workflow` | 清洗口径 + 两期低于阈值筛选 + 风险报告 + 校验说明 |

两个任务仍基于：

`eval_test/test_dataset/tables/市州数据-营业收现率台账.xlsx`

## 运行方式

```bash
./eval.sh --case workflow
./eval.sh --modes skill-on skill-off --task-id tc_workflow_001
./eval.sh --modes skill-on skill-off --task-id tc_workflow_002
```

## 预期观察

理想情况下：

- `tc_workflow_001`：优先读取 `table-read`，随后读取 `table-clean` 或 `table-validate`。
- `tc_workflow_002`：优先读取 `table-read` / `table-clean`，计算后读取 `table-validate` / `table-report`。
- skill-off 不应读取上述 skill。

如果模型仍然只读取 `xlsx` 或完全不读 skill，也不是失败，而是说明后续需要：

- 优化 skill description。
- 给 Nanobot 加显式 table workflow router。
- 把高频 inspect/clean/validate 下沉成 tools，而不只靠文档 skill。

## 2026-06-06 试跑结果

命令：

```bash
./eval.sh --case workflow
```

结果文件：

- `eval_test/results/skill_matrix/latest_eval.json`
- `docs/实验评测/skill-matrix/latest-eval-summary.md`

观察摘要：

| Task | Mode | Skill sequence | Auto score | Total tokens | Tool steps | 观察 |
| --- | --- | --- | --- | ---: | ---: | --- |
| `tc_workflow_001` | skill-on | `table-read` | pass | 89,778 | 6 | 首步命中结构读取 skill，输出包含表结构、有效行、缺失检查和可分析判断。 |
| `tc_workflow_001` | skill-off | `-` | stale strict fail | 63,929 | 4 | 语义正确，但旧评分把“无缺失”当作没命中数字 0；已调整任务评分口径。 |
| `tc_workflow_002` | skill-on | `table-read -> table-clean` | pass | 87,425 | 7 | 首轮命中读表与清洗 skill，报告结构更明确。 |
| `tc_workflow_002` | skill-off | `-` | pass | 75,783 | 5 | 也能答对，但路径是直接读表、读 tool-result、再补脚本探索。 |

关键 insight：

- 轻量 skill 已经能被模型自然选择，不需要改 Nanobot 核心。
- `tc_workflow_002` 首轮可稳定触发多个 skill，证明“一个任务按阶段选择不同 skill”的方向成立。
- skill-on 当前不一定省 token；它更像是提升流程结构和可追踪性。真正降 token 需要后续做 schema cache 和 table tools。
- skill-off 也能解决当前小表任务，说明数据集还需要扩到更复杂、多 sheet、公式、图表、编辑类任务，才能拉开能力边界。
- `table-report` 命中不稳定：第一次试跑读了 `table-report`，第二次没有读。后续可以微调 description，或者引入显式 workflow router。

## 评分边界

当前 `run_eval.py` 仍使用事实匹配 + 数值检查：

- `required_facts`
- `numeric_checks`

这足够验证结构化问答和报告摘要，但还不能评价真正的文件修改、公式修复、图表产物质量。后续需要扩展 harness。
