# Operations workflow

Use this only when maintaining the skill or refining safety behavior. Normal lookups should not read references.

## Default flow

1. Query structured data with `server-md server brief --name <alias> --tag <topic> --json`.
2. Prefer registered read-only shortcuts for health, status, and logs.
3. For connectivity problems, run `server-md server probe --name <alias> --json` first; add `--ssh` only when an SSH handshake is needed.
4. For destructive or production-affecting operations, present a plan and wait for explicit confirmation.

## Connectivity probes

- `server probe` checks all available host fields (`magic_dns`, `tailnet_ip`, `public_host`, `public_ip`) before summarizing.
- It should collect DNS lookup, TCP/22 reachability, and optional BatchMode SSH handshake results in one output.
- Do not stop at the first failed probe; summarize all observed failure classes together so the user does not need repeated trial-and-error.
- Prefer the word `probe` for diagnostics; avoid adding a generic `check` command because it is ambiguous with validation/lint commands.

## Shortcut safety

- `shortcut list` and `shortcut show` only inspect records.
- `shortcut run` follows the registered `execute_mode` and appends masked JSONL events to `execution.log`.
- Use `server-md log path --json` to find the log path and `server-md log tail --limit 20 --json` to inspect recent events.
- `risk=medium/high` or `confirm=true` requires `shortcut challenge`; the user must provide the confirmation code.
- Without explicit authorization, render commands instead of executing remote operations.

## Sync workflow

Use sync only when the user wants sidecar data exchanged between the main CLI and registered servers.

1. Start with a plan:
   ```bash
   server-md sync plan --server <alias> --json
   ```
2. Use `--dry-run` for pull/push/bidir before writing:
   ```bash
   server-md sync push --server <alias> --scope resources --tag <topic> --dry-run --json
   ```
3. Sync is hub-and-spoke: it only exchanges the target server slice (`servers[target]`, `resources.server == target`, `shortcuts.host == target`). It must not broadcast all known servers.
4. Default `--max-depth=1`; deeper recursion is unsupported in the first version to prevent loops and accidental fan-out.
5. Conflicts default to `fail`; do not use `local`, `remote`, `newer`, or `merge` unless the desired winner is clear.
6. Successful writes create `server-md.json.bak` next to the written sidecar and use atomic replacement.
7. Remote commands must run through `bash -lc` because some hosts use fish as the login shell.

## Secret safety

- Keep masked output by default.
- Do not print environment-file contents, tokens, passwords, private keys, full bearer strings, node keys, IP addresses, DNS names, or raw connection commands.
- Use aliases and registered shortcuts for routine operations; use command-rendering or explicit execution only after authorization.
- Use `--reveal` only when the user explicitly asks to see the real value.
