# TableClaw 开发日志

> 用途：记录 TableClaw 二次开发过程中的关键决策、配置、验证结果和待办，方便后续切换模型、切换上下文或继续开发时快速恢复现场。

---

## 2026-05-28

### 已阅读的项目上下文

- 阅读了 `docs/架构/project-structure.md`，确认 TableClaw 当前以裁剪后的上游 `nanobot/` 为骨干。
- 阅读了 `nanobot/README.md`、`nanobot/CLAUDE.md`、`nanobot/.agent/design.md`、`nanobot/.agent/security.md`、`nanobot/.agent/gotchas.md`。
- 阅读了内置 skill 加载器 `nanobot/nanobot/agent/skills.py` 和内置 skills 摘要。
- 阅读了三个外部 spreadsheet skill：
  - `skills/anthropic_xlsx_skill/SKILL.md`
  - `skills/kimi_xlsx_skill/SKILL.md`
  - `skills/kimi_xlsx_skill/pivot-table.md`
  - `skills/codex/SKILL.md`

### 关键架构判断

- 新能力优先加在 `nanobot/nanobot/agent/tools/`、`nanobot/nanobot/skills/`、`nanobot/nanobot/channels/` 或 `nanobot/nanobot/providers/`。
- 尽量不动 `nanobot/nanobot/agent/loop.py` 和 `nanobot/nanobot/agent/runner.py`，除非问题确实发生在核心调度链路。
- 配置集中在 `nanobot/nanobot/config/schema.py`；JSON 使用 camelCase，Pydantic 支持 snake_case 兼容。
- Provider 注册入口是 `nanobot/nanobot/providers/registry.py`。
- DashScope provider 已内置，默认 API Base 是 `https://dashscope.aliyuncs.com/compatible-mode/v1`，并支持 `enable_thinking` 风格的思考开关。

### 百炼模型配置

新增本地运行配置模板：

- 文件：`nanobot/configs/tableclaw-bailian-dashscope.json`
- Provider：`dashscope`
- API Base：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- 当前 model：`deepseek-v4-pro`
- Reasoning：`high`
- Workspace：`/Users/hxy/Desktop/TableClaw/workspace`
- API Key：通过 `${DASHSCOPE_API_KEY}` 环境变量注入，避免明文写入项目文件

备注：用户描述为 “Kimi K2.6”，但提供的百炼文档内容是 DeepSeek 系列，示例模型为 `deepseek-v4-pro`。先按文档示例跑通；后续如确认 Kimi K2.6 的百炼 model id，再替换配置中的 `agents.defaults.model`。

### 待验证

- 使用上述配置启动 nanobot。
- 发送一次 `你好`。
- 等待模型返回，确认端到端调用链路可用。

### 验证结果

已跑通。

本地环境：

- 创建虚拟环境：`nanobot/.venv`
- 安装方式：在 `nanobot/` 目录执行 `.venv/bin/python -m pip install -e .`
- 配置文件：`nanobot/configs/tableclaw-bailian-dashscope.json`

验证命令：

```bash
cd /Users/hxy/Desktop/TableClaw/nanobot
DASHSCOPE_API_KEY="<百炼 API Key>" .venv/bin/python -m nanobot agent \
  --config configs/tableclaw-bailian-dashscope.json \
  --message "你好" \
  --no-markdown \
  --no-logs
```

实际返回摘要：

- nanobot 成功创建 `~/.nanobot/tableclaw-workspace` 下的模板与记忆文件。
- Git store 初始化成功。
- 模型返回了中文问候：“你好！我是 nanobot，你的个人 AI 助手。有什么我可以帮你的吗？”

### 后续切换模型

优先只改 `nanobot/configs/tableclaw-bailian-dashscope.json`：

- `agents.defaults.model`
- `agents.defaults.provider`
- `providers.<provider>.apiBase`
- `providers.<provider>.apiKey` 对应的环境变量名
- 如模型不支持思考模式，将 `agents.defaults.reasoningEffort` 改为 `"none"` 或删除该字段

