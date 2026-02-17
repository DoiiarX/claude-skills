# claude-skills

A collection of Claude Code skills for extending agent capabilities.

## Skills

### [json-flat-tool](./json-flat-tool/)

A single-script tool (`jstool.py`) for viewing, inspecting, and editing JSON data.

**Features:**
- **Flat path/type/value view** — every field on one line: `users[0].name string Alice`
- **Schema mode** (`-s`) — collapses arrays, deduplicates, hides values
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
```

---

## Installation

Skills are installed via the [Skills CLI](https://skills.sh/):

```bash
npx skills add DoiiarX/claude-skills@<skill-name>
```

## Contributing

Skills live in their own subdirectory with a `SKILL.md` descriptor and implementation files.
