# Claude Code Session Manager 计划文档

## 目标

做一个本机 Claude Code session 管理器，用来解决“我记得之前计划过某件事，但忘了在哪个 session 里”的问题。

第一阶段先做“UI-first 最小可用版”，验证数据链路、搜索找回和本机交互体验是否成立。验证通过后，再继续做“真正好用版”：自动摘要、计划/TODO/决策提取、语义搜索、解释式搜索结果、标签和收藏。

本文档的设计目标是：后续可以由一个主控 session 零人工介入地拆分任务、启动其他 Claude Code session 并完成最小可用版。

## 产品边界

### 最小可用版

最小可用版只解决一个 UI 闭环：

```text
扫描本机 Claude Code 历史 session
-> 解析基础元数据和消息文本
-> 建立本地索引
-> 启动本机 Web UI
-> 在 UI 里搜索关键词、筛选项目、浏览匹配片段
-> 打开 session 详情
-> 复制 claude --resume <session> 命令继续工作
```

必须具备：

- 扫描默认 Claude Code transcript 目录。
- 支持用户指定额外扫描目录。
- 识别 session id、项目路径、文件路径、时间、首条用户消息。
- 读取 JSONL transcript，容错处理坏行和未知字段。
- 将 session、message、chunk 写入 SQLite。
- 使用 SQLite FTS5 做全文检索。
- 本机 Web UI 支持 session 列表、关键词搜索、项目筛选、详情预览、匹配片段展示、resume 命令复制。
- 后端 API 支持扫描、搜索、详情、健康检查。
- CLI 保留 `scan`、`doctor`、`serve`，用于后台任务、排障和启动 UI。
- 不调用远程 LLM，不做语义搜索，不做自动摘要。

明确不做：

- 不修改 Claude Code 原始 session 文件。
- 不承诺恢复 git 工作区状态。
- 不做向量数据库。
- 不做自动计划/TODO/决策提取。
- 不做云同步。
- 不默认从 UI 直接执行 `claude --resume`，第一版只复制命令，避免后台进程和终端控制复杂度。

### 真正好用版

真正好用版在最小可用版上增加：

- session 结构化摘要。
- 自动提取计划、TODO、决策、风险、未完成问题。
- 本地或可配置 embedding 的语义搜索。
- 搜索结果解释“为什么匹配”。
- 手动标签、收藏、重命名、归档。
- “未完成计划”视图。
- 项目级记忆沉淀。
- 可选 wrapper：启动 Claude Code 时自动记录 cwd、git branch、commit、session 名称。
- 可选从 UI 发起 resume/fork，并把命令交给明确配置的终端或脚本执行。

## 设计原则

- 本机优先：默认所有数据留在本机。
- 只读原始会话：扫描器不能修改 Claude Code 的 transcript。
- 原始数据与解析结果分离：内部格式变化时，可以重建索引。
- 容错优先：遇到无法解析的行，记录 warning，继续扫描。
- 先全文检索，再语义增强：不要第一版就被 embedding 和摘要拖慢。
- 搜索结果要可解释：用户必须看到匹配片段和来源 session。
- 恢复动作交给 Claude Code 官方 CLI：MVP 只生成并复制 `claude --resume <id/name>`。

## 推荐技术栈

最小可用版建议采用“Python 后端 + 本机 Web UI”：

- Python 3.11+
- FastAPI
- Uvicorn
- `sqlite3`
- SQLite FTS5
- `typer` 或 `argparse`，用于 `scan`、`doctor`、`serve`
- React + Vite + TypeScript
- TanStack Query 或轻量 fetch wrapper
- `pytest` 用于后端测试
- Playwright 用于 UI smoke test

原因：

- Python 读写 JSONL、SQLite、文件扫描足够直接。
- FastAPI 能快速提供本机 API，后续也方便接入摘要和语义搜索。
- Web UI 比 CLI 更适合浏览、筛选、预览、复制 resume 命令。
- MVP 仍然只在本机运行，不需要账号、云服务或远程数据库。

## 目录结构建议

如果新建独立工具仓库，建议结构如下：

```text
cc-session-manager/
  README.md
  pyproject.toml
  ccm/
    __init__.py
    api.py
    cli.py
    config.py
    scanner.py
    parser.py
    index.py
    search.py
    models.py
    services.py
  web/
    package.json
    index.html
    src/
      main.tsx
      App.tsx
      api.ts
      components/
        SearchBar.tsx
        SessionList.tsx
        SessionDetail.tsx
        ProjectFilter.tsx
        ResumeCommand.tsx
  tests/
    fixtures/
      sample_session.jsonl
      malformed_session.jsonl
    test_parser.py
    test_index.py
    test_search.py
    test_api.py
  e2e/
    session-search.spec.ts
  docs/
    mvp_acceptance.md
```

