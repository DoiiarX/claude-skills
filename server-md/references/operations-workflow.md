# Operations workflow

Use this only when maintaining the skill or refining safety behavior. Normal lookups should not read references.

## Default flow

1. Query structured data with `server-md server brief --name <alias> --tag <topic> --json`.
2. Prefer registered read-only shortcuts for health, status, and logs.
3. For destructive or production-affecting operations, present a plan and wait for explicit confirmation.

## Shortcut safety

- `shortcut list` and `shortcut show` only inspect records.
- `shortcut run` follows the registered `execute_mode`.
- `risk=medium/high` or `confirm=true` requires `shortcut challenge`; the user must provide the confirmation code.
- Without explicit authorization, render commands instead of executing remote operations.

## Secret safety

- Keep masked output by default.
- Do not print environment-file contents, tokens, passwords, private keys, full bearer strings, or node keys.
- Use `--reveal` only when the user explicitly asks to see the real value.
