---
name: local-issue
description: "本地文件系统 issue 管理。Use when the user wants to create, update, or close a local issue, report a bug, add a feature request, or track a task in the local file-based issue system. Triggers on: local issue, 本地issue, 创建issue, 新建issue, bug report, feature request, 关闭issue, 创建任务."
---

# Local Issue Skill

> Everything is a file.

Issue 即 Markdown 文件，存于版本控制之中。无服务、无网络、无 API——每一条 issue 都是可被 `grep`、`cat`、`git log` 直接操作的纯文本。这让 agent 能像处理代码一样处理任务上下文：跨 issue 全文搜索、批量提取状态、在同一次 commit 中同时更新代码与 issue 进展，一切工具链天然适配。

## Issue 系统位置

```
.issues/
├── open/        # 待处理 issue（文件名格式：NNN-type-description.md）
├── closed/      # 已完成 issue
└── templates/   # 模板（bug.md / feature.md / refactor.md）
```

## 执行步骤

### 1. 确定下一个 Issue 编号

```bash
# 合并 open 和 closed 目录，找最大编号
ls .issues/open/ .issues/closed/ 2>/dev/null \
  | grep -oE '^[0-9]+' | sort -n | tail -1
# 新编号 = 最大编号 + 1，补零到3位（如 047）
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

### 4. 创建 Issue 文件

文件名格式：`.issues/open/{NNN}-{type}-{short-description}.md`

- `{NNN}` = 三位数字编号，不足补零
- `{type}` = 类型标签（小写）
- `{short-description}` = 简短描述（用连字符，英文或中文均可）

示例：`047-bug-websocket-timeout.md`、`048-feature-历史推文拉取.md`

将模板内容复制后，填写以下占位字段：
- `#XXX` → 实际编号
- `YYYY-MM-DD` → 今日日期
- 标题、描述、相关章节内容

### 5. 提交 Issue 文件到 Git

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

## 关闭 Issue

完成后：

1. 在 issue 文件中更新：
   - `Status: Closed ✅`
   - `Updated: {YYYY-MM-DD}`
   - 新增 `Closed: {YYYY-MM-DD}` 字段
   - 补充进展记录和解决总结

2. 移动并提交：
```bash
mv .issues/open/{NNN}-*.md .issues/closed/
git add .issues/
git commit -m "docs: close issue #{NNN} - {描述}

Closes #{NNN}"
```

## Git Commit 引用规范

- Issue 创建：`docs: add issue #{NNN} - {描述}`
- 功能提交：`feat: #{NNN} - {描述}` 或 `fix: #{NNN} - {描述}`
- 关闭 Issue：在 commit body 中写 `Closes #{NNN}`

## 示例

用户输入：`/new-local-issue 记录 WebSocket 断线重连的 bug`

执行：
1. 扫描得最大编号为 046，新建 047
2. 类型：bug
3. 检查 `.issues/templates/bug.md` → 存在，使用项目模板
4. 文件：`.issues/open/047-bug-websocket-reconnect.md`
5. 填写模板内容，描述断线重连问题
6. `git commit -m "docs: add issue #047 - WebSocket断线重连bug"`
7. 开始分析代码，在进展记录中更新状态
