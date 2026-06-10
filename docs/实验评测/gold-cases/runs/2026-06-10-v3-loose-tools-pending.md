# Gold Cases Parallel Eval Summary

## Run Profile

| Item | Value |
| --- | --- |
| Version | `v3-loose-tools` |
| Status | Running / pending metrics |
| Purpose | 验证“工具可用但 prompt 不显式点名、不强制调用”的宽松工具策略 |
| Prompt strategy | 只告诉模型：用户表格已上传到 `workspace/uploads`、不能假设 gold answer / gold table path、不要把所有上传表完整塞入上下文、视觉题当前只评底层数据、最后说明使用表文件名；不显式列出任何 `tableclaw_*` 工具名 |
| Tool exposure | Nanobot registry 仍提供 `tableclaw_retrieve_tables`、`tableclaw_inspect`、`tableclaw_locate_column`、`tableclaw_topk`、`tableclaw_filter`、`tableclaw_extract_series`；模型可自主选择是否使用 |
| Skill behavior | 待评测；目标是恢复模型对 xlsx/table skill 和自写代码的自主选择能力 |
| Main insight | 待评测；重点观察 ACC 是否回升到 v1-baseline 附近，同时保留 v2 的部分速度/结构化工具收益 |

## Prompt Template

```text
用户问题：
{question}

这是 TableClaw workflow 评测。用户已将相关工业表上传到 workspace/uploads，但没有显式指定文件路径。
{gold_note}

执行要求：
1. 请自主选择最可靠的方式完成任务，可以使用可用工具、skill 或简短代码，但不要假设标准答案或 gold table path。
2. 不要把所有上传表完整塞入上下文；优先围绕问题中的时间、指标、地域/单位和表名线索选择相关表格。
3. 如果候选表不足或字段缺失，请明确说明，并基于最相关表格给出 best-effort 结果。
4. {visual_note}
5. 最后列出使用的表文件名，并说明是否成功完成。
```

## Run Command

```bash
./eval_gold_parallel.sh --concurrency 8
```

正式结果跑完后，将 `latest-parallel-eval-summary.md` 另存为 `2026-06-10-v3-loose-tools-accXX.md`，并更新本 run index。