如果后续确认 “Kimi K2.6” 的百炼 model id：

1. 先替换 `agents.defaults.model`。
2. 保持 provider 为 `dashscope` 试跑一次。
3. 如果百炼返回参数不兼容，再检查 `nanobot/nanobot/providers/openai_compat_provider.py` 中 Kimi thinking 参数映射是否需要为 DashScope 做特殊处理。

### 一键启动脚本

新增项目根目录脚本：

- 文件：`start.sh`
- 用途：直接进入 nanobot 交互聊天界面
- 运行方式：

```bash
cd /Users/hxy/Desktop/TableClaw
./start.sh
```

脚本行为：

- 自动定位项目根目录。
- 自动激活 `nanobot/.venv`，再使用该环境里的 `python`。
- 使用配置 `nanobot/configs/tableclaw-bailian-dashscope.json`。
- 自动设置 `DASHSCOPE_API_KEY`；如果外部环境已设置同名变量，则优先使用外部变量。
- 执行 `python -m nanobot agent --config ... --no-logs`，进入交互模式。

安全备注：为了满足“只执行 `./start.sh`，不再输入虚拟环境和参数”的需求，脚本内有本地默认 API Key。后续如果要提交到公开仓库或发给别人，先改成只从环境变量、`.env` 或系统钥匙串读取。

### 启动脚本交互修复

现象：在未手动 `source nanobot/.venv/bin/activate` 的 shell 中直接执行 `./start.sh`，nanobot 能进入交互界面但第一次会自动收到 EOF 并退出；手动激活 venv 后再执行正常。

处理：更新 `start.sh`，让脚本内部先 `source nanobot/.venv/bin/activate`，再执行 `python -m nanobot ...`。这样保留“一键启动”，同时让 prompt_toolkit/交互 CLI 拿到完整虚拟环境上下文。

### 工作区迁移到项目目录

问题：初始 workspace 位于 `~/.nanobot/tableclaw-workspace`，位置较深，不方便查看 `USER.md`、`SOUL.md`、会话历史、输出和调试文件，也会让 TableClaw 运行状态散落到用户全局目录。

处理：

- 将 `nanobot/configs/tableclaw-bailian-dashscope.json` 中的 `agents.defaults.workspace` 改为 `/Users/hxy/Desktop/TableClaw/workspace`。
- 将旧 workspace 内容从 `~/.nanobot/tableclaw-workspace/` 复制到项目内 `workspace/`。
- 保留旧目录不删除，避免误删已有本地状态。

后续查看重点：

- `workspace/USER.md`
- `workspace/SOUL.md`
- `workspace/AGENTS.md`
- `workspace/memory/MEMORY.md`
- `workspace/memory/history.jsonl`
- `workspace/sessions/`
- `workspace/skills/`

### 搭建第一版 eval_test/test_dataset

目标：先完成一个很小的评测数据集，用来验证 TableClaw 对 Excel 表格的基本读取、定位、筛选和排序能力。

输入表池：

- 原始目录：`test_table/`
- 本次选表：`test_table/市州数据-营业收现率台账.xlsx`

新增目录：

- `eval_test/README.md`
- `eval_test/test_dataset/README.md`
- `eval_test/test_dataset/manifest.json`
- `eval_test/test_dataset/tasks.jsonl`
- `eval_test/test_dataset/tables/市州数据-营业收现率台账.xlsx`

设计决定：

- 不把测试表放进 `workspace/`。
- `workspace/` 是 nanobot 运行态，存放 memory、sessions、用户级 skills 和临时输出。
- eval 数据集是项目资产，放在 `eval_test/test_dataset/`，并复制本次需要的表格，避免依赖全量 `test_table/`。

当前任务：

1. `tc_smoke_001`：问 202602 期间“营业收现率完成”最高的单位及数值。
   - Gold：达州，`1.08669577950616`。
2. `tc_smoke_002`：问 202601 期间“营业收现率完成”低于 `0.7` 的单位和数量。
   - Gold：6 个，分别为自贡、攀枝花、雅安、阿坝、甘孜、凉山。

