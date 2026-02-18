# claude-skills

A collection of Claude Code skills for extending agent capabilities.

## Skills

### [json-flat-tool](./json-flat-tool/)

A single-script tool (`jstool.py`) for viewing, inspecting, and editing JSON data.

**Features:**
- **Flat path/type/value view** — every field on one line: `users[0].name string Alice`
- **Schema mode** (`-s`) — collapses arrays, deduplicates, hides values
- **Depth limiting** (`-d N`) — collapse containers beyond N key levels, showing `{3 keys}` / `[12 items]` summaries
- **Path filtering** (`-F`) — show only a subtree
- **Pagination** — row-level (`-n`, `-O`) and element-aware (`-E`, `-L`)
- **Null type inference** — infers null field types from sibling values
- **JSON Schema Draft 7** — infer schema from any JSON file
- **Edit commands** — `set`, `before`, `after`, `del`, `set-null` with preview by default
- **Fuzzy command suggestions** — Levenshtein-based typo correction

**Install:**
```bash
npx skills add DoiiarX/claude-skills@json-flat-tool
```

**Quick start:**
```bash
# View structure
python3 ~/.claude/skills/json-flat-tool/jstool.py view data.json -s

# Filter to a nested array with element-aware pagination
python3 ~/.claude/skills/json-flat-tool/jstool.py view data.json -F "data[0].bids" -E 2 -L 5

# Infer JSON Schema
python3 ~/.claude/skills/json-flat-tool/jstool.py schema data.json --title "My API"

# Edit (preview only)
python3 ~/.claude/skills/json-flat-tool/jstool.py set users[0].name Bob data.json

# Edit (apply)
python3 ~/.claude/skills/json-flat-tool/jstool.py set users[0].name Bob data.json -f

# Depth-limited view (collapse beyond 2 key levels)
python3 ~/.claude/skills/json-flat-tool/jstool.py view data.json -d 2
```

---

### [local-issue](./local-issue/)

本地 issue 文件系统管理工具，用于创建和跟踪项目任务。

**Features:**
- **自动编号** — 扫描 open/closed 目录，自动分配下一个编号
- **多类型支持** — bug / feature / refactor / chore / docs
- **模板化内容** — 根据类型自动生成对应章节结构
- **Git 集成** — 自动提交 issue 文件，规范引用格式
- **即时处理** — 创建后立即开始分析和实现

**Install:**
```bash
npx skills add DoiiarX/claude-skills@local-issue
```

**Quick start:**
```
/new-local-issue 记录 WebSocket 断线重连 bug
/new-local-issue 添加历史推文拉取功能
/new-local-issue 重构 plugin manager 依赖解析
```

---

## Installation

Skills are installed via the [Skills CLI](https://skills.sh/):

```bash
npx skills add DoiiarX/claude-skills@<skill-name>
```

## Contributing

Skills live in their own subdirectory with a `SKILL.md` descriptor and implementation files.
