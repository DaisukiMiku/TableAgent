# Server Runbook: qwen3.5 Framework Comparison

本包用于在不能联网的堡垒机/服务器环境里运行 TableAgent framework comparison 实验。

## 模型口径

```bash
export QWEN35_MODEL=qwen3.5
export QWEN35_API_URL=http://10.127.23.252:48057/v1
export QWEN35_API_KEY=EMPTY
```

如果服务端需要鉴权，把 `QWEN35_API_KEY` 改成实际 key；如果不需要鉴权，保留 `EMPTY` 即可。

## 解包后检查

```bash
cd TableAgent-framework-comparison-qwen35
chmod +x eval_gold_parallel.sh scripts/server/run_gold_qwen35.sh scripts/sync_domain_pack.sh
```

服务器需要已有 Python 环境和依赖。当前打包不包含可用 `.venv`，因为本机 `.venv` 不是完整依赖环境。

核心依赖来源：

- `nanobot/pyproject.toml`
- `eval_test/frameworks/requirements-frameworks.txt`
- `tablepipeline-2/requirements.txt`

## 跑 Nanobot baseline

```bash
scripts/server/run_gold_qwen35.sh \
  --framework nanobot-current \
  --task-file eval_test/test_dataset/bad_cases.jsonl \
  --limit 10 \
  --concurrency 2 \
  --run-id qwen35-smoke-nanobot-current
```

```bash
scripts/server/run_gold_qwen35.sh \
  --framework nanobot-skill-off \
  --task-file eval_test/test_dataset/bad_cases.jsonl \
  --limit 10 \
  --concurrency 2 \
  --run-id qwen35-smoke-nanobot-skill-off
```

## 跑第三方 framework

这些需要服务器 Python 环境里已安装对应依赖。

```bash
scripts/server/run_gold_qwen35.sh \
  --framework langgraph \
  --task-file eval_test/test_dataset/bad_cases.jsonl \
  --limit 10 \
  --concurrency 1 \
  --run-id qwen35-smoke-langgraph
```

`openai-agents-sdk` 和 `autogen` 同理替换 `--framework`。

## 跑 tablepipeline-v2

`tablepipeline-v2` 需要预处理后的 CSV/JSON 表目录。请把目录路径传给 `--tablepipeline2-data-dir`。

```bash
scripts/server/run_gold_qwen35.sh \
  --framework tablepipeline-v2 \
  --task-file eval_test/test_dataset/bad_cases.jsonl \
  --limit 10 \
  --concurrency 1 \
  --run-id qwen35-smoke-tablepipeline-v2 \
  --tablepipeline2-data-dir /path/to/tablepipeline2/preprocessed_tables \
  --tablepipeline2-qq-knowledge-path tablepipeline-2/指标知识库0123.xlsx
```

## 输出位置

默认输出在：

```text
eval_test/results/gold_cases/parallel/
```

重点看：

- `latest_report.md`
- `latest_summary.json`
- `latest_results.jsonl`
- `traces/<run-id>/<framework>/`
