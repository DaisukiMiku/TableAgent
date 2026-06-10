# TableClaw 项目目录结构

> 本文件用于追踪 TableClaw 项目当前的目录组成与各部分职责。每次新增 / 删除 / 重构目录时同步更新本文件。
>
> 最后更新：2026-06-10（table schema cache 与 inspect tool 已接入）

---

## 顶层

```
TableClaw/
├── start.sh              # 本地一键启动 nanobot 交互聊天入口
├── eval.sh               # 一键运行 skill matrix / uploaded-table workflow eval
├── .gitignore
├── docs/                  # 本项目自身的文档（结构、设计决策、开发日志等）
├── eval_test/             # 评测数据集与 skill matrix runner
├── nanobot/               # 上游 nanobot 框架源码（TableClaw 二次开发的基础）
├── workspace/             # TableClaw 本地 nanobot 工作区（记忆、会话、上传表、输出）
├── test_table/            # 原始工业表格池（不直接作为干净 eval 集）
└── skills/                # 三个外部参考 skill（用作 TableClaw skill 设计参考）
    ├── anthropic_xlsx_skill/    # Anthropic 官方 xlsx skill（Python + openpyxl + LibreOffice）
    ├── kimi_xlsx_skill/         # Kimi xlsx skill（Python + KimiXlsx CLI，含 PivotTable）
    └── codex/                   # OpenAI Codex Spreadsheets skill（Node + @oai/artifact-tool）
```

### `workspace/` —— 本地运行工作区

```
workspace/
├── USER.md / SOUL.md / AGENTS.md / HEARTBEAT.md
├── uploads/              # 模拟用户上传表；未来 Web 前端上传也对齐这里
├── table_index/
│   └── tables.jsonl      # uploaded-table workflow 的 schema-based 召回索引
├── table_cache/
│   └── *.schema.json     # tableclaw_inspect 生成的 sheet/header/column/sample cache
├── memory/
├── sessions/
├── usage/
│   └── usage.jsonl       # 每轮模型调用 token usage 与工具/延迟统计
└── skills/               # 用户级 skill 覆盖层；当前不放 TableClaw 核心 xlsx skill
```

---

## `nanobot/` —— 框架本体

```
nanobot/
├── .agent/                # 给 AI agent 看的项目元规范（必读）
│   ├── design.md          # 架构约束（核心保持小，能力下沉到 channels/tools/skills）
│   ├── security.md        # 安全边界（workspace 限制、SSRF、shell sandbox）
│   └── gotchas.md         # 常见坑（禁用 ruff format、原子写、Windows 兼容等）
├── CLAUDE.md              # Claude Code 视角的项目说明（含开发命令、子系统总览）
├── CONTRIBUTING.md        # 分支策略与 PR 规范（main vs nightly 双分支模型）
├── README.md              # 项目主 README（README 中引用的 case/ images/ 已被裁剪，链接会失效，可后续重写）
├── THIRD_PARTY_NOTICES.md # ⚠ 被 pyproject.toml 的 license-files 引用，不能删
├── pyproject.toml         # Python 包定义（含 force-include 把 bridge 打进 wheel）
├── configs/               # TableClaw 本地运行配置模板（不直接写入明文密钥）
│   ├── tableclaw-bailian-dashscope.json  # 百炼 DashScope OpenAI 兼容接口配置
│   └── tableclaw-bailian-dashscope-no-xlsx-skill.json  # 对照测试：禁用 xlsx + TableClaw table skills
├── hatch_build.py         # 自定义构建钩子
├── docker-compose.yml / Dockerfile / entrypoint.sh / .dockerignore   # 容器化部署
├── bridge/                # TypeScript 桥接服务（如 WhatsApp）；构建时打进 wheel
│   ├── src/
│   ├── package.json
│   └── tsconfig.json
├── docs/                  # nanobot 用户文档（不是 TableClaw 的文档；保留作参考）
│   ├── quick-start.md / configuration.md / deployment.md
│   ├── chat-apps.md / chat-commands.md / cli-reference.md
│   ├── channel-plugin-guide.md / my-tool.md
│   ├── memory.md / image-generation.md / agent-social-network.md
│   ├── multiple-instances.md / openai-api.md / python-sdk.md / websocket.md
│   └── README.md
├── webui/                 # Vite + React + TypeScript 前端 SPA
│   ├── public/ (含 brand/)
│   ├── src/
│   │   ├── App.tsx / main.tsx / globals.css
│   │   ├── components/    # UI 组件
│   │   ├── hooks/         # React hooks
│   │   ├── i18n/          # 多语言
│   │   ├── lib/           # 工具函数
│   │   ├── providers/     # React Context providers
│   │   ├── types/
│   │   └── workers/       # Web Workers
│   ├── vite.config.ts     # 开发代理 /api /webui /auth 与 WS 到 gateway:8765
│   ├── tailwind.config.js / postcss.config.js
│   ├── tsconfig.json / tsconfig.build.json
│   ├── package.json / bun.lock / package-lock.json
│   └── eslint.config.js
└── nanobot/               # ★ Python 包主体
```

