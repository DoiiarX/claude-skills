---
name: json-flat-tool
description: JSON 平铺查看与编辑工具。当用户提供 JSON 文件/数据并想要查看结构、修改字段、插入/删除元素时使用。触发词：view json, edit json, set json field, jstool, json flat, 查看json, 编辑json, 修改json字段
---

# JSON Flat Tool Skill

此 skill 使用 `jstool.py` 对 JSON 数据进行平铺查看和结构化编辑。

脚本路径：`~/.claude/skills/json-flat-tool/jstool.py`

## 调用方式

```bash
python3 ~/.claude/skills/json-flat-tool/jstool.py <command> [args]
```

## 命令一览

| 命令 | 说明 |
|------|------|
| `view [file] [-s] [-F path] [-n N] [-O N]` | 平铺显示 JSON 结构 |
| `set <path> <value> [file] [-f]` | 修改字段值 |
| `<path> = <value> [file] [-f]` | 同上，B-style 语法 |
| `before <path> <value> [file] [-f]` | 在数组元素前插入 |
| `after <path> <value> [file] [-f]` | 在数组元素后插入 |
| `del <path> [file] [-f]` | 删除字段或元素 |
| `set-null <path> [file] [-f]` | 将字段设为 null |

**view 选项**：
- `-s` / `--schema`：结构模式——合并 `[N]→[*]`，去重，隐藏具体值
- `-F <path>`：只显示该路径及其子节点
- `-n <N>`：最多显示 N 行
- `-O <N>`：跳过前 N 行（配合 `-n` 实现分页）

**`-f` 标志**（编辑命令）：默认为预览模式；加 `-f` 才真正写入文件。

## 路径语法

```
root              → 根节点
count             → 根级别字段
users[0]          → 数组元素
users[0].name     → 嵌套字段
root[0].key       → 根数组元素的字段
```

## 值语法

```
Alice             → string（自动推断）
42                → integer
3.14              → number
true / false      → boolean
null              → null
'{"k":"v"}'       → object（JSON 格式）
'[1,2,3]'         → array（JSON 格式）
```

## 输出格式

`view` 命令输出格式：`path type value`

```
root object
users array
users[0] object
users[0].name string Alice
users[0].age integer 30
users[1].age integer (null)     ← 品红：null 但推断出类型
orphan unknown (null)           ← 红色：无法推断类型
meta object (empty)             ← 暗色：空容器
```

颜色说明：
- 青色：路径
- 黄色：类型
- 绿色：值
- 品红色：null（类型已推断）
- 红色：unknown null / 删除操作
- 暗色：(empty) 容器

## 预览模式示例

预览 `set users[0].name Bob`:
```
  {
    "users": [
      {
        "name": "Alice",
                ~~~~~~~ → "Bob"
        ...
      }
    ]
  }

[PREVIEW] set users[0].name: "Alice" → "Bob"
Run with -f to apply.
```

## 工作流程

### Step 1: 确认输入
用户提供：
- 文件路径（`/path/to/data.json`）
- 或直接粘贴 JSON 字符串

对于粘贴的内容，先保存到临时文件：
```bash
cat > /tmp/data.json << 'EOF'
<user's json>
EOF
```

### Step 2: 查看结构
```bash
python3 ~/.claude/skills/json-flat-tool/jstool.py view /tmp/data.json
```

### Step 3: 执行编辑（预览）
```bash
# 修改字段
python3 ~/.claude/skills/json-flat-tool/jstool.py set users[0].name "Bob" /tmp/data.json

# B-style 等价写法
python3 ~/.claude/skills/json-flat-tool/jstool.py "users[0].name" = "Bob" /tmp/data.json
```

### Step 4: 确认后写入
```bash
python3 ~/.claude/skills/json-flat-tool/jstool.py set users[0].name "Bob" /tmp/data.json -f
```

### Step 5: stdin 管道（只读，无法 -f 写回）
```bash
curl https://api.example.com/data | python3 ~/.claude/skills/json-flat-tool/jstool.py view
```

## 注意事项

- `before`/`after` 只对**数组元素**有效，对 object key 无效
- object 新增字段统一用 `set`（自动追加到末尾）
- stdin 模式下，`-f` 无法写回（无文件路径），会打印到 stdout
- 路径大小写敏感，与 JSON key 一致
