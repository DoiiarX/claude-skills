---
name: local-issue
description: >
  本地文件系统 issue 管理。Use when the user wants to create, list, view,
  close, or query issues in the local file-based issue system, or wants to
  see issue-related git commit history.
  Triggers on: local issue, 本地issue, 创建issue, 新建issue, bug report,
  feature request, 关闭issue, 创建任务, list issues, 列出issue, issue列表,
  查看issue, issue状态, issue status, issue log, issue history,
  show issues, open issues, closed issues, issue summary.
allowed-tools: Bash
---

# Local Issue Skill

> Everything is a file.

Issue 即 Markdown 文件，存于版本控制之中。无服务、无网络、无 API——每一条 issue 都是可被 `grep`、`cat`、`git log` 直接操作的纯文本。这让 agent 能像处理代码一样处理任务上下文：跨 issue 全文搜索、批量提取状态、在同一次 commit 中同时更新代码与 issue 进展，一切工具链天然适配。

更深层的意义在于：每个独立的 issue 文件本质上是一个**事件（event）**。项目由此从线性的任务列表，演变为事件驱动的结构——多个 agent 可以各自认领不同的 issue 并行推进，CI/CD 流水线可以监听 issue 状态变更并自动触发，代码与任务的边界在 git 历史中完全透明。这或许正是 AI 原生开发的新范式：不是 AI 辅助人类写代码，而是以 issue 为协议，人与 agent 协同驱动一个持续演进的系统。

## CLI 工具

本 skill 提供统一的 `local-issue` CLI 工具，设计遵循 agent-friendly 原则：

- **非交互式优先**：所有输入通过参数传递，无需交互式菜单
- **管道友好**：支持 `--quiet` 模式输出机器可读格式
- **分层帮助**：每个子命令有独立的 `--help` 和示例
- **明确的错误信息**：失败时提供可操作的提示
- **幂等性**：重复执行相同命令是安全的

**安装**：

```bash
# 将 CLI 工具链接到系统路径
ln -s ~/.claude/skills/local-issue/local-issue ~/.local/bin/local-issue
# 或直接使用完整路径
alias local-issue='python3 ~/.claude/skills/local-issue/local-issue'
```

**可用命令**：

- `local-issue create` - 从模板创建新 issue
- `local-issue close` - 关闭 issue 并移动到 `closed/`
- `local-issue progress` - 追加进展记录
- `local-issue next` - 预留下一个可用的 issue 编号
- `local-issue list` - 列出 issues
- `local-issue status` - 显示详细状态汇总
- `local-issue log` - 显示 issue 相关的 git commit 历史

每个命令都支持 `--help` 查看详细用法和示例。

## Issue 系统位置

```
.issues/
├── open/        # 待处理 issue（文件名格式：NNN-type-description.md）
├── closed/      # 已完成 issue
└── templates/   # 模板（bug.md / feature.md / refactor.md）
```

## 执行步骤

### 1. 确定下一个 Issue 编号并创建占位文件

使用 `local-issue next` 命令，默认行为会创建占位文件以避免序号竞争。

**基本用法**：

```bash
local-issue next
```

输出示例：
```
047
placeholder_path=.issues/open/047-placeholder.md
# Next: Rename to 047-{type}-{description}.md
```

**在指定项目中使用**：

```bash
local-issue next /path/to/project/.issues
```

**可用选项**：

| 选项 | 说明 | 使用场景 |
|------|------|----------|
| `--query-only` | 仅查询下一个编号，不创建占位文件 | 统计、预览 |
| `--dry-run` | 预览将创建的占位文件，但不实际创建 | 测试、验证 |
| `--quiet` / `-q` | 仅输出编号（机器可读模式） | 管道、脚本集成 |

**管道友好的用法**：

```bash
# 在脚本中使用
ISSUE_ID=$(local-issue next --quiet)
mv .issues/open/$ISSUE_ID-placeholder.md .issues/open/$ISSUE_ID-bug-fix.md

# 提取占位文件路径
OUTPUT=$(local-issue next)
ISSUE_ID=$(echo "$OUTPUT" | head -1)
PLACEHOLDER=$(echo "$OUTPUT" | grep "placeholder_path=" | cut -d= -f2)
```

**错误处理**：

如果占位文件已存在（序号竞争），命令会报错并提示重新运行：
```
Error: Placeholder already exists: .issues/open/047-placeholder.md
Hint: Run 'local-issue next' again to get the next available ID.
```