### `nanobot/nanobot/` —— Python 包（核心）

```
nanobot/
├── __init__.py / __main__.py
├── nanobot.py             # Python SDK 入口（facade）
├── agent/                 # ★ Agent 核心（修改要克制，遵守 design.md）
│   ├── loop.py            # AgentLoop：消息消费、上下文构建、hooks 协调（68 KB，关键路径）
│   ├── runner.py          # AgentRunner：多轮 LLM 对话 + 工具执行（54 KB，关键路径）
│   ├── context.py         # 上下文构建
│   ├── memory.py          # 历史持久化 + Dream 两阶段记忆（46 KB，原子写 history.jsonl）
│   ├── autocompact.py     # TTL 触发的自动压缩
│   ├── hook.py            # 生命周期钩子
│   ├── progress_hook.py   # 进度事件
│   ├── model_presets.py   # 模型预设（带 WebUI badge）
│   ├── skills.py          # skill 加载与上下文注入
│   ├── subagent.py        # 子 agent 派生
│   └── tools/             # ★ Agent 可调用的工具集（plugin 自动发现）
│       ├── base.py / registry.py / loader.py / schema.py / context.py
│       ├── filesystem.py  # read/write/edit/list（强制走 _resolve_path）
│       ├── shell.py       # ExecTool（含 sandbox.py 包装）
│       ├── sandbox.py     # bwrap 沙箱后端
│       ├── exec_session.py / file_state.py / runtime_state.py
│       ├── apply_patch.py / path_utils.py
│       ├── search.py / web.py        # 搜索 / web fetch（走 SSRF 校验）
│       ├── mcp.py                    # MCP server 集成
│       ├── cron.py / long_task.py    # 定时 + 长任务
│       ├── image_generation.py
│       ├── message.py / spawn.py / cli_apps.py / self.py
│       ├── tableclaw.py              # TableClaw builtin tools：上传表召回 + schema inspect/cache
├── api/
│   ├── __init__.py
│   └── server.py          # OpenAI 兼容 HTTP API（/v1/chat/completions, /v1/models, SSE）
├── apps/
│   └── cli/               # CLI 应用
├── bus/
│   ├── queue.py           # 异步 MessageBus，解耦 channel 与 agent 核心
│   └── events.py          # InboundMessage / OutboundMessage 事件类型
├── channels/              # ★ 平台适配（auto-discovery via pkgutil + entry-point）
│   ├── base.py / manager.py / registry.py
│   ├── telegram.py / discord.py / slack.py / feishu.py
│   ├── matrix.py / signal.py / whatsapp.py
│   ├── qq.py / weixin.py / wecom.py / dingtalk.py / mochat.py
│   ├── msteams.py / email.py / websocket.py
├── cli/
│   ├── commands.py        # CLI 入口
│   ├── models.py / onboard.py / stream.py
├── command/
│   ├── router.py          # /xxx slash 命令路由
│   └── builtin.py         # 内置命令
├── config/
│   ├── schema.py          # ★ Pydantic 配置模型（camelCase 别名兼容 JSON）
│   ├── loader.py          # 读取 ~/.nanobot/config.json，解析 ${VAR}（缺失即抛错）
│   └── paths.py
├── cron/                  # 定时任务
├── heartbeat/             # 周期性 agent 唤醒（heartbeat 虚拟工具调用模式）
├── pairing/               # DM 发送方授权码持久化
├── providers/             # ★ LLM provider（基于 base.py，factory + registry 装配）
│   ├── base.py / factory.py / registry.py
│   ├── anthropic_provider.py
│   ├── openai_compat_provider.py
│   ├── openai_responses/         # OpenAI Responses API（独立子包）
│   ├── azure_openai_provider.py
│   ├── bedrock_provider.py
│   ├── github_copilot_provider.py
│   ├── openai_codex_provider.py
│   ├── fallback_provider.py      # fallback_models 实现
│   ├── image_generation.py
│   └── transcription.py          # 音频转写
├── security/
│   ├── network.py         # validate_url_target（SSRF 防护，封 RFC1918 + 元数据端点）
│   └── __init__.py        # PTH 守卫等启动时安全措施
├── session/
│   ├── manager.py         # 会话历史 + TTL 自动压缩
│   ├── goal_state.py      # /goal 长目标状态
│   └── webui_turns.py
├── skills/                # ★ 内置 skill 目录（每个目录一个 SKILL.md）
│   ├── README.md
│   ├── xlsx/SKILL.md                     # Codex Spreadsheets skill，当前宽能力兜底 skill
│   ├── table-read/SKILL.md               # TableClaw 轻量 skill：结构读取、表头、指标列定位
│   ├── table-clean/SKILL.md              # TableClaw 轻量 skill：空行、合计行、缺失值、类型清洗
│   ├── table-validate/SKILL.md           # TableClaw 轻量 skill：口径、数值、排序、证据校验
│   ├── table-report/SKILL.md             # TableClaw 轻量 skill：管理摘要、风险列表、建议
│   ├── table-formula-debug/SKILL.md      # TableClaw 轻量 skill：公式读取、错误值、引用修复
│   ├── table-chart/SKILL.md              # TableClaw 轻量 skill：图表选择、chart-ready summary
│   ├── github/SKILL.md
│   ├── weather/SKILL.md
│   ├── summarize/SKILL.md
│   ├── tmux/SKILL.md (含 scripts/)
│   ├── cron/SKILL.md
│   ├── image-generation/SKILL.md
│   ├── long-goal/SKILL.md
│   ├── memory/SKILL.md
│   ├── update-setup/SKILL.md
│   ├── clawhub/SKILL.md            # 从 ClawHub 注册中心搜索/安装 skill
│   ├── skill-creator/              # 含 init_skill.py / package_skill.py / quick_validate.py
│   └── my/                         # 用户自定义 skill 占位（含 references/examples.md）
├── templates/             # Jinja2 提示词模板（修改等同改 Python 代码）
│   ├── AGENTS.md / SOUL.md / USER.md / HEARTBEAT.md
│   ├── agent/             # agent 子模板
│   └── memory/            # memory 子模板
├── utils/                 # 通用工具
│   ├── prompt_templates.py        # 加载 templates/*.md
│   ├── artifacts.py / document.py / media_decode.py
│   ├── path.py / file_edit_events.py / progress_events.py
│   ├── llm_runtime.py / runtime.py / restart.py
│   ├── searchusage.py / tool_hints.py / image_generation_intent.py
│   ├── subagent_channel_display.py / logging_bridge.py
│   ├── usage_log.py                # TableClaw 运行时 usage JSONL 持久化
│   ├── evaluator.py / gitstore.py / helpers.py
└── web/                   # WebUI 构建产物挂载点（webui/ build → 此处，打进 wheel）
└── webui/                 # WebUI 后端服务（gateway 模块）
```

