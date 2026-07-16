---
name: server-md
description: >
  管理个人 SERVER.md 运维知识库。Use this skill whenever the user mentions ~/SERVER.md, SERVER.md, 服务器清单, server inventory, tailnet nodes, self-managed servers, WSL/Windows/Ubuntu host notes, or asks Claude to create, locate, update, summarize, or use a personal server runbook. It helps Claude find the canonical SERVER.md across WSL, Windows, native Ubuntu, and remote hosts; preserve progressive disclosure by splitting details into reference files; summarize local machine and managed servers without leaking secrets; and turn server notes into safe operational checklists.
---

# SERVER.md 运维知识库 Skill

这个 skill 用来通过 `server-md` CLI 查询和维护个人服务器清单、资源和运维快捷命令。常见需求走“需求词 → tag → find → show → run/render”的短路径：先用 tag 一次发现候选 shortcut/resource/server，再 show 精确记录，最后按 risk / execute_mode 决定 run、render 或请用户确认。主副本定位、环境排查、schema 维护等场景再使用高级命令。

## 快速流程

### 1. 从需求提取候选 tag

从用户原话提取 1–3 个自然 tag；优先用通用词、服务类型、资源类型。同义词可以并查，但不要为了“确认一下”全量扫 sidecar。

| 用户说法 | 候选 tag |
|---|---|
| X / Twitter / 推文 / tweets API | `tweet`, `tweets`, `tweets-api`, `twitter`, `x`, `public-api` |
| 代理 / SOCKS / 转发 | `proxy`, `socks`, `tunnel` |
| Cloudflare / DNS / tunnel | `cloudflare`, `cloudflared`, `tunnel` |
| Tailnet / VPN / 节点网络 | `tailnet`, `tailscale`, `headscale` |
| 数据库 / 备份 / 日志 | `database`, `backup`, `logs` |

### 2. find：一次发现候选 shortcut/resource/server

```bash
~/.claude/skills/server-md/server-md find --tag <tag> --limit 20 --json
~/.claude/skills/server-md/server-md find --tag tweet --tag twitter --tag x --limit 20 --json
```

如果只想找可执行入口，限制类型：

```bash
~/.claude/skills/server-md/server-md find --tag <tag> --type shortcut --limit 20 --json
```

如果 tag 不确定，用关键词过滤：

```bash
~/.claude/skills/server-md/server-md find --filter <keyword> --limit 20 --json
```

### 3. show：查看精确记录

从 `find` 结果中选出最相关的 shortcut/resource 后，先 `show`，再决定是否运行。`show` 用于确认 `description`、`risk`、`execute_mode`、`warnings`、`tips`、`params`。

```bash
~/.claude/skills/server-md/server-md shortcut show --category <category> --name <name> --json
~/.claude/skills/server-md/server-md resource show --name <resource-name> --json
```

如果需要聚合某台服务器上的相关资源和 shortcut：

```bash
~/.claude/skills/server-md/server-md server brief --name <server-or-alias> --tag <tag> --json
```

### 4. run/render：执行或渲染 shortcut

根据 `risk` / `execute_mode` / `warnings` 决定是否直接运行：

```bash
~/.claude/skills/server-md/server-md shortcut run --category <category> --name <name> --execute-mode auto --arg key=value --raw --json
```

- `risk=read-only` 且 `execute_mode=auto`：通常可以直接 `run`。
- `execute_mode=render/manual`：只渲染命令或按说明操作，不擅自执行远程操作。
- `risk=medium/high`、`confirm=true`、涉及重启/删除/DNS/生产数据/token 轮换：先说明影响，等待用户确认。
- 默认不使用 `--reveal`，不输出 token、密码、私钥、完整 host/IP/连接命令。

## tag 不确定时：subagent 推荐 tag

需求模糊或 tag 命名不确定时，可以启动一个不继承当前上下文细节的 subagent 做轻量发现。它只需要推荐 tag 和下一步 `show` 的候选，不要完整跑完任务；主 agent 再继续执行。

推荐 prompt：

```text
你只能使用 server-md CLI，不能使用 --reveal，不能读取 sidecar 原文。
给定自然需求：“<用户原始需求>”。
请用少量 `server-md find` 查询判断应该搜索哪些 tag，以及最可能的 resource/shortcut 名称。
返回：推荐 tag 列表、命中的 shortcut/resource、是否有歧义、建议下一步 show 的精确 category/name 或 resource name。
```

目标输出形态：

```text
推荐 tags: <tag1>, <tag2>, <tag3>
下一步 show shortcut: <category>/<name>
下一步 show resource: <resource-name>
歧义: <none|说明>
```

## 常用命令

默认输出会 mask secret-like 字段和值，也会 mask IP/host/command/SSH 指纹等连接目标。Mask 格式为 `__MASKED_TYPE_hash__`，同一真实值在同一 CLI 安装目录内会稳定映射到同一 token，方便判断多行日志是否指向同一对象。`stdout`/`stderr`/`output` 会保留可读日志内容，但会掩码其中的 secret、IP、host 和 SSH 指纹。

### find