### 2. 选择 Issue 类型

根据用户描述选择类型标签：

| 类型 | 标签 | 文件头 | 使用场景 |
|------|------|--------|----------|
| `bug` | bug | `[Bug]` | 功能异常、错误行为 |
| `feature` | feature | `[Feature]` | 新功能需求 |
| `refactor` | refactor | `[Refactor]` | 代码重构、技术债务 |

### 3. 选择模板

**优先使用项目自带模板**：

```bash
# 检查项目是否有对应模板
ls .issues/templates/
```

- 若存在 `.issues/templates/{type}.md` → 以该文件为模板
- 若不存在 → 使用 skill 内置模板（见 `templates/` 目录）

## 推荐创建方式：`create`

`create` 会自动完成编号分配、文件命名、模板选择和常见占位符替换，是创建 issue 的首选方式。

```bash
local-issue create bug "PDF 连续模式缩放错位"
local-issue create feature "支持视频 mov/mkv 转码" --priority High
local-issue create refactor "拆分 AnnotationCanvas" --assignee claude
local-issue create bug "渲染回归" --label pdf --label regression
```

行为：
- 自动选择下一个编号
- 文件名格式：`.issues/open/{NNN}-{type}-{title}.md`
- 优先使用项目模板 `.issues/templates/{type}.md`，否则使用 skill 内置模板
- 自动替换 `#XXX`、`YYYY-MM-DD`、`Issue Title`、`{简短标题}`
- 自动维护 `Status`、`Priority`、`Type`、`Created`、`Updated`、`Assignee`、`Labels` 等常见元信息

输出示例：

```text
Created .issues/open/047-bug-PDF连续模式缩放错位.md
```

## 手动创建流程

以下 `next` + `mv` 流程保留给需要精确控制文件名或模板内容的场景。

### 4. 重命名占位文件并填充内容

由于步骤 1 已经创建了占位文件（如 `.issues/open/047-placeholder.md`），现在需要：

**4.1 确定最终文件名**

文件名格式：`.issues/open/{NNN}-{type}-{short-description}.md`

- `{NNN}` = 三位数字编号，不足补零（已由脚本生成）
- `{type}` = 类型标签（小写）
- `{short-description}` = 简短描述（用连字符，英文或中文均可）

示例：`047-bug-websocket-timeout.md`、`048-feature-历史推文拉取.md`

**4.2 重命名占位文件**

```bash
mv .issues/open/047-placeholder.md .issues/open/047-bug-websocket-timeout.md
```

**4.3 填充 Issue 内容**

将模板内容写入重命名后的文件，填写以下占位字段：
- `#XXX` → 实际编号
- `YYYY-MM-DD` → 今日日期
- 标题、描述、相关章节内容

**注意**：如果在重命名前发现占位文件已不存在，说明发生了序号竞争。此时应重新运行步骤 1 获取新的序号。

### 5. 提交 Issue 文件到 Git

**首先检查项目的 commit 规范**，优先级从高到低：

1. `CLAUDE.md` / `AGENTS.md` — AI agent 专属规范
2. `CONTRIBUTING.md` — 项目贡献规范
3. `git log --oneline` — 从历史提交归纳风格

在没有任何规范的情况下，才使用以下格式作为兜底：

```bash
git add .issues/open/{filename}.md
git commit -m "docs: add issue #{NNN} - {简短描述}"
```

### 6. 开始处理

创建 issue 后立即着手解决：
- 分析问题根源
- 制定实现计划
- 更新 issue 中的"进展记录"
- 实现时在代码注释中引用：`// Fix: #{NNN}`

## 更新进展

使用 `progress` 为指定 issue 追加进展记录，并同步更新 `Updated` 日期：

```bash
local-issue progress 047 "完成根因定位：canvasZoom 被重复应用"
```

如果 issue 中已有当天的 `### YYYY-MM-DD` 小节，会直接追加 bullet；否则会在 `## 进展记录` 下创建当天小节。

## 关闭 Issue

推荐使用 `close` 关闭 issue：

```bash
local-issue close 047
local-issue close 047 --summary "修复 canvasZoom 重复换算"
```

行为：
1. 查找 `.issues/open/047-*.md`
2. 更新：
   - `Status: Closed ✅`
   - `Updated: {YYYY-MM-DD}`
   - `Closed: {YYYY-MM-DD}`
3. 如传入 `--summary`，追加 `## 解决总结`
4. 移动到 `.issues/closed/`