后续方向：

- 加 eval runner：读取 JSONL，调用 `./start.sh --message ...` 或 SDK，记录模型答案。
- 加判分器：先做 structured exact/numeric tolerance，再考虑 LLM-as-judge。
- 网站上传文件时，建议进入单独的 upload/storage 目录，例如 `workspace/uploads/<session_id>/` 或服务端专用 `storage/uploads/<tenant>/<upload_id>/`；不要直接混入固定 eval dataset。

### 加入 xlsx skill 作为最小可演示 skill 选择机制

需求：希望看到当用户问题涉及表格时，框架可以选择 skill，再调用工具解决问题；并且 skill/no skill 行为有区别。

实现选择：不改 nanobot 核心，只新增用户级 workspace skill：

- `workspace/skills/xlsx/SKILL.md`

原因：

- nanobot 已经支持从 `workspace/skills/` 自动发现 skill。
- `nanobot/nanobot/templates/agent/skills_section.md` 已明确要求：要使用 skill，先用 `read_file` 读取对应 `SKILL.md`。
- 这种方式只改项目运行态/配置资产，不碰 agent loop/runner。

当前 `xlsx` skill 内容：

- 触发范围：`.xlsx`、`.xlsm`、`.xls`、`.csv`、`.tsv`，以及用户询问 spreadsheet/table 文件。
- 推荐流程：先 inspect workbook，再用 `exec` + Python + `openpyxl` 精确计算。
- 对 TableClaw eval 表格增加提示：两级表头、月份在第 1 行、指标在第 2 行、`市州合计` 为汇总行。

skill/no skill 对比建议：

- skill：默认 `./start.sh`。
- no skill：在配置里临时设置 `agents.defaults.disabledSkills = ["xlsx"]`，或者后续增加一份 no-skill config/runner 统一跑对照。

### Skill/no-skill 手动对照测试

该早期手动对照结果已合并到统一矩阵报告：

- `docs/实验评测/skill-matrix/xlsx-skill-selection-matrix.md`

结论简述：

- skill on：模型明确读取 `workspace/skills/xlsx/SKILL.md`，再读取表格，并用 Python/openpyxl 计算；答案正确。
- skill off：模型没有读取 skill，先尝试直接读取表格文本化输出，遇到截断后改用 Python；答案也正确，但过程更绕。
- 当前手动对照已能展示“表格任务触发 skill 选择 + 工具调用”的过程。

Token 统计补充：

- 早期曾新增单次 token 对照脚本，用于 skill-on/skill-off token 对照。
- 该能力后续已统一由 `eval_test/run_eval.py` 接管，旧脚本与旧结果快照已清理。
- 本次 hard prompt 结果：
  - skill on：35,562 total tokens。
  - skill off：57,234 total tokens。
  - no-skill 比 skill-on 多 21,672 tokens，约 +60.9%。
- 这一步先证明 skill/no-skill 的 token 差异；随后已把 usage 持久化接入 AgentLoop，见下一节。

### Token usage 运行时持久化

详见独立文档：

- `docs/功能开发/token-usage.md`

实现：

- 新增 `nanobot/nanobot/utils/usage_log.py`，用 JSONL + file lock 写入 usage。
- 修改 `nanobot/nanobot/agent/loop.py`，在每轮 AgentLoop 保存会话时同步记录 usage。
- 新增 `eval_test/summarize_usage.py`，用于汇总 `workspace/usage/usage.jsonl`。

输出位置：

- `workspace/usage/usage.jsonl`

记录内容：

- session、turn、model、provider、token usage、tools_used、stop_reason、latency_ms 等。

说明：

- 这是运行时能力，不再只依赖 eval 脚本。
- 正常 `./start.sh` 对话和 `./start.sh --message ...` 都会写入。
- 纯命令或未发生模型调用的轮次不会产生 usage 记录。

### 显示工具调用过程

