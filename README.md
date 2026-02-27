# claude-skills

A collection of Claude Code skills for extending agent capabilities.

## Skills

### [json-flat-tool](./json-flat-tool/)

A single-script tool (`jstool.py`) for viewing, inspecting, and editing JSON data.

**Auto-triggers on:**
- JSON files on disk — view, inspect, search
- JSON config files — `config.json`, `settings.json`, `package.json`, `tsconfig.json`, etc.
- Editing / modifying fields in any JSON file — set key, delete key, insert array element
- HTTP / REST API responses — curl output, Postman captures, fetch() results
- WebSocket (WSS) message payloads — frames captured from browser DevTools or a proxy
- Orderbook / market-data snapshots — CLOB, AMM, streaming events, RPC responses
- Inline JSON pasted directly into chat

**Features:**
- **Flat path/type/value view** — every field on one line: `users[0].name string Alice`
- **Schema mode** (`-s`) — collapses arrays, deduplicates, hides values
- **Depth limiting** (`-d N`) — collapse containers beyond N key levels, showing `{3 keys}` / `[12 items]` summaries
- **Path filtering** (`-F`) — show only a subtree
- **Pagination** — row-level (`-n`, `-O`) and element-aware (`-E`, `-L`)
- **Null type inference** — infers null field types from sibling values
- **JSON Schema Draft 7** — infer schema from any JSON file
- **Edit commands** — `set`, `before`, `after`, `del`, `set-null` with preview by default; B-style `path = value` syntax supported
- **`@file` value syntax** — pass a JSON file as the value: `set my.key @/tmp/val.json`
- **Copy / merge** — deep-clone a subtree (`copy`), deep-merge a patch file (`merge`)
- **Find** — search paths and values by regex or glob (`find -k/-v/-i/-g`)
- **Stdin / pipe support** — omit file argument to read from stdin
- **Fuzzy command suggestions** — Levenshtein-based typo correction

**Install:**
```bash
npx skills add DoiiarX/claude-skills@json-flat-tool
```

**Quick start:**
```bash
# View structure (schema mode)
python3 ~/.claude/skills/json-flat-tool/jstool.py view data.json -s

# Filter subtree with element-aware pagination
python3 ~/.claude/skills/json-flat-tool/jstool.py view data.json -F "data[0].bids" -E 2 -L 5

# Depth-limited view; combine with filter to expand one branch
python3 ~/.claude/skills/json-flat-tool/jstool.py view data.json -d 2
python3 ~/.claude/skills/json-flat-tool/jstool.py view data.json -d 1 -F users

# Row-level pagination
python3 ~/.claude/skills/json-flat-tool/jstool.py view data.json -n 50 -O 100

# Infer JSON Schema
python3 ~/.claude/skills/json-flat-tool/jstool.py schema data.json --title "My API"

# Edit: set (preview / apply / B-style)
python3 ~/.claude/skills/json-flat-tool/jstool.py set users[0].name Bob data.json
python3 ~/.claude/skills/json-flat-tool/jstool.py set users[0].name Bob data.json -f
python3 ~/.claude/skills/json-flat-tool/jstool.py "users[0].name" = Bob data.json -f

# Edit: insert / delete / set-null
python3 ~/.claude/skills/json-flat-tool/jstool.py before users[1] '{"name":"Eve"}' data.json -f
python3 ~/.claude/skills/json-flat-tool/jstool.py after  users[1] '{"name":"Eve"}' data.json -f
python3 ~/.claude/skills/json-flat-tool/jstool.py del users[2] data.json -f
python3 ~/.claude/skills/json-flat-tool/jstool.py set-null users[0].age data.json -f

# Set value from file (@file syntax)
python3 ~/.claude/skills/json-flat-tool/jstool.py set provider.openai @/tmp/openai.json config.json -f

# Clone a subtree to a new path
python3 ~/.claude/skills/json-flat-tool/jstool.py copy \
  provider.google.models.old-model \
  provider.google.models.new-model \
  config.json -f

# Deep-merge a patch file into a path
python3 ~/.claude/skills/json-flat-tool/jstool.py merge provider.models /tmp/patch.json config.json -f

# Find: regex (default), path-only, value-only, case-insensitive, glob
python3 ~/.claude/skills/json-flat-tool/jstool.py find apiKey config.json
python3 ~/.claude/skills/json-flat-tool/jstool.py find apiKey config.json -k
python3 ~/.claude/skills/json-flat-tool/jstool.py find "sk-.*" config.json -v
python3 ~/.claude/skills/json-flat-tool/jstool.py find "APIKEY" config.json -k -i
python3 ~/.claude/skills/json-flat-tool/jstool.py find "*api*" config.json -k -g -i

# HTTP API response — fetch and inspect inline
curl -s https://api.example.com/markets | \
  python3 ~/.claude/skills/json-flat-tool/jstool.py view -s

# WebSocket capture — save frame to temp file and inspect
echo '{"type":"book","market":"..."}' > /tmp/wss.json
python3 ~/.claude/skills/json-flat-tool/jstool.py view /tmp/wss.json -s

# Pipe / stdin
echo '{"name":"Alice"}' | python3 ~/.claude/skills/json-flat-tool/jstool.py view
curl https://api.example.com/data | python3 ~/.claude/skills/json-flat-tool/jstool.py schema
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
/new-issue 记录 WebSocket 断线重连 bug
/new-issue 添加历史推文拉取功能
/new-issue 重构 plugin manager 依赖解析
```

---

### [multipar-cli](./multipar-cli/)

Comprehensive guide for MultiPar CLI - PAR2 recovery file creation and verification tool.

**Features:**
- **PAR2 Creation** — create recovery files with configurable redundancy (5-100%)
- **File Verification** — detect corruption using parity data
- **Automatic Repair** — restore damaged files from recovery blocks
- **Batch Processing** — automate verification and repair workflows
- **Redundancy Optimization** — tune block sizes and memory usage
- **Scripting Examples** — Bash, Batch, and Python automation templates
- **Integration Patterns** — rsync, 7-Zip, and cloud storage workflows
- **Best Practices** — redundancy strategies, verification schedules, storage recommendations
- **Troubleshooting** — common issues, error codes, performance tuning

**Install:**
```bash
npx skills add DoiiarX/claude-skills@multipar-cli
```

**Quick start:**
```bash
# Create PAR2 with 10% redundancy
par2j64.exe c -r10 backup.par2 files/*

# Verify files
par2j64.exe v backup.par2

# Repair damaged files
par2j64.exe r backup.par2

# High redundancy for critical data
par2j64.exe c -r50 critical.par2 important_files/*

# Automated verification script
for par2 in *.par2; do
  par2j64.exe v -q "$par2" && echo "✓ $par2" || echo "✗ $par2"
done
```

---

## Installation

Skills are installed via the [Skills CLI](https://skills.sh/):

```bash
npx skills add DoiiarX/claude-skills@<skill-name>
```

## Contributing

Skills live in their own subdirectory with a `SKILL.md` descriptor and implementation files.