---

## `skills/` —— 三个参考 Skill

| Skill | 形态 | 主要技术 | 验证手段 | 突出能力 |
| --- | --- | --- | --- | --- |
| `anthropic_xlsx_skill/` | `SKILL.md` + `scripts/recalc.py` + `scripts/office/` | Python + openpyxl + LibreOffice 子进程 | recalc.py（重算公式 + 扫描所有 Excel 错误） | 财务模型颜色规范（蓝色输入/黑色公式…）、ZERO formula errors |
| `kimi_xlsx_skill/` | `SKILL.md` + `pivot-table.md` + `scripts/KimiXlsx`（**Linux ELF 二进制 77MB**） | Python + openpyxl + KimiXlsx CLI（OpenXML SDK） | recheck / reference-check / chart-verify / validate | PivotTable（OpenXML 真实结构）、Monochrome / Finance 双风格、按 sheet 逐张校验循环 |
| `codex/` | `SKILL.md` 一个文件 | Node.js + `@oai/artifact-tool` JS 库 | `workbook.inspect` / `workbook.render` / `workbook.trace` | 一体化 JS API、原生 chart/table/data validation/conditional format、Google Sheets 导入路径 |

### `anthropic_xlsx_skill/` 内部

```
anthropic_xlsx_skill/
├── SKILL.md
├── LICENSE.txt
└── scripts/
    ├── recalc.py                    # 通过 LibreOffice 重算 + 扫错（输出 JSON）
    └── office/
        ├── soffice.py / pack.py / unpack.py / validate.py
        ├── helpers/                 # simplify_redlines.py / merge_runs.py
        ├── validators/              # docx.py / pptx.py / redlining.py / base.py
        └── schemas/                 # OOXML 官方 XSD（microsoft/ + ISO-IEC29500-4_2016/）
```