如果临时放在现有仓库，建议放入：

```text
Tools/ClaudeSessionManager/
```

但长期更建议独立仓库，因为它不是当前 Unity 项目的业务代码。

## 数据模型

### sessions

```text
id                text primary key
name              text nullable
project_path      text nullable
transcript_path   text not null
created_at        text nullable
updated_at        text nullable
first_user_text   text nullable
message_count     integer not null default 0
scan_status       text not null
scan_error        text nullable
raw_metadata      text nullable
```

### messages

```text
id                integer primary key autoincrement
session_id        text not null
ordinal           integer not null
role              text not null
timestamp         text nullable
uuid              text nullable
parent_uuid       text nullable
text              text not null
raw_json          text nullable
```

### chunks

```text
id                integer primary key autoincrement
session_id        text not null
message_id        integer nullable
chunk_index       integer not null
text              text not null
```

### chunks_fts

SQLite FTS5 虚表：

```text
text
session_id
message_id
chunk_id
```

最小可用版可以只对 message text 建 chunk。chunk 长度建议 800 到 1600 字符，带少量 overlap。

## 解析规则

解析器需要对 Claude Code transcript 的 JSONL 做宽松处理：

- 每一行独立解析。
- JSON 解析失败时记录 warning，不中断整个文件。
- `type=user` 时提取用户文本。
- `type=assistant` 时提取 assistant 文本。
- `message.content` 可能是字符串，也可能是 block 数组。
- block 数组里只提取 `type=text` 的内容。
- tool result 可以先忽略，或作为普通文本记录。
- 未知字段保存在 `raw_json`，以后升级用。

session id 的来源优先级：

1. metadata 文件里的 id。
2. JSONL 行里的 session id。
3. transcript 文件名去掉扩展名。

project path 的来源优先级：

1. metadata 文件。
2. transcript 所在项目目录映射。
3. 扫描时用户提供的 `--project-path`。
4. unknown。

## 后端 API 与 CLI 设计

Web UI 是最小可用版的主要交互入口。CLI 只承担启动、扫描和排障职责。

### HTTP API

后端只监听本机地址，默认：

```text
http://127.0.0.1:8765
```

必须提供：

```text
GET  /api/health
POST /api/scan
GET  /api/sessions
GET  /api/sessions/{session_id}
GET  /api/search?q=<keyword>&project=<optional>&limit=20
GET  /api/projects
```

API 返回 JSON，核心字段：

```text
session_id
name
project_path
transcript_path
created_at
updated_at
first_user_text
message_count
snippet
resume_command
```

`POST /api/scan` 支持 body：

```json
{
  "roots": ["~/.claude/projects"],
  "rebuild": false
}
```

第一版不提供“执行 resume”接口，只返回 `resume_command`。

## Web UI 设计

### 页面布局

最小可用版只有一个主页面，三栏或两栏响应式布局：

```text
顶部工具栏：搜索框、项目筛选、扫描按钮、状态提示
左侧/主列表：session 搜索结果
右侧/详情区：session 元数据、匹配片段、消息预览、resume 命令
```

### 必须交互

- 初次打开时显示索引状态：未扫描、已扫描 session 数、最后扫描时间。
- 用户点击“扫描”后触发后端 scan，并显示进行中/成功/失败状态。
- 用户输入关键词后搜索 session。
- 用户可以按项目路径筛选。
- 用户点击搜索结果后打开详情。
- 详情区显示 transcript path、时间、首条 prompt、message count、匹配片段。
- 详情区提供复制 `claude --resume <session>` 的按钮。
- 空结果、扫描失败、数据库为空都要有明确 UI 状态。

### UI 不做

- 不做登录。
- 不做云同步。
- 不直接编辑 transcript。
- 不自动执行 `claude --resume`。
- 不做复杂仪表盘。
- 不做 landing page。

## CLI 设计

### doctor

检查环境和默认目录：

```bash
ccm doctor
```

输出：

- Python 版本。
- SQLite FTS5 是否可用。
- 默认 Claude Code session 目录是否存在。
- 当前索引数据库路径。

### scan

扫描历史 session：

```bash
ccm scan
ccm scan --root ~/.claude/projects
ccm scan --root ~/.config/claude/projects
ccm scan --rebuild
```

要求：

- 默认扫描常见位置。
- 支持多个 `--root`。
- 重复扫描要幂等。
- transcript 文件变更后更新索引。

### serve