## 参考文档记录规范

当 issue 涉及第三方库、框架、API 或版本特定行为时，应在 issue 中记录参考来源，避免只凭记忆实现。

### Context7 特例

如果项目安装了 `/context7` skill，且 issue 涉及第三方库 API，应优先使用 Context7 查询官方文档。

推荐流程：

1. 搜索库 ID：

   ```bash
   scripts/context7.sh search "library-name"
   ```

2. 查询相关主题：

   ```bash
   scripts/context7.sh docs "/library-id" "topic" "code"
   ```

3. 在 issue 的 `参考资料` 或 `技术方案` 中记录：

   ```md
   ## 参考资料

   - Context7: `/library-id` — topic: `xxx`
   - 结论：……
   ```

适用场景：
- 新增或修改第三方库调用
- 不确定 API 参数、返回值、生命周期、版本差异
- 需要示例代码辅助实现
- 依赖升级或替换

## 查询命令

### `list` — 列出 Issues

按 **type 分组**，组内按 **Priority 降序**（High 在前）。

**语法**

```bash
local-issue list [issues-dir] [--state open|closed|all] [--type bug|feature|refactor] [--priority high|medium|low] [--limit N] [--quiet]
```

**默认行为**：`--state open`，不限 type / priority，`--limit 30`

**示例**

```bash
# 列出所有 open issues（默认）
local-issue list

# 列出所有状态的 issues
local-issue list --state all

# 只列出 bug 类型的 issues
local-issue list --type bug

# 只列出高优先级的 issues
local-issue list --priority high

# 限制显示数量
local-issue list --limit 10

# 机器可读模式（仅输出 ID）
local-issue list --quiet

# 在指定项目中使用
local-issue list /path/to/project/.issues
```

**输出格式**

```
Open Issues (26)

[bug] 12
  #034  High      websocket-reconnect-on-reset-without-closing-handshake
  #075  High      decay-sell-missing-reverse-constraint
  #040  -         tweet_storage_plugin-chartjs-cdn-url-不存在

[feature] 10
  #064  High      polymarket-order-entry-plugin
  #051  Medium    纸面交易页面显示当前选项价格挂单数量
  #031  -         迁移-liquidity-rewards-plugin

[refactor] 4
  #055  -         统一polymarket-ws服务注册
```

`-` 表示 Priority 字段缺失或为 Unassigned。

**机器可读输出** (`--quiet`)：

```
034
075
040
064
051
031
055
```

---

### `status` — 详细状态汇总

显示 issue 系统的整体状态，包括统计、分布和最近活动。

**语法**

```bash
local-issue status [issues-dir]
```

**示例**

```bash
# 显示当前项目的状态
local-issue status

# 显示指定项目的状态
local-issue status /path/to/project/.issues
```

**输出格式**

```
─────────────────────────────────────────────
Issue Status                  2026-04-12
─────────────────────────────────────────────
Open: 26    Closed: 95    Total: 121

By Type (open)
  bug          12  ████████████░░░░░░░░  46%
  feature      10  ██████████░░░░░░░░░░  38%
  refactor      4  ████░░░░░░░░░░░░░░░░  15%

By Priority (open)
  High          8  ████████░░░░░░░░░░░░  31%
  Medium       12  ████████████░░░░░░░░  46%
  Low           0  ░░░░░░░░░░░░░░░░░░░░   0%
  (unset)       6  ██████░░░░░░░░░░░░░░  23%

Recently Updated (open)
  #117  feature   持仓空缺自动诊断 POC                        2026-04-12
  #114  bug       实盘下单三类精度与金额校验                   2026-04-11
  #116  bug       SELL size 超出实际持仓                      2026-04-10
  #091  bug       current-count-shows-2                      2026-04-09
  #082  bug       rest-price-fallback-not-applied            2026-04-08

Recent Issue Commits
  30a940a  #114  docs: close issue #114 - 实盘下单三类精度
  eb422a7  #116  docs: close issue #116 - SELL size 超出实际持仓
  389109f  #116  fix: #116 - SELL size 截断到 1 位小数
  8da1b3d  #116  docs: add issue #116 - 实盘下单 SELL size 超出
  c2d62cb  #117  feat: logger_factory auto_issue watcher POC
─────────────────────────────────────────────
```

---

### `log` — Issue 关联的 Git Commit 历史

查询哪些 commit 引用了 issue。

**语法**

