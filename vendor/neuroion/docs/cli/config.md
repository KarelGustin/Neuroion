---
summary: "CLI reference for `neuroion config` (get/set/unset config values)"
read_when:
  - You want to read or edit config non-interactively
title: "config"
---

# `neuroion config`

Config helpers: get/set/unset values by path. Run without a subcommand to open
the configure wizard (same as `neuroion configure`).

## Examples

```bash
neuroion config get browser.executablePath
neuroion config set browser.executablePath "/usr/bin/google-chrome"
neuroion config set agents.defaults.heartbeat.every "2h"
neuroion config set agents.list[0].tools.exec.node "node-id-or-name"
neuroion config unset tools.web.search.apiKey
```

## Paths

Paths use dot or bracket notation:

```bash
neuroion config get agents.defaults.workspace
neuroion config get agents.list[0].id
```

Use the agent list index to target a specific agent:

```bash
neuroion config get agents.list
neuroion config set agents.list[1].tools.exec.node "node-id-or-name"
```

## Values

Values are parsed as JSON5 when possible; otherwise they are treated as strings.
Use `--json` to require JSON5 parsing.

```bash
neuroion config set agents.defaults.heartbeat.every "0m"
neuroion config set gateway.port 19001 --json
neuroion config set channels.whatsapp.groups '["*"]' --json
```

Restart the gateway after edits.