启动本机 Web UI：

```bash
ccm serve
ccm serve --host 127.0.0.1 --port 8765
```

要求：

- 启动 FastAPI 后端。
- 在开发模式下可提示前端地址。
- 生产/打包模式下可由后端托管静态 UI。

### search/show

`search` 和 `show` 可以保留为调试命令，但不是最小可用版体验验收的主入口。真正面向用户的搜索和详情浏览必须在 Web UI 中完成。

## 最小可用版验收标准

验收时准备至少 3 类测试数据：

- 正常 JSONL session。
- 含坏行的 JSONL session。
- 多项目、多 session 数据。

必须通过：

- `ccm doctor` 能确认 FTS5 可用。
- `ccm scan --root tests/fixtures` 能成功导入样例。
- 同一个目录重复 scan 不产生重复 message。
- 坏行不会导致扫描失败。
- `ccm serve` 能启动本机后端和 UI。
- 打开 Web UI 后能看到 session 总数、项目筛选和搜索框。
- 在 UI 搜索 `<样例关键词>` 能返回正确 session。
- UI 搜索结果包含匹配片段。
- UI 详情页包含 transcript path、首条 prompt、message count。
- UI 详情页包含 `claude --resume <session>`，并提供复制按钮。
- Playwright smoke test 能打开页面、搜索 fixture keyword、进入详情。

手工体验验收：

- 启动 `ccm serve`，在浏览器打开本机 UI。
- 点击扫描真实 Claude Code 历史。
- 用一个自己模糊记得的关键词搜索。
- 能在 10 秒内从 UI 定位候选 session。
- 能复制 resume 命令，并在终端回到目标 session。

## 零人工介入的 session 编排方案

这里的“零人工介入”指：主控 session 读取本文档后，自动拆分任务，启动多个 worker session，在独立分支或 worktree 中实现最小可用版，并最后集成。

### 推荐执行模型

使用一个主控 session：

- 负责建立工具仓库或目录。
- 负责生成任务文件。
- 负责启动 worker session。
- 负责合并结果。
- 负责跑测试和验收。

使用 5 个 worker session：

- Worker A：项目骨架、后端 API 与 CLI。
- Worker B：scanner/parser。
- Worker C：SQLite/FTS index/search。
- Worker D：Web UI。
- Worker E：测试、fixtures、README、验收文档。

每个 worker 必须拥有互不重叠的主要写入范围，减少冲突。

### Worker A 任务

写入范围：

```text
pyproject.toml
ccm/__init__.py
ccm/api.py
ccm/cli.py
ccm/config.py
ccm/services.py
```

职责：

- 建立 Python 包。
- 实现 FastAPI 应用入口。
- 实现 CLI 命令入口：`doctor`、`scan`、`serve`。
- 定义 API：health、scan、sessions、session detail、search、projects。
- 不实现底层扫描和索引细节，只调用模块接口。
- 为 Web UI 提供稳定 JSON response shape。

交付标准：

- `python -m ccm.cli --help` 可运行。
- `ccm doctor` 可运行。
- `ccm serve` 可启动本机服务。
- `GET /api/health` 可返回成功。
- API 能调用空实现或 mock 实现，不报 import error。

### Worker B 任务

写入范围：

```text
ccm/scanner.py
ccm/parser.py
ccm/models.py
```

职责：

- 实现 transcript 文件发现。
- 实现 JSONL 容错解析。
- 提取 session id、timestamp、role、text、uuid、parent uuid。
- 兼容 `message.content` 为字符串或 block 数组。
- 返回结构化 Python dataclass 或 typed dict。

交付标准：

- 能解析正常 fixture。
- 能跳过 malformed JSONL 行。
- 不访问数据库。
- 不依赖 CLI。

### Worker C 任务

写入范围：

```text
ccm/index.py
ccm/search.py
```

职责：

- 创建 SQLite schema。
- 创建 FTS5 虚表。
- 实现 upsert session。
- 实现 replace messages/chunks。
- 实现关键词搜索。
- 实现按 project、limit 过滤。

交付标准：

- 重复导入同一个 session 不重复。
- FTS 搜索能返回 session、chunk、snippet。
- SQLite 数据库路径可配置。

### Worker D 任务

写入范围：

```text
web/
```

职责：

- 建立 React + Vite + TypeScript 前端。
- 实现主页面布局：顶部工具栏、结果列表、详情区。
- 实现 API client。
- 实现扫描按钮、搜索框、项目筛选、session 详情、resume 命令复制。
- 实现 loading、empty、error 状态。
- 使用 mock API 或清晰接口假设，等待 Worker A 集成。