```bash
server-md find --tag <topic> --limit 20 --json
server-md find --tag <topic> --type shortcut --limit 20 --json
server-md find --filter <keyword> --limit 20 --json
server-md find --tag <topic> --type shortcut --type resource --json
```

Rules:
- `find` 同时查询 shortcut/resource/server，结果按 shortcut → resource → server 排序。
- 多个 `--tag` 是 OR 语义；`--type` 可重复，也支持 `shortcut,resource` 逗号分隔。
- 普通查询先 `find`，命中后 `show` 精确记录；需要单机聚合时才用 `server brief`。

### server

```bash
server-md server list --status active --traffic-role primary --limit 20 --json
server-md server list --tail --limit 5 --json
server-md server resolve --name <name-or-alias> --json
server-md server connect --name <name-or-alias> --prefer tailnet --json
server-md server probe --name <name-or-alias> --prefer auto --timeout 5 --json
server-md server probe --name <name-or-alias> --ssh --json
server-md server brief --name <name-or-alias> --tag <topic> --status active --limit 20 --json
server-md server register --name <name> --alias <alias> --user <user> --role <role> --magic-dns <host> --status active --traffic-role primary --json
```

Notes:
- `connect` only renders an SSH command; do not execute it unless the user asks.
- `probe` collects DNS, TCP/22, and optional SSH findings in one result; use it for connectivity troubleshooting before guessing.
- List-like commands use `--limit` and optional `--tail` for compact head/tail-style output.
- `--status` filters lifecycle state (`active`, `staging`, `deprecated`, `retired`, `disabled`, `unknown`); `--traffic-role` filters serving role (`primary`, `secondary`, `staging`, `none`).
- `--role` and `--user` may be repeated; server records store them as `roles[]` and `users[]` while remaining compatible with old singular `role`/`user` sidecars.
- Optional fields such as `tailnet_ip`, `magic_dns`, `public_ip`, `public_host`, `identity`, `proxy_command`, `notes_file`, `users`, and `port` may be absent.
- Prefer omitting unknown optional fields over writing empty strings.

### resource

```bash
server-md resource list --server <name-or-alias> --tag <topic> --status active --limit 20 --json
server-md resource list --status retired --tail --limit 10 --json
server-md resource show --name <resource-name> --json
server-md resource add --name <name> --server <server> --kind project --path <path> --tag <tag> --status active --traffic-role primary --json
```

### shortcut

```bash
server-md shortcut list --server <name-or-alias> --tag <topic> --status active --limit 20 --json
server-md shortcut show --category <category> --name <name> --json
server-md shortcut add --category health --name <name> --host <server> --command '<target-host command with {{param}}>' --transport auto --param param=default --risk read-only --execute-mode render --status active --traffic-role primary --json
server-md shortcut challenge --category <category> --name <name> --arg param=value --json
server-md shortcut run --category <category> --name <name> --execute-mode auto --arg param=value
server-md shortcut run --category <category> --name <name> --execute-mode auto --raw
server-md shortcut run --category <category> --name <name> --execute-mode auto --raw --json
server-md shortcut run --category <category> --name <name> --execute-mode auto --detail
server-md shortcut run --category <category> --name <name> --execute-mode auto --detail --json
server-md shortcut run --category <category> --name <name> --confirm-code <code> --detail --json
```

Rules:
- `list` and `show` only inspect records.
- `add` writes shortcut metadata directly into `server-md.json`; do not create wrapper files/directories, clone repositories, or change CLI code just to register a shortcut.
- `shortcut.host` is executable targeting, not descriptive metadata. With `transport=auto`, `run` executes locally only when the sidecar declares/detects that host as the current machine; otherwise it builds the registered SSH connection automatically.
- Store the command as it should run on the target host, for example `systemctl status app --no-pager`. Do not manually prepend SSH to new shortcuts.
- `transport=local` explicitly runs on the caller even when `host` is present; use it for public HTTP checks or caller-side orchestration. `transport=ssh` always uses the registered server connection.
- Legacy commands that already begin with `ssh` or `tailscale ssh` are executed unchanged and marked `legacy_explicit_transport`; migrate them gradually instead of wrapping them twice.
- `shortcut challenge` and `shortcut run` resolve the same target and template arguments, so pass the same repeated `--arg` values to both.
- Template placeholders use `{{name}}`. Register safe defaults with `shortcut add --param name=value`; override at run time with repeated `shortcut run --arg name=value`.
- Template values are constrained to a safe character set (`letters/digits/_.:@%+=,/-`) and are substituted by the CLI, not by shell eval.
- `run` follows the registered `execute_mode`: `render`, `manual`, or `auto`.
- `run` has two output shapes: raw and detail. Raw prints only stdout/stderr and is the default for log-reading; detail includes metadata plus stdout/stderr.
- `--json` is only a format switch for the selected shape: `--raw --json` returns `{stdout,stderr}`, while `--detail --json` returns the full envelope.
- Every `run` appends a masked JSONL event to `execution.log` (default `~/.server-md/ops.jsonl`).
- `risk=medium/high` or `confirm=true` requires `challenge`; the user must provide the confirmation code.
- Without explicit authorization, render commands instead of executing remote operations.

