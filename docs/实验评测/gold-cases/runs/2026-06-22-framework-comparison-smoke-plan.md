# 2026-06-22 Framework Comparison Smoke Plan

> 本文件记录首轮 framework comparison 的运行口径。正式结果文件在跑完 smoke 后另行归档。

## 固定口径

- Answer model: `deepseek-v4-pro`
- Judge model: `deepseek-v4-pro`
- Provider: DashScope OpenAI-compatible API
- Dataset smoke: `eval_test/test_dataset/bad_cases.jsonl --limit 10`
- Workspace: `workspace/`
- Domain pack: `domain_packs/sichuan-finance`
- Prompt: `eval_test/run_eval.py::render_prompt`
- Judge: `data-correctness-v5-2026-06-16`
- 说明：本轮先按用户确认使用 `deepseek-v4-pro`，不是 V4-flash；后续报告必须沿用这个口径，不能混写。

## Baseline smoke

```bash
./eval_gold_parallel.sh \
  --framework nanobot-current \
  --task-file eval_test/test_dataset/bad_cases.jsonl \
  --limit 10 \
  --concurrency 2 \
  --run-id framework-smoke-nanobot-current
```

```bash
./eval_gold_parallel.sh \
  --framework nanobot-skill-off \
  --task-file eval_test/test_dataset/bad_cases.jsonl \
  --limit 10 \
  --concurrency 2 \
  --run-id framework-smoke-nanobot-skill-off
```

## Optional framework smoke

安装可选依赖后再运行：

```bash
nanobot/.venv/bin/python -m pip install -r eval_test/frameworks/requirements-frameworks.txt
```

```bash
./eval_gold_parallel.sh \
  --framework openai-agents-sdk \
  --task-file eval_test/test_dataset/bad_cases.jsonl \
  --limit 10 \
  --concurrency 1 \
  --run-id framework-smoke-openai-agents
```

```bash
./eval_gold_parallel.sh \
  --framework langgraph \
  --task-file eval_test/test_dataset/bad_cases.jsonl \
  --limit 10 \
  --concurrency 1 \
  --run-id framework-smoke-langgraph
```

```bash
./eval_gold_parallel.sh \
  --framework autogen \
  --task-file eval_test/test_dataset/bad_cases.jsonl \
  --limit 10 \
  --concurrency 1 \
  --run-id framework-smoke-autogen
```

## Self-developed pipeline smoke

`tablepipeline-v2` 使用 `/Users/glenxin/Desktop/TableAgent/tablepipeline-2/` 的新版自研 pipeline。它不是同一套 TableClaw tools 的 agent framework，而是历史/旁路自研 pipeline baseline；报告里应单列。

运行前需要准备：

- `tablepipeline-2` 自己的依赖环境；当前本机 Python import 已知缺 `pandas`，应按 `tablepipeline-2/requirements.txt` 或对应镜像安装。
- 已预处理好的 CSV/JSON 表目录，传给 `--tablepipeline2-data-dir`。
- QQ/指标知识库 xlsx，默认尝试使用 `tablepipeline-2/指标知识库0123.xlsx`，也可用 `--tablepipeline2-qq-knowledge-path` 指定。
- 并发建议固定 `--concurrency 1`，因为它会切换工作目录、加载同名顶层模块，并且内部有全局 env/module 状态。

```bash
./eval_gold_parallel.sh \
  --framework tablepipeline-v2 \
  --task-file eval_test/test_dataset/bad_cases.jsonl \
  --limit 10 \
  --concurrency 1 \
  --run-id framework-smoke-tablepipeline-v2 \
  --tablepipeline2-root /Users/glenxin/Desktop/TableAgent/tablepipeline-2 \
  --tablepipeline2-data-dir /path/to/tablepipeline2/preprocessed_tables \
  --tablepipeline2-qq-knowledge-path /Users/glenxin/Desktop/TableAgent/tablepipeline-2/指标知识库0123.xlsx
```

## 判断规则

- 如果 `tablepipeline-v2` 明显优于 Nanobot，先拆解优势来自召回、query rewriting、Python agent loop、经验库还是知识库，而不是直接归因为“框架更强”。
- 如果 LangGraph 在 hard cases 上更稳，说明显式 state / verifier loop 值得吸收。
- 如果 OpenAI Agents SDK 接近 LangGraph，说明轻量 runtime 不是主要瓶颈。
- 如果 AutoGen 明显更稳但成本高，优先把 verifier step 移植回 TableClaw，而不是直接换多 agent runtime。
- 如果所有框架失败在同一类 case，先归因到 tool/domain/eval/data。