交付标准：

- `npm install` 后 `npm run dev` 可启动。
- 页面无 landing page，打开就是 session 管理器。
- 使用 mock 数据时可以完成搜索、选中详情、复制命令的交互。

### Worker E 任务

写入范围：

```text
tests/
e2e/
README.md
docs/mvp_acceptance.md
```

职责：

- 创建 fixture JSONL。
- 写 parser/index/search/API 测试。
- 写 Playwright UI smoke test。
- 写最小 README。
- 写验收步骤。

交付标准：

- `pytest` 覆盖 parser、scan/index/search/API 主路径。
- Playwright 覆盖打开 UI、搜索、进入详情、看到 resume 命令。
- README 说明安装、扫描、启动 UI、搜索、恢复。
- 验收文档包含真实历史验证步骤。

### 主控 session 集成步骤

主控 session 按以下顺序执行：

1. 创建独立工具目录或仓库。
2. 写入本文档摘要和 worker task 文件。
3. 为每个 worker 创建独立 worktree 或分支。
4. 启动 5 个 worker session。
5. 等待 worker 完成。
6. 合并 Worker A 和 B。
7. 合并 Worker C。
8. 合并 Worker D。
9. 合并 Worker E。
10. 解决冲突。
11. 运行 `pytest`。
12. 运行 `python -m ccm.cli doctor`。
13. 运行 `python -m ccm.cli scan --root tests/fixtures --rebuild`。
14. 运行 `python -m ccm.cli serve`。
15. 运行前端 smoke test。
16. 生成验收报告。

### 可直接使用的 worker prompt 模板

#### Worker A Prompt

```text
你负责实现 Claude Code Session Manager UI-first 最小可用版的项目骨架、后端 API 和 CLI。

只写这些文件：
- pyproject.toml
- ccm/__init__.py
- ccm/api.py
- ccm/cli.py
- ccm/config.py
- ccm/services.py

不要修改其他 worker 的文件。你不是独自在代码库中工作，请兼容其他 session 的改动，不要回滚他人的文件。

目标：
- 建立 Python 3.11+ 包。
- 提供 FastAPI 应用。
- 提供 API：GET /api/health、POST /api/scan、GET /api/sessions、GET /api/sessions/{session_id}、GET /api/search、GET /api/projects。
- 提供 CLI：doctor、scan、serve。
- CLI 和 API 调用 scanner/parser/index/search 的公共接口。
- 如果底层模块暂时不存在，使用清晰的接口假设或临时 stub，并让后续集成容易。
- API response 必须包含 Web UI 需要的 session_id、project_path、transcript_path、first_user_text、message_count、snippet、resume_command。

完成后运行：
- python -m ccm.cli --help
- python -m ccm.cli doctor
- python -m ccm.cli serve
- curl http://127.0.0.1:8765/api/health

最终回复列出改动文件、接口假设、运行结果。
```

#### Worker B Prompt

```text
你负责实现 Claude Code Session Manager 最小可用版的 scanner/parser/models。

只写这些文件：
- ccm/scanner.py
- ccm/parser.py
- ccm/models.py

不要修改其他 worker 的文件。你不是独自在代码库中工作，请兼容其他 session 的改动，不要回滚他人的文件。

目标：
- 发现 Claude Code transcript JSONL 文件。
- 容错解析 JSONL。
- 提取 session id、project path、transcript path、timestamp、role、text、uuid、parent uuid。
- 支持 message.content 为字符串或 block 数组。
- 坏行记录 warning，不能中断整个 session。

不要访问数据库，不要实现 CLI。

完成后尽量用简单临时命令验证 parser。
最终回复列出改动文件、公共接口、边界处理。
```

#### Worker C Prompt

```text
你负责实现 Claude Code Session Manager 最小可用版的 SQLite index/search。

只写这些文件：
- ccm/index.py
- ccm/search.py

不要修改其他 worker 的文件。你不是独自在代码库中工作，请兼容其他 session 的改动，不要回滚他人的文件。

目标：
- 创建 SQLite schema：sessions、messages、chunks。
- 创建 SQLite FTS5 虚表。
- 实现 init_db、index_session、search。
- 重复导入同一个 session 必须幂等。
- 支持 limit 和 project 过滤。
- 搜索结果包含 session id、project、transcript path、snippet、resume command。

不要实现 CLI，不要实现 parser。

完成后用内存或临时 SQLite 文件做最小验证。
最终回复列出改动文件、公共接口、运行结果。
```

#### Worker D Prompt

