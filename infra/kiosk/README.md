# Kiosk Mode Setup

This directory contains scripts for running the Neuroion setup UI in kiosk mode on a Raspberry Pi (or similar) with HDMI display (e.g. 7" touchscreen).

## Behaviour

The kiosk opens the Setup UI with `?kiosk=1`:

- **Before setup is complete:** Fullscreen QR code is shown. Users scan it with their phone to open the setup wizard and complete configuration (WiFi, household, owner, etc.) on their device.
- **After setup is complete:** The same screen shows the **core dashboard**: connection status, members list, + Add member (QR for onboarding), Neuroion Requests count, and option to remove members.

Default URL: `http://localhost:5173/?kiosk=1` (Vite dev port). Set `SETUP_UI_PORT` if your setup UI runs on another port (e.g. 3000 for production).

## Setup

1. Install Chromium, xbindkeys (for Ctrl+Shift+Q to exit kiosk), and unclutter (to hide the mouse cursor for an Apple-like kiosk feel) on Raspberry Pi:
   ```bash
   sudo apt-get update
   sudo apt-get install chromium-browser xbindkeys unclutter
   ```

2. Make the scripts executable:
   ```bash
   chmod +x start-kiosk.sh exit-kiosk.sh
   ```

3. Configure auto-start (optional):
   - Add to `/etc/xdg/lxsession/LXDE-pi/autostart`:
     ```
     @/path/to/start-kiosk.sh
     ```
   - Or use a systemd service that starts after the setup-ui and API are running.

## Usage

- **Start kiosk:** run `./start-kiosk.sh`. Chromium opens in fullscreen.
- **Exit kiosk:** press **Ctrl+Shift+Q** (requires xbindkeys), or run `./exit-kiosk.sh` from another terminal.

Run manually:
```bash
# Default: port 5173 (setup-ui npm run dev)
./start-kiosk.sh

# Or with custom port (e.g. production build on 3000)
SETUP_UI_PORT=3000 ./start-kiosk.sh
```

Ensure the Neuroion API and Setup UI are already running before starting the kiosk.

## Hotspot (SoftAP) for onboarding on Pi 5

When you run `npm run dev` on the Pi, the setup wizard is reachable from your phone via the hotspot so you can scan the QR code and complete onboarding.

1. **One-time:** allow the hotspot script to run without sudo password (from repo root):
   ```bash
   sudo ./infra/scripts/allow-softap-sudo.sh
   ```
2. Start dev: `npm run dev`. The SoftAP will start; connect your phone to Wi‑Fi **Neuroion-Core wizard** (password: `neuroion123`).
3. On your phone open **http://neuroion.core:3000** for the onboarding wizard (or use the QR code on the kiosk). On Pi 5/Bookworm the script may use NetworkManager; then use **http://10.42.0.1:3000** if neuroion.core does not resolve.