需求：启动后能在终端看到 agent 是否读取 skill、是否调用工具，而不是只看到最终答案。

处理：

- 将 `nanobot/configs/tableclaw-bailian-dashscope.json` 的 `channels.sendToolHints` 改为 `true`。
- 保持 `nanobot/nanobot/templates/agent/skills_section.md` 的原生机制：模型如果决定使用 skill，会通过 `read_file` 读取对应 `SKILL.md`。

预期展示：

- 当用户提出 xlsx/table 问题时，如果模型自然选择 `xlsx` skill，终端会显示读取 `nanobot/nanobot/skills/xlsx/SKILL.md` 的 tool hint。
- 由于 tool hints 已开启，终端也会显示执行 Python/openpyxl 等工具调用提示。

## 2026-05-29

### 整理 docs 文档结构

目标：把原先平铺在 `docs/` 下的文档整理成长期可维护的信息架构。

新增总索引：

- `docs/README.md`

分类目录：

- `docs/架构/`
- `docs/功能开发/`
- `docs/实验评测/`
- `docs/项目管理/`

移动结果：

- `docs/project-structure.md` -> `docs/架构/project-structure.md`
- `docs/token-usage.md` -> `docs/功能开发/token-usage.md`
- skill/no-skill 对照与后续 trace 统一收敛到 `docs/实验评测/skill-matrix/xlsx-skill-selection-matrix.md`
- `docs/development-log.md` -> `docs/项目管理/development-log.md`

新增功能文档：

- `docs/功能开发/skill-system.md`

该文档记录：

- nanobot skill 的 builtin/workspace 两类来源。
- workspace skill 优先覆盖 builtin skill 的加载规则。
- skill summary 如何进入 system prompt。
- 基模如何基于 name/description/path 自行选择并读取 skill。
- TableClaw 上线时核心 skill 内置化、业务 skill workspace 化的建议。
- 后续增加 skill router 的方向。

### 分析三个参考 Spreadsheet Skill

新增文档：

- `docs/功能开发/reference-spreadsheet-skills.md`

分析对象：

- `skills/codex/SKILL.md`
- `skills/kimi_xlsx_skill/SKILL.md`
- `skills/anthropic_xlsx_skill/SKILL.md`

结论：

- Codex skill 更偏高质量创建/编辑/渲染/验证 workbook artifact，适合吸收产物质量和 verify/render 闭环。
- Kimi skill 更偏 Excel 结构验证和 PivotTable 工具链，适合吸收 inspect、recheck、reference-check、validate、pivot 顺序。
- Anthropic/Claude skill 更贴近当前 TableClaw v0 的 Python/openpyxl 路线，适合吸收公式不硬编码、LibreOffice 重算、公式错误扫描、模板保持等规范。
- 三者都不建议整包搬入 nanobot；下一步应写 TableClaw Core Table Skill v0，吸收三者强项。

### 将 Codex Spreadsheet Skill 接入 nanobot builtin

目标：验证不依赖 workspace 用户级 skill 时，nanobot 主流程是否仍能通过 builtin skill 发现和调用表格能力。

处理：

- 新增 `nanobot/nanobot/skills/xlsx/SKILL.md`。
- 内容来自 `skills/codex/SKILL.md`，作为单文件 Codex Spreadsheets 参考版本先接入。
- 删除 `workspace/skills/xlsx/SKILL.md`。
- 保留 skill 名称为目录名 `xlsx`，这样 `nanobot/configs/tableclaw-bailian-dashscope-no-xlsx-skill.json` 里的 `disabledSkills: ["xlsx"]` 仍然有效。
- 后续由 `eval_test/run_eval.py` 统一识别旧 workspace 路径和新 builtin 路径。

当前加载验证：

- `SkillsLoader` 现在返回 `xlsx` 的 source 为 `builtin`。
- 路径为 `/Users/hxy/Desktop/TableClaw/nanobot/nanobot/skills/xlsx/SKILL.md`。

注意：

