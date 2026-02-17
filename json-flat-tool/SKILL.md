---
name: json-flat-tool
description: JSON flat view, schema inference, and edit tool. Use when the user provides a JSON file or data and wants to explore its structure, infer its schema, or modify fields. Triggers on: view json, edit json, json schema, json structure, set json field, jstool, analyze json, flat view, orderbook, json flat.
---

# JSON Flat Tool

A single-script tool (`jstool.py`) for viewing, inspecting, and editing JSON data.

Script path: `~/.claude/skills/json-flat-tool/jstool.py`

## Invocation

```bash
python3 ~/.claude/skills/json-flat-tool/jstool.py <command> [args]
```

## Commands

| Command | Description |
|---------|-------------|
| `view [file] [opts]` | Flat path/type/value display |
| `schema [file] [--title T]` | Infer JSON Schema Draft 7 |
| `set <path> <value> [file] [-f]` | Set a field value |
| `<path> = <value> [file] [-f]` | Same, B-style syntax |
| `before <path> <value> [file] [-f]` | Insert before array element |
| `after <path> <value> [file] [-f]` | Insert after array element |
| `del <path> [file] [-f]` | Delete a key or element |
| `set-null <path> [file] [-f]` | Set a field to null |

Omit `[file]` to read from stdin.

## view Options

| Flag | Unit | Description |
|------|------|-------------|
| `-s` | — | Schema mode: collapse `[N]→[*]`, deduplicate, hide values |
| `-F <path>` | — | Filter: show only this path and its children |
| `-n <N>` | rows | Show at most N rows |
| `-O <N>` | rows | Skip first N rows |
| `-E <N>` | elements | Skip first N array elements (use with `-F`) |
| `-L <N>` | elements | Show at most N array elements (use with `-F`) |

`-E` and `-L` are element-aware and never cut an element in the middle.

## Edit flags

- `-f` — Force: apply change to file. Default is **preview-only**.
- Without `-f`: shows a color-annotated diff of the original JSON with `~~~~~` underline markers at the exact change position.

## Path syntax

```
root              root node
count             root-level key
users[0]          array element
users[0].name     nested key
root[0].key       root-array element key
```

## Value parsing

Values are parsed as JSON first, then fall back to plain string:

```
Alice          → string
42             → integer
3.14           → number
true / false   → boolean
null           → null
'{"k":"v"}'    → object
'[1,2,3]'      → array
```

## Output format (view)

```
root object
users array
users[0] object
users[0].name string Alice
users[0].age integer 30
users[1].age integer (null)    ← magenta: null with inferred type
orphan unknown (null)          ← red: null, type unknown
meta object (empty)            ← dim: empty container
```

Colors: cyan = path, yellow = type, green = value,
        magenta = inferred null, red = unknown/delete, dim = empty.

## Workflow

### Explore a JSON file

```bash
# Quick structure overview
python3 ~/.claude/skills/json-flat-tool/jstool.py view data.json -s

# Filter to a nested array, element-aware pagination
python3 ~/.claude/skills/json-flat-tool/jstool.py view data.json -F "data[0].bids" -E 5 -L 3

# Infer JSON Schema Draft 7
python3 ~/.claude/skills/json-flat-tool/jstool.py schema data.json --title "My API"
```

### Edit a JSON file

```bash
# Preview change (default)
python3 ~/.claude/skills/json-flat-tool/jstool.py set users[0].name Bob data.json

# Apply change
python3 ~/.claude/skills/json-flat-tool/jstool.py set users[0].name Bob data.json -f

# B-style
python3 ~/.claude/skills/json-flat-tool/jstool.py "users[0].name" = Bob data.json -f

# Insert / delete
python3 ~/.claude/skills/json-flat-tool/jstool.py before users[1] '{"name":"Eve"}' data.json -f
python3 ~/.claude/skills/json-flat-tool/jstool.py del users[2] data.json -f
python3 ~/.claude/skills/json-flat-tool/jstool.py set-null users[0].age data.json -f
```

### Inline / piped JSON

```bash
echo '{"name":"Alice"}' | python3 ~/.claude/skills/json-flat-tool/jstool.py view
curl https://api.example.com/data | python3 ~/.claude/skills/json-flat-tool/jstool.py schema
```

## Notes

- `before` / `after` only apply to **array elements**, not object keys.
- To add a new key to an object, use `set`.
- `-f` without a file path prints modified JSON to stdout.
- `-E` / `-L` require `-F` pointing to an array path.
- Array sampling for schema inference: up to 20 elements.
- `required` in schema = fields present and non-empty in all sampled elements.