### `kimi_xlsx_skill/` 内部

```
kimi_xlsx_skill/
├── SKILL.md                # 主体 skill（含风格规范、PivotTable 触发条件）
├── pivot-table.md          # PivotTable 专用补充文档（按需加载）
└── scripts/
    └── KimiXlsx            # Linux x86-64 ELF 可执行文件（macOS 不能直接用）
```

### `codex/` 内部

```
codex/
└── SKILL.md                # 单文件，依赖 @oai/artifact-tool node_modules（外部依赖）
```

---

## 关键扩展点速查

| 想做的事 | 应该改 / 加在哪里 |
| --- | --- |
| 加新工具（agent 能调用的能力） | `nanobot/nanobot/agent/tools/<new_tool>.py`，继承 `base.py` |
| 加新 channel（接入新 IM 平台） | `nanobot/nanobot/channels/<platform>.py`，继承 `base.py` |
| 加新 LLM provider | `nanobot/nanobot/providers/<provider>.py`，继承 `base.py`，在 `factory.py` / `registry.py` 注册 |
| 加新 skill（procedural 知识，非代码） | `nanobot/nanobot/skills/<skill-name>/SKILL.md`（YAML frontmatter + Markdown） |
| 用户级 skill（不进框架） | `<workspace>/skills/<skill-name>/SKILL.md`，运行时自动发现 |
| 改提示词 | `nanobot/nanobot/templates/*.md`（Jinja2） |
| 改配置项 | `nanobot/nanobot/config/schema.py` 加 Pydantic 字段 |
| 改 WebUI | `nanobot/webui/src/`，开发用 `bun run dev`，构建产物落到 `nanobot/web/dist` |

---

## `eval_test/` —— 评测数据 + Runner

```
eval_test/
├── README.md
├── run_eval.py                # 12-task skill matrix runner（./eval.sh 调用）
├── summarize_usage.py         # 长期 usage 汇总（独立工具）
├── results/
│   ├── skill_matrix/          # ./eval.sh 输出
│   │   ├── latest_eval.json
│   │   └── skill_trace_matrix_latest.json
└── test_dataset/
    ├── README.md
    ├── manifest.json
    ├── tasks.jsonl                          # 12 任务（skill matrix + workflow routing）
    └── tables/
        └── 市州数据-营业收现率台账.xlsx       # skill matrix 表（29×54）
```

设计边界：

- `test_table/`：原始工业表格池，保留全量表格。
- `eval_test/test_dataset/`：清洗后的评测子集，只放少量明确任务、gold answer 和对应表格副本。
- `workspace/`：nanobot 运行状态，不放固定评测数据；避免 memory/session 与 eval 数据耦合。

## 当前评测主线

| Line | Runner | Config | Skill | Dataset | 报告 |
| --- | --- | --- | --- | --- | --- |
| **Skill Matrix** | `./eval.sh` | `tableclaw-bailian-dashscope*.json` | `xlsx` + TableClaw table skills | `tasks.jsonl`（12 任务） | [`docs/实验评测/skill-matrix/xlsx-skill-selection-matrix.md`](../实验评测/skill-matrix/xlsx-skill-selection-matrix.md) |

当前只保留这条主线，避免临时展示任务、专用 skill、专用配置污染后续研发。

---

## 当前 Skill 接入

TableClaw 当前在 nanobot builtin skills 目录下保留一组主线表格 skill：

```
nanobot/nanobot/skills/
├── xlsx/SKILL.md                       # Codex Spreadsheets 原文，宽能力兜底
├── table-read/SKILL.md                 # 读表结构
├── table-clean/SKILL.md                # 清洗口径
├── table-validate/SKILL.md             # 校验证据
├── table-report/SKILL.md               # 报告输出
├── table-formula-debug/SKILL.md        # 公式调试
└── table-chart/SKILL.md                # 图表/看板
```

- `tableclaw-bailian-dashscope.json`（skill matrix on 模式）：默认全开。
- `tableclaw-bailian-dashscope-no-xlsx-skill.json`（skill matrix off）：禁用 `xlsx` 与 6 个 TableClaw table skills。

