---
name: server-md
description: >
  管理个人 SERVER.md 运维知识库。Use this skill whenever the user mentions ~/SERVER.md, SERVER.md, 服务器清单, server inventory, tailnet nodes, self-managed servers, WSL/Windows/Ubuntu host notes, or asks Claude to create, locate, update, summarize, or use a personal server runbook. It helps Claude find the canonical SERVER.md across WSL, Windows, native Ubuntu, and remote hosts; preserve progressive disclosure by splitting details into reference files; summarize local machine and managed servers without leaking secrets; and turn server notes into safe operational checklists.
allowed-tools: Bash
---

# SERVER.md 运维知识库 Skill

这个 skill 用来维护个人服务器清单与运维手册。核心标准是机器可读的 `server-md.json` sidecar；Markdown 只做简短人类入口，建议保持 200 行以内。普通查询不要打开 references；只有维护 skill / CLI / schema / eval 时才读对应参考。

## 必须使用 `server-md` CLI（sidecar 是唯一事实源）

`server-md.json` 是核心标准和唯一结构化事实源。Markdown 只允许作为占位符和简短说明；事实查询只走 CLI。

禁止为了常见查询再调用 Markdown 读取或分段流程；如果 CLI 返回了足够信息，立即停止，不要二次验证。

### 一跳查询规则

```bash
# 判断主副本：只跑这一条，然后结束
~/.claude/skills/server-md/server-md locate --json

# 查询某服务器、相关资源和快捷命令：优先一条 brief
~/.claude/skills/server-md/server-md server brief --name prod --tag web --json

# 只查资源
~/.claude/skills/server-md/server-md resource list --server prod --tag web --json

# 只查快捷命令
~/.claude/skills/server-md/server-md shortcut list --server prod --tag web --json
```

### 允许的常用命令

- `locate --json`：返回 compact 主副本/sidecar 定位；默认不要 `--verbose`。
- `server list|resolve|connect|brief`：服务器查询；`connect` 只渲染 SSH 命令，不执行。
- `resource list|show|add`：资源查询/注册，支持 `warnings`、`tips`、`constraints`。
- `shortcut list|show|add|run`：快捷命令查询/渲染，支持 `--server`、`--tag`、warnings/tips/constraints。
- `redact-check`：发布前脱敏扫描。
- `inventory *`：结构化 inventory 维护。

只有在新增 CLI 功能、修 CLI bug、或用户明确要求看人类说明时，才打开 `SERVER.md`。


## CLI 速查

默认输出会 mask secret-like 字段和值。不要主动揭示真实 secret；只有用户明确要求查看真实值时，才使用本节末尾的高级参数。

### locate / env

```bash
server-md locate --json
server-md env --json
```

### server

```bash
server-md server list --json
server-md server resolve --name <name-or-alias> --json
server-md server connect --name <name-or-alias> --prefer tailnet --json
server-md server brief --name <name-or-alias> --tag <topic> --json
server-md server register --name <name> --alias <alias> --user <user> --magic-dns <host> --json
```

Notes:
- `connect` only renders an SSH command; do not execute it unless the user asks.
- Optional fields such as `tailnet_ip`, `magic_dns`, `public_ip`, `public_host`, `identity`, `proxy_command`, `notes_file`, `user`, and `port` may be absent.
- Prefer omitting unknown optional fields over writing empty strings.

### resource

```bash
server-md resource list --server <name-or-alias> --tag <topic> --json
server-md resource show --name <resource-name> --json
server-md resource add --name <name> --server <server> --kind project --path <path> --tag <tag> --json
```

### shortcut

```bash
server-md shortcut list --server <name-or-alias> --tag <topic> --json
server-md shortcut show --category <category> --name <name> --json
server-md shortcut add --category health --name <name> --host <server> --command '<cmd>' --risk read-only --execute-mode render --json
server-md shortcut challenge --category <category> --name <name> --json
server-md shortcut run --category <category> --name <name> --json
server-md shortcut run --category <category> --name <name> --confirm-code <code> --json
```

Rules:
- `list` and `show` only inspect records.
- `run` follows the registered `execute_mode`: `render`, `manual`, or `auto`.
- `risk=medium/high` or `confirm=true` requires `challenge`; the user must provide the confirmation code.
- Without explicit authorization, render commands instead of executing remote operations.

### inventory

```bash
server-md inventory init --json
server-md inventory list --kind hosts --json
server-md inventory list --kind services --host <host> --tag <tag> --json
server-md inventory host-set --name <host> --tailnet-ip <ip> --tag <tag> --json
server-md inventory service-set --name <service> --host <host> --unit <unit> --healthcheck <url> --json
server-md inventory validate --json
```

### redact-check

```bash
server-md redact-check <paths...> --json
server-md redact-check <paths...> --fix --json
```

- `--fix` masks detected secret-like values in place.
- Keep masked output by default.

### 高级：显示被掩码的真实值

`--reveal` 是全局参数，必须放在子命令前。只有用户明确要求查看真实值时才用：

```bash
server-md --reveal <subcommand> ...
server-md --reveal redact-check <paths...> --json
```

Do not use `--reveal` for routine diagnostics, examples, docs, or A/B tests.

## 核心原则

1. **JSON 优先，Markdown 退场**
   - `server-md.json` 决定主副本、服务器、资源、快捷命令、warnings、tips、constraints。
   - `SERVER.md` 不保存长命令和细节；事实查询只走 CLI。

2. **一跳够用就停止**
   - 主副本判断 = `locate --json`。
   - 服务器上下文 = `server brief --name <name> [--tag <tag>] --json`。
   - 不要为了“确认一下”再读 Markdown。

3. **敏感信息默认不输出**
   - 不要输出 token、密码、私钥、SMTP 授权码、完整 Bearer token、完整 cloudflared token、兑换码私钥等。
   - 命令示例使用环境变量占位。

4. **危险操作先确认**
   - 涉及公网、DNS、生产服务、数据、账号状态、删除、重启、token 轮换时，先给计划和影响，不直接执行。

## 文件结构

```text
server-md/
├── SKILL.md
├── server-md
├── examples/
│   └── server-md.example.json
└── references/
    ├── sidecar-config.md
    └── operations-workflow.md
```

## 输出风格

- 用简短表格先给结论，再给命令。
- 明确说明信息来自 `server-md` CLI / sidecar 查询，而不是 Markdown 正文。
- 当信息可能过期时，给出验证命令，而不是假设仍正确。
- 如命令涉及重启、删除、DNS、Cloudflare、生产数据库、兑换码作废、token 轮换，先给计划，不要直接执行。

## 相关参考

普通查询不要打开 references。只有在维护 skill / CLI / schema / 安全流程时才读对应文件：

- `examples/server-md.example.json` — 完全脱敏的 sidecar 示例。
- `references/sidecar-config.md` — sidecar schema 与空值规则维护。
- `references/operations-workflow.md` — shortcut 执行与安全规则维护。
