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

- Optional fields may be absent: `tailnet_ip`, `magic_dns`, `public_ip`, `public_host`, `identity`, `proxy_command`, `notes_file`, `user`, `port`.
- Prefer omitting unknown optional fields instead of writing empty strings.
- The CLI should tolerate `null`, missing values, and empty strings in existing sidecars.
- Do not store secret values. Store paths and operational warnings only.

## Query rule

Normal tasks should use one compact CLI query first, especially `locate --json` or `server brief --json`, and stop when the answer is complete.
