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

## 判断规则

- 如果 LangGraph 在 hard cases 上更稳，说明显式 state / verifier loop 值得吸收。
- 如果 OpenAI Agents SDK 接近 LangGraph，说明轻量 runtime 不是主要瓶颈。
- 如果 AutoGen 明显更稳但成本高，优先把 verifier step 移植回 TableClaw，而不是直接换多 agent runtime。
- 如果所有框架失败在同一类 case，先归因到 tool/domain/eval/data。