```bash
local-issue log [issue-id] [issues-dir] [--limit N] [--quiet]
```

**示例**

```bash
# 列出最近所有引用任意 issue 编号的 commits
local-issue log

# 查询特定 issue 的 commit 历史
local-issue log 064

# 限制显示数量
local-issue log --limit 10

# 机器可读模式（仅输出 commit hash）
local-issue log --quiet
local-issue log 064 --quiet

# 在指定项目中使用
local-issue log 064 /path/to/project/.issues
```

**输出（无参数）**

```
Recent issue-related commits (20)
  30a940a  #114    docs: close issue #114 - 实盘下单三类精度
  eb422a7  #116    docs: close issue #116 - SELL size 超出实际持仓
  389109f  #116    fix: #116 - SELL size 截断到 1 位小数
  8da1b3d  #116    docs: add issue #116 - 实盘下单 SELL size 超出
  ...
```

**输出（带 issue 编号）**

```
Commits referencing #064 (3)
  abc1234  2026-02-20  feat: #064 - add order entry plugin base structure
  def5678  2026-02-21  feat: #064 - implement order form UI
  ghi9012  2026-02-22  docs: close issue #064

── Issue ──────────────────────────────
  File:    .issues/closed/064-feature-polymarket-order-entry-plugin.md
  Status:  Closed ✅
  Created: 2026-02-19
```

**机器可读输出** (`--quiet`)：

```
abc1234
def5678
ghi9012
```

---

## Git Commit 引用规范

以下为通用参考，**项目自有规范优先**：

- Issue 创建：`docs: add issue #{NNN} - {描述}`
- 功能提交：`feat: #{NNN} - {描述}` 或 `fix: #{NNN} - {描述}`
- 关闭 Issue：在 commit body 中写 `Closes #{NNN}`

## 示例

用户输入：`/local-issue 记录 WebSocket 断线重连的 bug`

执行（推荐）：
1. 运行 `local-issue create bug "WebSocket 断线重连"`
2. 根据输出文件补充问题细节
3. `git add .issues/open/047-bug-WebSocket断线重连.md`
4. `git commit -m "docs: add issue #047 - WebSocket断线重连bug"`
5. 开始分析代码，在进展记录中更新状态

手动流程：
1. 运行 `local-issue next`
   - 扫描得最大编号为 046，新建 047
   - 创建占位文件 `.issues/open/047-placeholder.md`
   - 输出：`047` 和 `placeholder_path=.issues/open/047-placeholder.md`
2. 类型：bug
3. 检查 `.issues/templates/bug.md` → 存在，使用项目模板
4. 重命名占位文件：`mv .issues/open/047-placeholder.md .issues/open/047-bug-websocket-reconnect.md`
5. 填写模板内容，描述断线重连问题
6. `git add .issues/open/047-bug-websocket-reconnect.md`
7. `git commit -m "docs: add issue #047 - WebSocket断线重连bug"`
8. 开始分析代码，在进展记录中更新状态

## 序号竞争说明

**问题场景**：多个 agent 或用户同时创建 issue 时，可能读取到相同的"下一个序号"，导致文件名冲突。

**解决方案**：
- 默认行为：`local-issue next` 在返回序号的同时创建占位文件（如 `047-placeholder.md`）
- 占位文件作为"锁"，确保该序号被当前操作独占
- 后续操作通过重命名占位文件完成 issue 创建
- 如果占位文件已存在，命令会报错退出，提示序号已被占用

**仅查询模式**：
- 使用 `--query-only` 参数可以只查询序号而不创建占位文件
- 适用于统计、预览等场景
- **不应在实际创建 issue 时使用此模式**

## CLI 工具快速参考

```bash
# 获取帮助
local-issue help
local-issue help next

# 创建新 issue（推荐）
local-issue create bug "PDF 连续模式缩放错位"
local-issue create feature "支持视频 mov/mkv 转码" --priority High

# 追加进展
local-issue progress 047 "完成根因定位"

# 关闭 issue
local-issue close 047 --summary "修复完成"

# 预留编号（手动流程）
local-issue next
local-issue next --quiet  # 仅输出编号

# 列出 issues
local-issue list
local-issue list --state all
local-issue list --type bug --priority high
local-issue list --quiet  # 仅输出 ID

# 查看状态汇总
local-issue status

# 查看 commit 历史
local-issue log
local-issue log 047
local-issue log --quiet  # 仅输出 commit hash
```
