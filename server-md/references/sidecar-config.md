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
    "log": "~/.server-md/ops.jsonl",
    "local_server": "example-prod"
  }
}
```

## Field rules

- Optional host/contact fields may be absent: `tailnet_ip`, `magic_dns`, `public_ip`, `public_host`, `identity`, `proxy_command`, `notes_file`, `users`, `roles`, `port`.
- Server `roles` and `users` are arrays; old singular `role`/`user` fields are still accepted for compatibility and should be normalized when updating records.
- Prefer omitting unknown optional fields instead of writing empty strings.
- The CLI should tolerate `null`, missing values, and empty strings in existing sidecars.
- Do not store secret values. Store paths and operational warnings only.
- `execution.local_server` identifies the server represented by a host-scoped sidecar. Sync writes it automatically on the target. Canonical aggregate sidecars normally omit it.
- Shortcut `host` selects the execution target. Shortcut `transport` is `auto` (default), `local`, or `ssh`; new target-host commands should not contain their own SSH prefix.
- `transport=auto` preserves old commands beginning with `ssh` or `tailscale ssh` as legacy explicit transport so upgrades do not double-wrap them.
- Default CLI output masks IP addresses, DNS names, host fields, connection commands, and SSH fingerprints as `__MASKED_TYPE_hash__`. The salt is generated once in the CLI install directory, so identical values map to identical tokens on the same install. Remote `stdout`/`stderr`/`output` remains readable with embedded secrets, IPs, and hosts redacted.

## Lifecycle fields

Servers, resources, shortcuts, inventory hosts, and inventory services may carry:

- `status`: lifecycle state, usually `active`, `staging`, `deprecated`, `retired`, `disabled`, or `unknown`.
- `traffic_role`: serving role, usually `primary`, `secondary`, `staging`, or `none`.

List and brief commands support `--status` and `--traffic-role` filters. Write commands support the same fields for setting state.

## List limiting

List-like commands use `--limit N` and optional `--tail` for compact head/tail-style output.

## Sync slice shape

`server-md sync` does not copy the whole sidecar. It extracts a per-server slice:

```json
{
  "version": 1,
  "sync": {
    "target": "quant-rust",
    "max_depth": 1,
    "scopes": ["server", "resources", "shortcuts"],
    "tags": [],
    "generated_at": "2026-07-08T00:00:00+00:00",
    "source_hash": "sha256..."
  },
  "servers": {
    "quant-rust": {}
  },
  "resources": {},
  "shortcuts": {}
}
```

Slice validation rules:

- `servers` may include only the target server.
- `resources` must have `server == target`.
- `shortcuts` must have `host == target`.
- `inventory`, execution salts, unrelated servers, and unrelated shortcuts are not valid slice content. The sync writer separately sets `execution.local_server` on the target sidecar.
- First-version sync only supports `max_depth=1`; no recursive fan-out or child-server traversal.

Write safety:

- Sync writes create `server-md.json.bak` before replacing a sidecar.
- The new JSON is written to a same-directory temporary file and atomically moved into place.
- `--dry-run` never writes the JSON or backup.

## Query rule

Normal tasks should use one compact CLI find query first, usually `find --tag <topic> --limit 20 --json` or `find --filter <keyword> --limit 20 --json`, then `show` the exact candidate before `run` or reporting details. Use `server brief --json` for per-server aggregation, `locate --json` for canonical path issues, and `server probe --json` for connectivity diagnostics.
