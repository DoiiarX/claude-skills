# Sidecar config

`server-md.json` is the machine-readable source of truth. Markdown is only a short human pointer.

## Minimal shape

```json
{
  "version": 1,
  "role": "canonical",
  "priority": 100,
  "markdown": "SERVER.md",
  "environment_hint": "linux",
  "servers": {},
  "resources": {},
  "shortcuts": {},
  "execution": {
    "default_mode": "render",
    "log": "~/.server-md/ops.jsonl"
  }
}
```

## Field rules

- Optional host/contact fields may be absent: `tailnet_ip`, `magic_dns`, `public_ip`, `public_host`, `identity`, `proxy_command`, `notes_file`, `users`, `roles`, `port`.
- Server `roles` and `users` are arrays; old singular `role`/`user` fields are still accepted for compatibility and should be normalized when updating records.
- Prefer omitting unknown optional fields instead of writing empty strings.
- The CLI should tolerate `null`, missing values, and empty strings in existing sidecars.
- Do not store secret values. Store paths and operational warnings only.
- Default CLI output masks IP addresses, DNS names, host fields, connection commands, and probe output. Use aliases, shortcuts, or explicit command-rendering flows for normal operation.

## Lifecycle fields

Servers, resources, shortcuts, inventory hosts, and inventory services may carry:

- `status`: lifecycle state, usually `active`, `staging`, `deprecated`, `retired`, `disabled`, or `unknown`.
- `traffic_role`: serving role, usually `primary`, `secondary`, `staging`, or `none`.

List and brief commands support `--status` and `--traffic-role` filters. Write commands support the same fields for setting state.

## List limiting

List-like commands use `--limit N` and optional `--tail` for compact head/tail-style output.

## Query rule

Normal tasks should use one compact CLI query first, especially `locate --json`, `server brief --json`, or `server probe --json` for connectivity diagnostics, and stop when the answer is complete.
