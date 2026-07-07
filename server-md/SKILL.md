---
name: server-md
description: >
  Manage a private server inventory through a compact server-md.json sidecar. Use when the user mentions SERVER.md, server inventory, self-managed servers, host aliases, operational shortcuts, or asks where the canonical server notes live. Prefer one CLI query and stop; do not read Markdown notes for facts.
allowed-tools: Bash
---

# server-md

`server-md.json` is the machine-readable source of truth. Markdown notes are only short human pointers.

## Normal task rule

Use the bundled CLI. Do not open Markdown notes or parse JSON by hand.

```bash
~/.claude/skills/server-md/server-md locate --json
~/.claude/skills/server-md/server-md server brief --name <server-or-alias> --tag <topic> --json
~/.claude/skills/server-md/server-md resource list --server <server-or-alias> --tag <topic> --json
~/.claude/skills/server-md/server-md shortcut list --server <server-or-alias> --tag <topic> --json
```

Stop when the CLI output answers the question. Do not run extra verification reads.

## Command map

| User intent | Command |
|---|---|
| Which file is canonical? | `server-md locate --json` |
| What is known about a server/topic? | `server-md server brief --name <alias> --tag <topic> --json` |
| Show resources only | `server-md resource list --server <alias> --tag <topic> --json` |
| Show shortcuts only | `server-md shortcut list --server <alias> --tag <topic> --json` |
| Register data | `server register`, `resource add`, `shortcut add` |
| Check before publishing | `server-md redact-check <paths...> --json` |

## Safety

- Never print secrets, private keys, passwords, full bearer strings, node keys, or environment-file contents.
- Destructive or production-affecting operations require a plan and explicit user confirmation.
- Registered shortcuts default to render-only. Treat high-risk shortcuts as instructions to discuss, not execute.

## Maintainer-only references

No reference files are required for normal use. If you are editing this skill or extending the CLI, read the CLI source directly.
