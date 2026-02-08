---
summary: "CLI reference for `neuroion voicecall` (voice-call plugin command surface)"
read_when:
  - You use the voice-call plugin and want the CLI entry points
  - You want quick examples for `voicecall call|continue|status|tail|expose`
title: "voicecall"
---

# `neuroion voicecall`

`voicecall` is a plugin-provided command. It only appears if the voice-call plugin is installed and enabled.

Primary doc:

- Voice-call plugin: [Voice Call](/plugins/voice-call)

## Common commands

```bash
neuroion voicecall status --call-id <id>
neuroion voicecall call --to "+15555550123" --message "Hello" --mode notify
neuroion voicecall continue --call-id <id> --message "Any questions?"
neuroion voicecall end --call-id <id>
```

## Exposing webhooks (Tailscale)

```bash
neuroion voicecall expose --mode serve
neuroion voicecall expose --mode funnel
neuroion voicecall unexpose
```

Security note: only expose the webhook endpoint to networks you trust. Prefer Tailscale Serve over Funnel when possible.
