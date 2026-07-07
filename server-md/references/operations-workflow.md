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
- `shortcut run` follows the registered `execute_mode`.
- `risk=medium/high` or `confirm=true` requires `shortcut challenge`; the user must provide the confirmation code.
- Without explicit authorization, render commands instead of executing remote operations.

## Secret safety

- Keep masked output by default.
- Do not print environment-file contents, tokens, passwords, private keys, full bearer strings, or node keys.
- Use `--reveal` only when the user explicitly asks to see the real value.
