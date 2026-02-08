---
summary: "CLI reference for `neuroion reset` (reset local state/config)"
read_when:
  - You want to wipe local state while keeping the CLI installed
  - You want a dry-run of what would be removed
title: "reset"
---

# `neuroion reset`

Reset local config/state (keeps the CLI installed).

```bash
neuroion reset
neuroion reset --dry-run
neuroion reset --scope config+creds+sessions --yes --non-interactive
```
