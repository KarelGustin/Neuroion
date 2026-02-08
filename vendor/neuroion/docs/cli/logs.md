---
summary: "CLI reference for `neuroion logs` (tail gateway logs via RPC)"
read_when:
  - You need to tail Gateway logs remotely (without SSH)
  - You want JSON log lines for tooling
title: "logs"
---

# `neuroion logs`

Tail Gateway file logs over RPC (works in remote mode).

Related:

- Logging overview: [Logging](/logging)

## Examples

```bash
neuroion logs
neuroion logs --follow
neuroion logs --json
neuroion logs --limit 500
```
