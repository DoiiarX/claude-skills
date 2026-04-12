# Changelog

## 改进内容 (2026-04-12)

### 主要变更

1. **统一 CLI 工具**
   - 创建了 `local-issue` 统一命令行工具，替代原来的单一 `next-issue-id.py` 脚本
   - 实现了完整的子命令系统：`next`, `list`, `status`, `log`, `help`
   - 所有功能现在通过一个入口点访问

2. **避免序号竞争**
   - `local-issue next` 默认创建占位文件（`NNN-placeholder.md`）
   - 占位文件作为"锁"机制，防止多个 agent 同时获取相同序号
   - 如果占位文件已存在，命令会报错并提示重新运行
   - 提供 `--query-only` 选项用于仅查询场景

3. **Agent-Friendly 设计**
   - 遵循 cli-for-agents 设计原则
   - 非交互式优先：所有输入通过参数传递
   - 管道友好：支持 `--quiet` 模式输出机器可读格式
   - 分层帮助：每个子命令有独立的 `--help` 和示例
   - 明确的错误信息：失败时提供可操作的提示
   - 结构化输出：`placeholder_path=...` 格式便于解析

4. **完整的命令实现**
   - `next`: 预留下一个可用的 issue 编号（带占位文件）
   - `list`: 列出 issues，支持按状态、类型、优先级过滤
   - `status`: 显示详细状态汇总，包括统计图表
   - `log`: 显示 issue 相关的 git commit 历史
   - `help`: 显示命令帮助信息

### 技术细节

**占位文件机制**：
```bash
# 默认行为（创建占位文件）
local-issue next
# 输出：
# 047
# placeholder_path=.issues/open/047-placeholder.md

# 仅查询（不创建占位文件）
local-issue next --query-only
# 输出：
# 047
```

**管道集成**：
```bash
# 在脚本中使用
ISSUE_ID=$(local-issue next --quiet)
mv .issues/open/$ISSUE_ID-placeholder.md .issues/open/$ISSUE_ID-bug-fix.md

# 过滤和查询
local-issue list --type bug --quiet | while read id; do
  echo "Processing issue #$id"
done
```

**错误处理**：
- 退出码 0：成功
- 退出码 1：错误（目录不存在、占位文件已存在等）
- 错误信息输出到 stderr，包含可操作的提示

### 移除的文件

- 删除了 `next-issue-id.py` 脚本，完全由 `local-issue next` 命令替代
- 统一使用 `local-issue` CLI 工具，避免维护多个入口点

### 安装

```bash
# 方式 1：创建符号链接
ln -s ~/.claude/skills/local-issue/local-issue ~/.local/bin/local-issue

# 方式 2：添加别名
echo "alias local-issue='python3 ~/.claude/skills/local-issue/local-issue'" >> ~/.bashrc

# 方式 3：直接使用完整路径
python3 ~/.claude/skills/local-issue/local-issue next
```

### 使用示例

```bash
# 创建新 issue
ISSUE_ID=$(local-issue next --quiet)
mv .issues/open/$ISSUE_ID-placeholder.md .issues/open/$ISSUE_ID-bug-websocket-timeout.md
# 编辑文件...
git add .issues/open/$ISSUE_ID-bug-websocket-timeout.md
git commit -m "docs: add issue #$ISSUE_ID - WebSocket timeout"

# 查看所有高优先级的 bug
local-issue list --type bug --priority high

# 查看项目状态
local-issue status

# 查看特定 issue 的 commit 历史
local-issue log 047
```

### 文件结构

```
local-issue/
├── local-issue              # 统一 CLI 工具
├── SKILL.md                 # 技能文档
├── CHANGELOG.md             # 变更日志
└── templates/
    ├── bug.md
    ├── feature.md
    └── refactor.md
```
