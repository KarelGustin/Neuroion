---
summary: "CLI reference for `neuroion agents` (list/add/delete/set identity)"
read_when:
  - You want multiple isolated agents (workspaces + routing + auth)
title: "agents"
---

# `neuroion agents`

Manage isolated agents (workspaces + auth + routing).

Related:

- Multi-agent routing: [Multi-Agent Routing](/concepts/multi-agent)
- Agent workspace: [Agent workspace](/concepts/agent-workspace)

## Examples

```bash
neuroion agents list
neuroion agents add work --workspace ~/.neuroion/workspace-work
neuroion agents set-identity --workspace ~/.neuroion/workspace --from-identity
neuroion agents set-identity --agent main --avatar avatars/neuroion.png
neuroion agents delete work
```

## Identity files

Each agent workspace can include an `IDENTITY.md` at the workspace root:

- Example path: `~/.neuroion/workspace/IDENTITY.md`
- `set-identity --from-identity` reads from the workspace root (or an explicit `--identity-file`)

Avatar paths resolve relative to the workspace root.

## Set identity

`set-identity` writes fields into `agents.list[].identity`:

- `name`
- `theme`
- `emoji`
- `avatar` (workspace-relative path, http(s) URL, or data URI)

Load from `IDENTITY.md`:

```bash
neuroion agents set-identity --workspace ~/.neuroion/workspace --from-identity
```

Override fields explicitly:

```bash
neuroion agents set-identity --agent main --name "Neuroion" --emoji "🦞" --avatar avatars/neuroion.png
```

Config sample:

```json5
{
  agents: {
    list: [
      {
        id: "main",
        identity: {
          name: "Neuroion",
          theme: "space lobster",
          emoji: "🦞",
          avatar: "avatars/neuroion.png",
        },
      },
    ],
  },
}
```
