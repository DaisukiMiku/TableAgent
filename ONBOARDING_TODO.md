# TableClaw 新成员 Onboarding TODO

欢迎加入 TableClaw。明早先不急着改代码，主要目标是熟悉项目当前主线：TableClaw 如何基于 Nanobot 做表格任务，如何结合已上传表格、skill、domain knowledge、通用工具和评测闭环完成一次业务问题分析。

## 你明早需要完成什么

请围绕当前仓库完成一次小规模复现，并输出一份简短观察文档。重点不是刷分，也不是马上修 bug，而是先建立对整个 workflow 的直觉。

仓库地址：

```bash
git@github.com:Cutesxy/TableAgent.git
```

## 1. 熟悉项目

先拉代码，阅读根目录 `README.md`，再根据 README 里的入口顺着读几份核心文档即可。重点理解：

- TableClaw 当前想解决什么问题
- Nanobot 在这个项目里承担什么角色
- workspace、uploads、skills、domain knowledge、eval 分别大概做什么
- 当前评测是怎么跑的、结果怎么看

不要求第一遍读完所有文档，先抓住主线。

## 2. 跑通最小流程

先确认交互入口能启动：

```bash
./start.sh
```

能进入对话界面即可。如果环境有问题，记录报错，不要大改项目。

然后跑一个小规模评测，建议先跑 10 条 badcase：

```bash
./eval_gold_parallel.sh \
  --task-file eval_test/test_dataset/bad_cases.jsonl \
  --limit 10 \
  --concurrency 3 \
  --run-id onboarding-yourname-10cases
```

你可以简单记录这 10 条的整体情况，例如正确率、大致耗时、有没有 runtime error、哪些任务看起来比较容易失败。

## 3. 深挖一个 case

从这 10 条里任选 1 条你觉得有代表性的 case，尽量还原它的执行过程。可以关注：

- 用户问题是什么
- 系统大概找了哪些表，为什么可能选这些表
- 是否用到了 skill 或 domain knowledge，如果用了，读到了什么关键信息
- 调用了哪些表格工具，以及每个工具大概解决了什么问题
- 最终答案和 gold answer 差在哪里
- judge 为什么这么判
- 你觉得这条 case 暴露了什么问题

不要求写成非常机械的日志，重点是把你理解到的执行链路讲清楚。

如果不知道从哪里看，可以按下面这个顺序梳理：

```text
用户问题
-> 表格召回 / 候选表选择
-> skill 或 domain knowledge 是否介入
-> schema inspect / 表头理解
-> 具体数据抽取、排序、过滤、时间序列等工具调用
-> 模型如何组织最终答案
-> judge 如何对比 gold answer
-> 这条 case 成功或失败的原因
```

建议重点记录这些信息：

- `tableclaw_retrieve_tables`：召回了哪些候选表，最高分表是否合理。
- `tableclaw_domain_knowledge`：是否返回了 cohort、指标别名、推荐计划或 fallback。
- `tableclaw_inspect`：系统如何理解表头、sheet、行列结构。
- `tableclaw_extract_matrix` / `tableclaw_topk` / `tableclaw_rank` / `tableclaw_time_series`：实际用了哪些结构化抽取工具，输入参数是否合理，输出是否接近最终答案。
- `exec` 或自写 Python：如果模型绕开工具自己写代码，需要记录它为什么这么做，以及这样是否稳定。
- 最终答案：是否包含正确的时间、范围、单位、指标口径、数值和排序。
- 评测结果：judge 判分是否合理；如果你觉得 gold 或 judge 有问题，也可以写出来。

这部分不要求你完全读懂所有代码，但希望你能用自己的话解释：这条 case 是怎么被 agent 一步步完成的。

## 4. 画一张图

请用自己的理解画一张图，可以是架构图，也可以是流程图。重点表达两个问题：

1. TableClaw 现在整体是怎么工作的。
2. 一个具体业务 case 从用户提问到最终评测，大概是怎么走完的。

图不需要复杂，也不限定工具或形式，清楚比好看重要。

## 5. 输出一份观察文档

最后整理一份 Markdown 文档，建议放在：

```text
docs/项目管理/onboarding-yourname-YYYYMMDD.md
```

文档内容自由组织，但至少覆盖：

- 你对当前项目主线和架构的理解
- 10 条小评测的大致结果
- 1 条 case 的执行轨迹分析
- 你画的架构图 / 流程图
- 你发现的几个问题
- 你认为后续可以优先做的方向

写完先发给我 review，暂时不用 push。

## 注意事项

- 不要提交 API key。
- 不要直接改核心代码。
- 不要一上来跑全量 122 条评测。
- 如果环境或数据有问题，先记录现象。
- 第一阶段的目标是理解系统，而不是马上优化分数。