```text
你负责 Claude Code Session Manager UI-first 最小可用版的 Web UI。

只写这个路径：
- web/

不要修改其他 worker 的文件。你不是独自在代码库中工作，请兼容其他 session 的改动，不要回滚他人的文件。

目标：
- 建立 React + Vite + TypeScript 前端。
- 打开后直接进入 session 管理器，不做 landing page。
- 实现顶部工具栏：搜索框、项目筛选、扫描按钮、索引状态。
- 实现 session 结果列表：时间、项目、首条 prompt、匹配片段。
- 实现 session 详情：transcript path、时间、message count、首条 prompt、匹配片段、resume command。
- 实现复制 resume command。
- 实现 loading、empty、error 状态。
- 在后端未完成时使用 mock API，但 api.ts 的接口必须和 Worker A 的 API 设计一致。

完成后运行：
- npm install
- npm run dev

最终回复列出改动文件、UI 状态、API 假设、运行结果。
```

#### Worker E Prompt

```text
你负责 Claude Code Session Manager UI-first 最小可用版的 tests、fixtures、README 和验收文档。

只写这些路径：
- tests/
- e2e/
- README.md
- docs/mvp_acceptance.md

不要修改其他 worker 的文件。你不是独自在代码库中工作，请兼容其他 session 的改动，不要回滚他人的文件。

目标：
- 创建正常 JSONL fixture。
- 创建含 malformed line 的 JSONL fixture。
- 创建多 session fixture。
- 写 pytest 覆盖 parser、index、search、API 的关键行为。
- 写 Playwright smoke test：打开 UI、搜索 fixture keyword、进入详情、看到 resume command。
- README 说明安装、scan、serve、UI 搜索、复制 resume command。
- 验收文档说明如何用真实 Claude Code 历史验证。

完成后运行 pytest；如果前后端模块尚未完成，说明期望接口和阻塞项。
最终回复列出改动文件、测试覆盖点、阻塞项。
```

## 真正好用版路线

在最小可用版通过真实体验验证后，按以下顺序升级。

### V1：结构化摘要

新增表：

```text
session_summaries
  session_id
  title
  main_goal
  key_decisions
  plans
  todo_items
  risks
  open_questions
  files_discussed
  commands_run
  generated_at
  model
```

能力：

- 对每个 session 生成结构化摘要。
- 摘要必须保存证据 message id。
- 支持在 UI 中生成/查看 session 摘要。
- 可选保留 CLI 调试命令：`ccm summarize <session>`、`ccm search --summary "支付重构"`。

### V2：语义搜索

新增：

- embedding provider 抽象。
- 默认本地 embedding，或可配置远程 embedding。
- vector index，可选 sqlite-vec / LanceDB。

能力：

- 用户输入模糊描述，返回相关 session。
- 结果同时展示语义命中原因和证据片段。
- 支持全文 + 语义混合排序。

### V3：工作记忆视图

新增命令：

```bash
ccm plans
ccm todos
ccm decisions
ccm open-loops
```

能力：

- 跨 session 查看未完成计划。
- 按项目聚合历史决策。
- 将长期稳定记忆导出为项目 CLAUDE.md 候选内容。

### V4：高级交互

Web UI 已经是 MVP 的主入口，V4 不再是“是否做 UI”，而是增强交互深度。

增强视图：

- session 时间线
- 项目维度聚合
- 摘要/计划/决策分栏
- 未完成事项看板
- transcript 全文预览
- resume/fork action
- 可选 TUI，服务于纯终端工作流

## 风险和防护

### Claude Code 内部格式变化

防护：

- 原始 transcript 不修改。
- JSONL parser 宽松处理。
- 数据库可 rebuild。
- 未知字段保留 raw JSON。

### 隐私风险

防护：

- 默认本地存储。
- 不默认调用远程 LLM。
- README 明确 transcript 可能包含代码、路径、密钥。
- 后续版本增加敏感信息检测和索引排除规则。

### 搜索结果不准

防护：

- MVP 先保证全文搜索可靠。
- 真正好用版引入摘要和语义搜索。
- 所有自动摘要都保留证据片段。

### 多 session 并行开发冲突

防护：

- worker 写入范围固定。
- 主控 session 集成。
- 每个 worker 最终必须列出改动文件。

## 推荐下一步

1. 新建独立仓库 `cc-session-manager`。
2. 把本文档复制为 `docs/plan.md`。
3. 主控 session 根据“零人工介入的 session 编排方案”创建 worker task 文件。
4. 启动 5 个 worker session 完成 UI-first 最小可用版。
5. 用真实 Claude Code 历史验证 UI 搜索和详情预览体验。
6. 通过后进入“真正好用版”的 V1 结构化摘要。
