# TableClaw

TableClaw 是一个面向本地工业表格任务的 agent 原型，基于 Nanobot workflow，把上传表召回、表结构理解、确定性读算工具、skill 和评测闭环组合在一起。

## 核心开发思想

```text
通用探索能力兜底
+
稳定工具加速高频路径
+
skill/memory 承接半结构化经验
+
评测闭环决定什么该固化、什么该保持开放
```

含义：

- 基模负责未知问题中的探索、质疑、反证和临时代码执行。
- 工具负责把高频、确定、可测试的表格动作变得便宜和稳定。
- skill/memory 负责沉淀“怎么做一类任务”的过程知识，保留比工具更柔性的经验。
- 评测负责约束工具和 skill 的演进，避免只对单个 case 有效而伤害其他任务。

TableClaw 不追求把所有表格推理都写死成工具，也不把所有问题都交给模型临场探索。当前方向是在两者之间建立可验证的循环：

```text
临场探索 -> 发现可复用模式 -> 工具/skill 化 -> 评测验证
-> 失败样本回流 -> 更新工具/skill/memory -> 再评测
```

## 快速入口

| 文档 | 用途 |
| --- | --- |
| [文档总览](docs/README.md) | 项目文档入口，包含架构、功能开发、实验评测和项目管理索引。 |
| [Gold Cases Benchmark](docs/实验评测/gold-cases/README.md) | 40 条人工 gold case 的 benchmark 入口和历史 run。 |
| [Run History](docs/实验评测/gold-cases/runs/README.md) | 已归档的 40-case benchmark 与专项 case 对比报告。 |
| [开发日志](docs/项目管理/development-log.md) | 按时间记录关键决策、实现和评测结果。 |

## 常用命令

```bash
./start.sh
./eval_gold_parallel.sh --concurrency 4
```