- 当前 builtin `xlsx` 是 Codex 参考 skill 原文，偏 workbook 创建/编辑/渲染/验证。
- 它不一定最适合 TableClaw 的表格 QA 场景，后续还需要测试模型是否会因 artifact-tool 依赖而绕路或受阻。
- 如果测试发现过重，应继续沉淀更轻的 `tableclaw-table` builtin skill。

验证结果：

- 运行 `./start.sh --message ... --session cli:builtin-xlsx-skill-smoke`。
- 模型读取了 `nanobot/nanobot/skills/xlsx/SKILL.md`。
- 模型最终答对：202602 期间最高单位为达州，值为 `1.08669577950616`。
- 本轮 usage：`total_tokens=91892`，`prompt_tokens=90451`，`completion_tokens=1441`，`cached_tokens=44800`。
- 后续已合并进统一矩阵报告：`docs/实验评测/skill-matrix/xlsx-skill-selection-matrix.md`。

观察：

- builtin skill 调用成功。
- 模型不是第一步就读 skill，而是先读表遇到截断后再读 skill。
- Codex skill 原文约 38KB，明显偏重；下一步更应该写 TableClaw 专用轻量表格 QA skill。

### 增加 Skill Selection Trace

目标：把“模型有没有选择 skill、什么时候选择、调用了哪些工具、token 消耗多少”做成可复现日志，方便后续评估和复查。

输出：

- `eval_test/results/skill_matrix/latest_eval.json`
- `docs/实验评测/skill-matrix/latest-eval-summary.md`
- `docs/实验评测/skill-matrix/xlsx-skill-selection-matrix.md`

本次复杂问题结果：

- 模型第 1 个工具调用就是读取 `nanobot/nanobot/skills/xlsx/SKILL.md`。
- 随后读取测试 xlsx 表，再用 Python/openpyxl 精确计算。
- 答案命中关键 gold facts：Top3 为达州、乐山、巴中，使用 `Sheet1`，排除 `市州合计`。
- usage：`total_tokens=61239`，`prompt_tokens=58921`，`completion_tokens=2318`，`cached_tokens=33152`。

随后补充 simple/complex × skill-on/skill-off 矩阵实验：

| Case | Mode | Skill selected | Skill step | Correct | Total tokens |
| --- | --- | --- | ---: | --- | ---: |
| simple | skill-on | true | 1 | true | 73,161 |
| simple | skill-off | false | - | true | 55,624 |
| complex | skill-on | true | 1 | true | 70,227 |
| complex | skill-off | false | - | true | 74,139 |

观察：

- skill-on 的 simple 和 complex 两个问题都在第 1 个 tool step 读取 builtin `xlsx` skill。
- simple 问题中，skill-on 比 skill-off 多 17,537 tokens（+31.5%），说明当前 Codex 原版 skill 对简单 QA 偏重。
- complex 问题中，skill-on 比 skill-off 少 3,912 tokens（-5.3%），说明复杂任务更能体现 skill 提前加载流程的价值。
- 这个结果支持下一步：保留 builtin skill 机制，但裁剪成更轻、更偏 TableClaw QA 的 `tableclaw-table` skill。

### 整理 eval_test 脚本

目标：把 `eval_test/` 从临时脚本整理为可持续迭代的评测模块。

新增统一入口：

- `eval_test/run_eval.py`

能力：

- 读取 `eval_test/test_dataset/tasks.jsonl`。
- 支持 `skill-on` / `skill-off` 两种配置。
- 记录答案预览、工具调用时间线、是否读取 xlsx skill、skill 读取 step、token usage、latency。
- 输出 `eval_test/results/skill_matrix/latest_eval.json` 和 `docs/实验评测/skill-matrix/latest-eval-summary.md`。

整理：

- 删除旧的单次 token 对照脚本，token 对照由 `run_eval.py` 统一承担。
- 清理 `eval_test/__pycache__/` 和旧结果快照。
- `summarize_usage.py` 保留，职责是汇总运行时长期 usage 日志 `workspace/usage/usage.jsonl`。

