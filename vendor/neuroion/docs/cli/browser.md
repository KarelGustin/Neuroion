---
summary: "CLI reference for `neuroion browser` (profiles, tabs, actions, extension relay)"
read_when:
  - You use `neuroion browser` and want examples for common tasks
  - You want to control a browser running on another machine via a node host
  - You want to use the Chrome extension relay (attach/detach via toolbar button)
title: "browser"
---

# `neuroion browser`

Manage Neuroion’s browser control server and run browser actions (tabs, snapshots, screenshots, navigation, clicks, typing).

Related:

- Browser tool + API: [Browser tool](/tools/browser)
- Chrome extension relay: [Chrome extension](/tools/chrome-extension)

## Common flags

- `--url <gatewayWsUrl>`: Gateway WebSocket URL (defaults to config).
- `--token <token>`: Gateway token (if required).
- `--timeout <ms>`: request timeout (ms).
- `--browser-profile <name>`: choose a browser profile (default from config).
- `--json`: machine-readable output (where supported).

## Quick start (local)

```bash
neuroion browser --browser-profile chrome tabs
neuroion browser --browser-profile neuroion start
neuroion browser --browser-profile neuroion open https://example.com
neuroion browser --browser-profile neuroion snapshot
```

## Profiles

Profiles are named browser routing configs. In practice:

- `neuroion`: launches/attaches to a dedicated Neuroion-managed Chrome instance (isolated user data dir).
- `chrome`: controls your existing Chrome tab(s) via the Chrome extension relay.

```bash
neuroion browser profiles
neuroion browser create-profile --name work --color "#FF5A36"
neuroion browser delete-profile --name work
```

Use a specific profile:

```bash
neuroion browser --browser-profile work tabs
```

## Tabs

```bash
neuroion browser tabs
neuroion browser open https://docs.neuroion.ai
neuroion browser focus <targetId>
neuroion browser close <targetId>
```

## Snapshot / screenshot / actions

Snapshot:

```bash
neuroion browser snapshot
```

Screenshot:

```bash
neuroion browser screenshot
```

Navigate/click/type (ref-based UI automation):

```bash
neuroion browser navigate https://example.com
neuroion browser click <ref>
neuroion browser type <ref> "hello"
```

## Chrome extension relay (attach via toolbar button)

This mode lets the agent control an existing Chrome tab that you attach manually (it does not auto-attach).

Install the unpacked extension to a stable path:

```bash
neuroion browser extension install
neuroion browser extension path
```

Then Chrome → `chrome://extensions` → enable “Developer mode” → “Load unpacked” → select the printed folder.

Full guide: [Chrome extension](/tools/chrome-extension)

## Remote browser control (node host proxy)

If the Gateway runs on a different machine than the browser, run a **node host** on the machine that has Chrome/Brave/Edge/Chromium. The Gateway will proxy browser actions to that node (no separate browser control server required).

Use `gateway.nodes.browser.mode` to control auto-routing and `gateway.nodes.browser.node` to pin a specific node if multiple are connected.

Security + remote setup: [Browser tool](/tools/browser), [Remote access](/gateway/remote), [Tailscale](/gateway/tailscale), [Security](/gateway/security)