### log

```bash
server-md log path --json
server-md log tail --limit 20 --json
server-md log tail --category health --name <shortcut-name> --json
```

Rules:
- `log path` returns the configured JSONL log path.
- `log tail` reads recent shortcut execution events; output stays masked by default.

### sync

```bash
server-md sync plan --server <name-or-alias> --json
server-md sync pull --server <name-or-alias> --dry-run --json
server-md sync push --server <name-or-alias> --scope resources --tag <topic> --dry-run --json
server-md sync bidir --server <name-or-alias> --conflict merge --dry-run --json
```

Rules:
- `sync` only exchanges the target server slice: `servers[target]`, resources whose `server` is target, and shortcuts whose `host` is target.
- Default `--max-depth` is `1`; deeper recursion is intentionally unsupported in this version.
- `push` never sends the whole local sidecar to a child server; `pull` never imports unrelated remote servers.
- Writes create `server-md.json.bak` next to the written sidecar and then atomically replace the JSON file.
- Conflicts default to `fail`; use `--conflict local|remote|newer|merge` only when the desired winner is clear.
- Remote commands, including host-targeted shortcuts, are wrapped in `bash -lc` so a fish default shell does not parse bash syntax.
- Successful push/bidirectional sync writes `execution.local_server=<target>` into the host-scoped sidecar. This prevents a target host from SSHing back into itself.
- Use repeated `--server` to sync selected servers only; do not use sync as a broadcast mechanism.

### inventory

```bash
server-md inventory init --json
server-md inventory list --kind hosts --status active --limit 20 --json
server-md inventory list --kind services --host <host> --tag <tag> --traffic-role primary --json
server-md inventory host-set --name <host> --tailnet-ip <ip> --tag <tag> --status active --json
server-md inventory service-set --name <service> --host <host> --unit <unit> --healthcheck <url> --status active --traffic-role primary --json
server-md inventory validate --json
```

### 高级命令

```bash
server-md locate --json
server-md env --json
server-md redact-check <paths...> --json
server-md redact-check <paths...> --fix --json
```

- `locate --json`：定位主副本和 sidecar，适用于用户要求查找 SERVER.md、路径异常、迁移或维护 CLI/schema。
- `env --json`：查看 CLI 运行环境和配置来源，适用于排查环境差异。
- `redact-check`：发布或同步前做脱敏扫描；`--fix` 会就地改文件。
- Keep masked output by default.

### 高级：显示被掩码的真实值

`--reveal` 是全局参数，必须放在子命令前。只有用户明确要求查看真实值时才用。可以一次 reveal 多个类型；不传类型表示 reveal 全部。

```bash
server-md --reveal HOST IP <subcommand> ...
server-md --reveal __MASKED_HOST_ab12cd34ef__ __MASKED_IP_9f8e7d6c5b__ shortcut run --category logs --name newapi-errors --detail --json
server-md --reveal SSH_KEY HOST shortcut run --category logs --name newapi-errors --detail --json
server-md --reveal redact-check <paths...> --json
```

Mask token 使用稳定格式 `__MASKED_TYPE_hash__`，例如 `__MASKED_HOST_ab12cd34ef__`。同一 CLI 安装目录内首次运行会生成持久 salt，因此同一真实值会稳定映射到同一 token，方便跨行判断一致性；不同机器/安装目录不共享 salt。`--reveal` 支持一次传多个类型或多个具体 mask token：传类型会 reveal 该类型全部值，传具体 token 只 reveal 对应值。

## 核心原则

1. **Tag-first，find-first，show-before-run**
   - 从自然需求先推 1–3 个 tag，优先 `find --tag ...` 一次发现 shortcut/resource/server。
   - 命中候选后必须 `show` 精确记录，再根据 `risk` / `execute_mode` / `warnings` 决定 `run`、render 或请求确认。
   - 普通查询路径是 `find → shortcut/resource show → shortcut run/render`；定位、环境和维护路径归入“高级命令”。

2. **JSON/sidecar 是事实源**
   - `server-md.json` 决定服务器、资源、快捷命令、warnings、tips、constraints。
   - 通过 CLI 查询这些事实；Markdown 保持为简短入口和参考索引。

3. **一跳够用就停止**
   - `show` 返回足够信息时，直接给出结论或下一条安全命令。
   - `run` 只用于已确认的 shortcut；不要为拿 token、host、命令原文而使用 `--reveal`。
   - 需要聚合上下文时使用 `server brief --name <name> --tag <tag> --json`。

4. **敏感信息和网络地址默认不输出**
   - 不要输出 token、密码、私钥、SMTP 授权码、完整 Bearer token、完整 cloudflared token、兑换码私钥等。
   - 默认也不要输出 IP、MagicDNS/public host 和连接命令；平时用别名、shortcut、`connect`/`run` 渲染流程承接。
   - 远程命令的 `stdout`/`stderr` 可以保留结论性日志内容，但必须掩码其中的 secret、IP、host 和 SSH 指纹。
   - 命令示例使用环境变量或占位。

5. **危险操作先确认**
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