### 新增一键评测脚本

新增：

- `eval.sh`

用途：

- 在项目根目录直接运行 `./eval.sh` 即可调用 `eval_test/run_eval.py`。
- 自动激活 `nanobot/.venv`。
- 复用 `DASHSCOPE_API_KEY` 环境变量；如果外部未设置，则使用本地默认值。
- 参数会透传给 `run_eval.py`，例如 `./eval.sh --list-tasks`。

### 统一 eval task 集

目标：避免 `tasks.jsonl` 和 `skill_selection_matrix_tasks.jsonl` 分散维护。

处理：

- 删除 `eval_test/test_dataset/skill_selection_matrix_tasks.jsonl`。
- 将任务统一维护在 `eval_test/test_dataset/tasks.jsonl`。
- 当前任务数扩展到 10 个。
- 增加 `difficulty` 字段：`simple` / `medium` / `hard`。
- 保留 `case` 字段：`simple` / `medium` / `complex`，用于 skill-selection matrix 的 focused run。
- 更新 `eval_test/run_eval.py`，默认只读取统一的 `tasks.jsonl`。
- 新增筛选参数：
  - `--difficulty simple|medium|hard`
  - `--case simple|medium|complex`

当前任务覆盖：

- simple：直接最高值、阈值筛选、计数。
- medium：Top/Bottom 排名、跨期变化、阈值排序。
- hard：多期间 Top5 交集、连续两期阈值筛选、均值/最高/最低聚合。

说明：不维护一次性汇报文档；需要对外说明时，从实验评测和功能开发文档中提取即可。

### 完成 10-task skill/no-skill 对照评测

执行：

- `./eval.sh`

范围：

- 10 个统一评测任务。
- 每个任务分别跑 `skill-on` 与 `skill-off`，共 20 次模型调用。
- 表格统一为 `eval_test/test_dataset/tables/市州数据-营业收现率台账.xlsx`。

产物：

- 原始 JSON：`eval_test/results/skill_matrix/latest_eval.json`
- 自动报告：`docs/实验评测/skill-matrix/latest-eval-summary.md`
- 人工整理矩阵：`docs/实验评测/skill-matrix/xlsx-skill-selection-matrix.md`

结果摘要：

| Mode | Runs | Auto pass | Manual check | Skill reads | Total tokens | Avg tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| skill-on | 10 | 8/10 | 10/10 | 3/10 | 730,590 | 73,059 |
| skill-off | 10 | 7/10 | 10/10 | 0/10 | 712,548 | 71,254 |

观察：

- `skill-on` 并不等价于模型必然读取 skill；本轮 10 条中实际读取 `xlsx/SKILL.md` 的为 3 条。
- 实际读取 skill 的轮次均发生在第 3 个 tool step，说明模型常见路径是先看表或 tool-result，再决定补读 skill。
- `skill-off` 没有读取内置 skill，说明禁用配置生效。
- 自动评分的 false 多数来自模型输出四位小数而 gold 使用 `1e-6` 精度；人工核验排序、单位、数量和近似数值均正确。
- 当前 Codex 原版 spreadsheet skill 较重，整体 skill-on token 比 skill-off 多约 2.5%。后续如果要提高 TableClaw 的性价比，应裁剪为轻量、只服务表格问答的 TableClaw skill。

### 新增 TableClaw Skill Pipeline 可视化

新增：

- `docs/架构/tableclaw-skill-pipeline.svg`
- `docs/架构/tableclaw-xlsx-case-flow.svg`

用途：

- 用一张图展示 TableClaw 的核心链路：用户表格问题 -> nanobot agent -> skill registry -> 选择 `xlsx` skill -> 表格执行 -> 答案生成 -> trace/token usage。
- 用另一张具体案例图展示 `tc_hard_003` 从输入问题、选中 `xlsx` skill、执行 openpyxl 计算到输出答案的过程。
- 只保留 SVG 图片，便于直接用于演示材料或幻灯片。

表达边界：