不修改 `nanobot/nanobot/agent/loop.py` / `runner.py`，不改 skill loader。

nanobot 原生行为：

1. 启动时先扫描 `workspace/skills/*/SKILL.md`
2. 再扫描 `nanobot/nanobot/skills/*/SKILL.md`
3. workspace 同名 skill 会覆盖 builtin skill
4. 将 skill 名称、description、路径注入上下文摘要
5. 当任务匹配 description 时，agent 可用 `read_file` 读取对应 `SKILL.md`
6. 后续按 skill 指令调用工具

当前配置 `channels.sendToolHints` 已开启，因此如果模型读取 skill 文件或执行工具，终端会展示对应过程提示。

详细机制见 [Skill 模块设计](../功能开发/skill-system.md)。
两条实验线的具体表现分别见 [实验评测索引](../实验评测/README.md)。

---

## 当前本地模型配置

为先跑通 TableClaw 的 nanobot 基座，新增配置模板：

- `start.sh`：项目根目录的一键交互聊天入口，内部使用 `nanobot/.venv` 与下方配置文件
- `nanobot/configs/tableclaw-bailian-dashscope.json`
- Provider：`dashscope`
- API Base：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- 当前模型：`deepseek-v4-pro`
- Reasoning：`reasoningEffort: "high"`，由 nanobot 的 DashScope provider 转换为 `reasoning_effort` + `enable_thinking`
- Workspace：`/Users/hxy/Desktop/TableClaw/workspace`
- API Key：通过环境变量 `${DASHSCOPE_API_KEY}` 注入，不在仓库文档中保存明文密钥

启动方式：

```bash
./start.sh
```

`start.sh` 会自动激活 `nanobot/.venv`，优先使用调用方已设置的 `DASHSCOPE_API_KEY`；如果未设置，则使用脚本内置的本地默认 Key。

注意：用户口头目标写作 “Kimi K2.6”，但本次提供的百炼文档示例与能力表对应 `deepseek-v4-pro` / DeepSeek 系列。当前配置以可验证的文档示例模型为准；如果后续确认 Kimi K2.6 在百炼中的真实 model id，只需要替换配置文件里的 `agents.defaults.model`，必要时再调整 provider/extra body。

---

## 不要碰 / 谨慎碰

- `nanobot/nanobot/agent/loop.py` 与 `runner.py` —— 关键路径，改动需要明确正当性
- `nanobot/nanobot/agent/memory.py` 中的原子写（temp + fsync + rename） —— 不能换成普通 `open(..., "w")`
- 不要执行 `ruff format`（破坏 git blame）；只用 `ruff check`
- 任何路径处理必须走 `agent/tools/filesystem.py:_resolve_path`
- 任何 HTTP 出站必须走 `security/network.py:validate_url_target`

---

## 裁剪记录（2026-05-28）

为降噪、聚焦 TableClaw 二次开发，从上游 nanobot 移除了以下与开发本身无关的资产（共 ≈34 MB）：

| 路径 | 性质 |
| --- | --- |
| `nanobot/tests/` | 上游 pytest 用例；TableClaw 后续自建 |
| `nanobot/webui/src/tests/` | 前端单测；同上 |
| `nanobot/case/` | README 演示 GIF（30 MB） |
| `nanobot/images/` | README 图片资源 |
| `nanobot/.github/` | 上游 GitHub issue 模板 / workflow |
| `nanobot/SECURITY.md` | 上游漏洞披露策略（注意保留了 `nanobot/nanobot/security/` Python 模块） |
| `nanobot/COMMUNICATION.md` | 上游沟通渠道说明 |
| `nanobot/core_agent_lines.sh` | 上游统计脚本 |
| `nanobot/.gitattributes` | 上游 git 属性 |
| `**/.DS_Store` | macOS 元数据 |

未删但属于"评估后保留"的项：

- `THIRD_PARTY_NOTICES.md` —— 被 `pyproject.toml: license-files` 引用
- `bridge/` —— 被 `pyproject.toml: force-include` 打进 wheel
- `Dockerfile / docker-compose.yml / entrypoint.sh / .dockerignore` —— 后续 TableClaw 部署可复用
- `nanobot/docs/` —— 192 KB，作为 nanobot 用户视角参考文档
- `nanobot/CONTRIBUTING.md` —— 分支策略对开发流程仍有参考价值

> README.md 中对 `case/*.gif` 与 `images/*.png` 的引用现已失效，等 TableClaw 自己的 README 落地后会一起重写。
