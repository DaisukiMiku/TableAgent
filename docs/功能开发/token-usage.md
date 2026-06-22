# TableClaw Token Usage 统计

> 最后更新：2026-06-22

## 当前状态

TableClaw 已把 token usage 接入 nanobot 的运行主链路。

每一轮成功调用模型后，AgentLoop 会把该轮统计追加写入：

```text
workspace/usage/usage.jsonl
```

这不是 eval 专用能力；正常 `./start.sh` 交互、`./start.sh --message ...` 以及后续如果网页入口复用同一套 AgentLoop，都会写入同一份 usage 日志。

## 单条记录字段

每条 JSONL 记录包含：

- `timestamp`：UTC 时间。
- `session_key` / `turn_id`：会话与轮次标识。
- `channel` / `chat_id` / `sender_id` / `message_id`：消息来源信息。
- `model` / `provider`：本轮实际使用的模型与 provider 类。
- `usage`：模型返回的 token 统计，常见字段包括 `prompt_tokens`、`completion_tokens`、`total_tokens`、`cached_tokens`。
- `tools_used`：本轮调用过的工具，例如 `read_file`、`exec`。
- `stop_reason`：agent 停止原因。
- `latency_ms`：本轮端到端耗时。
- `had_injections`：是否有运行时注入消息。

## 查看统计

快速汇总：

```bash
nanobot/.venv/bin/python eval_test/summarize_usage.py
```

查看最近 20 条：

```bash
nanobot/.venv/bin/python eval_test/summarize_usage.py --last 20
```

这个脚本会输出：

- 总轮数。
- prompt / completion / total / cached token 汇总。
- 按 session 聚合的 token 消耗。
- 最近若干轮的逐轮明细。

## 与 eval token 统计的关系

`eval_test/run_eval.py` 用于早期 skill-on/skill-off 对照实验。当前主线 benchmark 使用 `eval_test/run_gold_parallel_eval.py` 和 `eval_gold_parallel.sh`，会在每条 case 结果里保存 token、耗时、工具轨迹和 judge 结果。

早期 skill matrix 结果位置：

```text
eval_test/results/skill_matrix/latest_eval.json
```

两者分工不同：

- `workspace/usage/usage.jsonl`：运行时长期记录，回答”日常使用花了多少 token”。
- `eval_test/results/skill_matrix/latest_eval.json`：早期实验结果快照，回答”某个测试任务在不同配置下差多少”。
- `eval_test/results/<dataset>/parallel/`：当前主线并行评测结果，回答”某批 gold/badcase/query case 的准确率、耗时、token 和路径稳定性如何”。

## 注意事项

- 日志只记录统计和运行元信息，不保存完整用户问题或模型回答正文。
- 多个 `./start.sh` 同时运行时会写同一份 JSONL；写入使用文件锁保护。
- 如果某轮没有真正调用模型，例如纯 slash command，可能不会产生 usage 记录。