- 图用于解释当前能力链路，不夸大为“skill 一定优于 no-skill”。
- 当前实验支撑点是：builtin `xlsx` skill 可以被 nanobot 选择，skill/no-skill ablation 可以记录选择时机、工具轨迹、答案质量和 token usage。

### 清理临时展示分支，回到 Codex xlsx skill 主线

本次清理展示用的合成内容，恢复到更适合继续研发的基线：

- 恢复活动内置 skill：`nanobot/nanobot/skills/xlsx/SKILL.md`
- 删除展示用小 skill：`table-structure`、`table-aggregation`、`table-ranking`
- 删除展示用合成任务、结果和文档。
- 删除展示 HTML 目录：`docs/展示/`
- `skill-off` 配置重新只禁用 `xlsx`
- `eval_test/run_eval.py` 重新只追踪 `xlsx` skill

后续研发继续沿用当前主线：Codex Spreadsheets skill 内置接入、10-task eval、skill/no-skill 矩阵、token usage 统计。

### 清理展示分支残留，回到主线

目标：让代码和文档只保留当前研发主线，避免临时展示任务、专用 runner、专用 skill、专用文档影响后续判断。

处理：

- 删除展示分支 runner、任务集、表格副本、配置和临时小 skill。
- 删除展示分支报告和同步材料。
- `eval_test/` 回到单一入口：`run_eval.py` + `tasks.jsonl` + `skill_matrix/` 输出。
- `docs/实验评测/` 回到单一主线索引：`skill-matrix/`。
- `run_eval.py` 继续只追踪 builtin `xlsx` skill。
- 修正 `_fact_matches`：`count=6` 等数字事实不再用字符串子串匹配，而是按完整数字匹配，减少自动评分误判。

后续研发继续沿用当前主线：Codex Spreadsheets skill 内置接入、10-task eval、skill/no-skill 矩阵、token usage 统计。

### 修正项目定位 + 建立 TODO/dev-log 双文档

定位：之前的文档把 TableClaw 当成"表格 QA agent"，过窄。明确修正为**表格专精 agent**，商用形态需要覆盖 4 大场景：

1. QA / 分析（当前主要做的）
2. 编辑 / 修复 / 清洗
3. 表格转换 / 跨表合并
4. 报表生成 / 从 0 建表

后续 skill / tool / 评测题设计都必须对照这 4 类，避免又退化回"只服务 QA"。

文档分工：

- 新增 `docs/项目管理/TODO.md`：维护近期/中期/长期待办，复选框格式，做完打勾不删，保留迭代轨迹。
- 现有 `docs/项目管理/development-log.md`：保留"做了什么 + 为什么"，**不再写计划**。
- 完成一项时：TODO 打勾 + dev-log 补一段说明，互相引用。
- `docs/README.md` 顶部索引补充 TODO 入口。

后续路径锁定为：先 git init 打基线 → 修评分器 → 写 native xlsx skill v0（4 大场景占位）→ 跑对照评测 → 拿数据对齐主推场景。具体见 [TODO.md](TODO.md)。

### 扩充 TODO 中期计划：dataset 规模化 + 专用 tool 系列 + 多家 skill 横评

为了让 TableClaw 真正走向商用 + 表格全场景定位，TODO 的中期段补了三件事：

1. **Eval Dataset 规模化到 80–150 题**：4 场景 × 三档运算难度 × 三档表结构复杂度，混合 4 类来源（test_table 现有 / 公开 benchmark / 同学贡献 / 合成），后续招募 3–5 名同学协作。本身需要先写 `CONTRIBUTING.md` + `SCHEMA.md` 才能开放认领。
2. **5 个专用表格 tool**：`tableclaw_inspect / locate_column / aggregate / filter / topk`，命名规范 `tableclaw_<动词>` snake_case，接入 `nanobot/nanobot/agent/tools/tableclaw/` 子目录。三道关卡验证：单元测试、集成测试、A/B vs SKILL.md 形态。先写 RFC 文档，code review 后再实现。
3. **多家 skill 横评 + 自研优化**：codex / kimi / anthropic / claude-code / 自研 v0 在同一 dataset 上跑，**带依赖跑（不降级）**，每家做 docker 隔离（kimi 跑 linux ELF / anthropic 装 LibreOffice）。新写 `run_multi_skill.py` harness，输出对比矩阵，最终在 `docs/实验评测/multi-skill/decision.md` 里决定 skill 路线。

