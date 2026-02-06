# Neuroion Smoke Test Checklist

Use this checklist to verify core flows after changes or before release.

## Prerequisites

- Raspberry Pi (or dev machine) with Neuroion installed
- Phone or tablet for onboarding
- Optional: Ollama running with `llama3.2` or `llama3.2:3b` for local model

## Smoke Test Steps

### 1. API health

- [ ] `GET /health` returns 200 and `{"status":"ok", ...}`.
- [ ] Service starts without errors (`python3 -m neuroion.core.main` or systemd).

### 2. Setup status

- [ ] `GET /setup/status` returns `is_complete` and `steps` (wifi, llm, household).
- [ ] `GET /api/status` returns network, model, uptime, household (and optionally storage, agent, degraded_message).

### 3. First-boot / setup flow (dev or Pi)

- [ ] **Welcome:** Open setup UI; first step shows "Connect to Neuroion Core Wi-Fi" and Start.
- [ ] **WiFi:** Scan networks, enter SSID/password (or skip); credentials saved.
- [ ] **Device & timezone:** Enter device name and timezone; saved via `POST /setup/device`.
- [ ] **Household / Owner / Model / Privacy:** Complete remaining steps; data persisted.
- [ ] **Validate:** Validation step runs; "Connect to home Wi-Fi" or Skip advances.
- [ ] **Finish:** Finish step calls `POST /setup/complete`; setup marked complete.
- [ ] After completion, `GET /setup/status` shows `is_complete: true`.

### 4. WiFi apply (on Pi with NetworkManager)

- [ ] After entering WiFi in setup, "Connect to home Wi-Fi" in Validate step succeeds or shows clear error.
- [ ] On success, device switches to normal mode (or document fallback).

### 5. Kiosk mode

- [ ] Open setup UI with `?kiosk=1` (e.g. `http://192.168.4.1/setup?kiosk=1`).
- [ ] Before setup complete: fullscreen Config QR is shown.
- [ ] After setup complete: dashboard (Members, WiFi, Requests, etc.) is shown.
- [ ] Add Member only available when setup is complete.

### 6. Dashboard and members

- [ ] After setup, dashboard shows Members list and "+ Add member".
- [ ] Create join token; QR and join URL displayed with Neuroion branding.
- [ ] Member roles (Owner/Admin/Guest) visible in list where applicable.

### 7. Chat / agent

- [ ] Authenticated request to `POST /chat` with a message returns a response (Python agent or Neuroion Agent when running).
- [ ] No API keys or secrets in any API response.

### 8. Per-device setup secret

- [ ] `GET /setup/setup-secret` returns a secret (AP password); value not logged.
- [ ] On Pi, AP uses this secret when configured (no default "neuroion123" in production path).

## Quick command reference

```bash
# Health
curl -s http://localhost:8000/health | jq .

# Setup status
curl -s http://localhost:8000/setup/status | jq .

# API status
curl -s http://localhost:8000/api/status | jq .
```

## Definition of Done

See [CONTRIBUTING.md](CONTRIBUTING.md#definition-of-done). Before release, run this smoke test on the target platform (e.g. Raspberry Pi) and fix any regressions.