这三件事是相互依赖的：dataset 扩了之后 tool 与 skill 才能在足够样本上做对照；tool 与 skill 横评结果反过来决定 dataset 还要补哪些边界 case。所以中期段并行推进，里程碑是"在 80+ 题 dataset 上拿到 5 家 skill × 全部场景的横评矩阵"。

## 2026-06-06

### 对齐 TableClaw 方案设计与老师要求

新增文档：

- `docs/功能开发/tableclaw-positioning-and-workflow.md`
- `docs/实验评测/workflow-routing.md`

这次把老师要求的四段内容收敛为一条研发主线：

1. 产品调研：Copilot in Excel、Gemini in Sheets、WPS AI、通用 Agent、SpreadsheetBench。
2. Eval 测试：从 10-task QA matrix 扩展到 12-task，新增 workflow routing 任务。
3. 能力边界：表格理解、操作、结果生成、workflow、context 五类边界。
4. TableClaw 方案：基于 Nanobot 做 TableAgent workflow，沉淀阶段化 table skills，后续补 memory/context/RAG、可插拔 harness、验证和回滚。

### 新增 TableClaw 轻量 Workflow Skills

新增 builtin skills：

- `nanobot/nanobot/skills/table-read/SKILL.md`
- `nanobot/nanobot/skills/table-clean/SKILL.md`
- `nanobot/nanobot/skills/table-validate/SKILL.md`
- `nanobot/nanobot/skills/table-report/SKILL.md`
- `nanobot/nanobot/skills/table-formula-debug/SKILL.md`
- `nanobot/nanobot/skills/table-chart/SKILL.md`

设计原则：

- 不替代 Codex 原文 `xlsx` skill，先作为轻量阶段化 skill 池。
- 每个 skill 都短，聚焦一个 workflow 阶段。
- 目标是让模型在单轮或多轮表格任务中按阶段读取不同 skill，例如 `table-read -> table-clean -> table-validate -> table-report`。

### 更新 Skill/no-skill Harness

修改：

- `eval_test/run_eval.py`
- `nanobot/configs/tableclaw-bailian-dashscope-no-xlsx-skill.json`

变化：

- `TRACKED_SKILLS` 从只追踪 `xlsx` 扩展到追踪 7 个 skill。
- 结果 JSON 增加 `skill_read_sequence`。
- Markdown summary 增加 `Skill sequence` 列。
- `--case` 支持 `workflow`。
- skill-off 配置禁用 `xlsx` 和 6 个 TableClaw 轻量 table skills，保证 ablation 干净。

### 新增 Workflow Routing Tasks

修改：

- `eval_test/test_dataset/tasks.jsonl`
- `eval_test/test_dataset/README.md`
- `eval_test/test_dataset/manifest.json`

新增：

- `tc_workflow_001`：读表结构 + 数据质量检查 + 判断是否适合跨期分析。
- `tc_workflow_002`：读表、清洗、两期低于阈值筛选、排序、管理建议、校验说明。

当前数据集从 10 题扩展到 12 题。

### 后续判断

下一步应先跑：

```bash
./eval.sh --case workflow
```

观察结果：

- skill-on 是否读取多个轻量 skill。
- skill-off 是否完全不读 table skills。
- skill-on 是否减少重复探索、提升报告结构、保留校验说明。
- token 是否因为读取多个 skill 增加，还是因流程清晰下降。

如果模型仍偏向只读 `xlsx` 或不读 skill，优先调整 skill descriptions；如果仍不稳定，再考虑在 Nanobot 上加显式 table workflow router 或把 inspect/clean/validate 下沉成 tools。
