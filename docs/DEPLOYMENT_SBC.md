# Neuroion SBC Deployment Guide

## Overview

This guide covers deploying Neuroion on single-board computers (SBCs):
- Raspberry Pi 5
- Jetson Nano
- Mac (for development/demo)

## Prerequisites

### Raspberry Pi 5
- Raspberry Pi OS (Debian-based)
- Minimum 4GB RAM (8GB recommended)
- MicroSD card (32GB+)
- WiFi adapter (built-in or USB)

### Jetson Nano
- Ubuntu 20.04 or 22.04
- Minimum 4GB RAM
- WiFi adapter (USB recommended)

### Mac (Demo)
- macOS 10.15+
- Python 3.9+
- Node.js 18+

## Installation

### Automated Installation

```bash
cd /path/to/Neuroion
chmod +x infra/scripts/install.sh
sudo ./infra/scripts/install.sh [raspberry_pi|jetson|macos|auto]
```

The script will:
1. Install system dependencies
2. Install Python dependencies
3. Build all UI applications
4. Configure systemd services (Linux)
5. Setup SoftAP and mDNS (Linux)

### Manual Installation

#### 1. System Dependencies

**Raspberry Pi / Jetson:**
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv \
    hostapd dnsmasq avahi-daemon avahi-utils nginx nodejs npm sqlite3
```

**Mac:**
```bash
brew install python3 node npm
```

#### 2. Python Dependencies

```bash
cd /path/to/Neuroion
python3 -m venv venv
source venv/bin/activate
pip install -r neuroion/core/requirements.txt
```

#### 3. Build UIs

```bash
# Setup UI
cd setup-ui
npm install
npm run build

# Touchscreen UI
cd ../touchscreen-ui
npm install
npm run build

# Dashboard
cd ../dashboard-nextjs
npm install
npm run build
```

#### 4. Configure System Services (Linux only)

```bash
# Copy systemd services
sudo cp infra/systemd/*.service /etc/systemd/system/

# Copy scripts
sudo cp infra/scripts/*.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/neuroion-*.sh

# Setup SoftAP
sudo infra/scripts/setup-softap.sh

# Setup mDNS
sudo infra/scripts/setup-mdns.sh

# Enable services (neuroion-setup-mode so first boot starts in AP)
sudo systemctl daemon-reload
sudo systemctl enable neuroion-setup-mode
```

## First Boot Setup

### 1. Initial Boot

When no home WiFi is configured or setup is not yet completed, the device should start in **Setup Mode (SoftAP)** so the user can connect and complete onboarding.

On first boot (no WiFi configured / setup not complete), Neuroion will:
- Start in Setup Mode (SoftAP)
- Create WiFi hotspot: **"Neuroion-Core wizard"**
- **AP password:** Per-device setup secret (no default). Shown once on the touchscreen/kiosk after boot, or via `GET /setup/setup-secret` (e.g. `http://192.168.4.1:8000/setup/setup-secret`). Note it or scan the QR to open the setup page.
- IP address: **192.168.4.1**
- Fallback URL if captive portal does not open: **http://192.168.4.1:3000**

Ensure `neuroion-setup-mode` is enabled at install time so the Pi starts in AP on first boot; see install script.

### 2. Connect to Setup

1. Connect your phone/iPad to "Neuroion-Core wizard" WiFi
2. Captive portal should automatically open setup page
3. If not, manually visit: http://192.168.4.1:3000

### 3. Complete Setup

Follow the setup wizard:
1. **WiFi**: Select home WiFi network (or skip for offline mode)
2. **Household**: Enter household name
3. **Owner**: Enter your name, language, timezone
4. **Privacy**: Configure data retention and storage preferences
5. **Model**: Select LLM preset (fast/balanced/quality)

### 4. Finish Setup

After completing all steps:
- Device disables SoftAP
- Connects to home WiFi
- Switches to Normal Mode (LAN)
- Accessible at: http://neuroion.local (or LAN IP)

## Network Modes

### Setup Mode (SoftAP)
- SSID: "Neuroion-Core wizard"
- IP: 192.168.4.1
- Captive portal enabled
- Used during initial setup

### Normal Mode (LAN)
- Connected to home WiFi
- Accessible via mDNS: http://neuroion.local
- Fallback: http://<LAN-IP>
- All services running

### Switching Modes

```bash
# Switch to Setup Mode
sudo systemctl start neuroion-setup-mode

# Switch to Normal Mode
sudo systemctl start neuroion-normal-mode

# Or use script
sudo /usr/local/bin/neuroion-switch-network-mode.sh [setup|normal]
```

## Accessing Neuroion

### After Setup

- **Dashboard**: http://neuroion.local/dashboard
- **Touchscreen UI**: http://neuroion.local:3001
- **API**: http://neuroion.local:8000
- **Setup UI**: http://neuroion.local:3000 (or your custom host, e.g. http://neuroion.core:3000)
- **Neuroion Agent (OpenClaw) state**: stored under the Neuroion data directory at `OPENCLAW_STATE_DIR/openclaw.json` (managed automatically; no CLI required)

### Adding Members

1. Owner creates join token (from touchscreen or dashboard)
2. QR code displayed with join URL
3. Member scans QR code
4. Member completes onboarding form
5. Integration choice page shown

## Troubleshooting

### SoftAP Not Starting

```bash
# Check hostapd status
sudo systemctl status hostapd

# Check WiFi interface
iw dev

# Restart setup mode
sudo systemctl restart neuroion-setup-mode
```

### mDNS Not Working

```bash
# Check Avahi status
sudo systemctl status avahi-daemon

# Test hostname
avahi-resolve -n neuroion.local

# Restart Avahi
sudo systemctl restart avahi-daemon
```

### Network Interface Issues

**Raspberry Pi**: Usually `wlan0`
**Jetson Nano**: May be `wlan1`

Update scripts with correct interface:
```bash
export WIFI_INTERFACE=wlan1
```

## Development (Mac)

For development on Mac, skip systemd services:

```bash
# Start FastAPI backend
cd /path/to/Neuroion
source venv/bin/activate
python3 -m neuroion.core.main

# Start setup UI (new terminal)
cd setup-ui
npm run dev

# Start touchscreen UI (new terminal)
cd touchscreen-ui
npm run dev

# Start Next.js dashboard (new terminal)
cd dashboard-nextjs
npm run dev
```

Access at:
- API: http://localhost:8000
- Setup UI: http://localhost:3000
- Touchscreen: http://localhost:3001
- Dashboard: http://localhost:3002

## Development (Raspberry Pi/Linux)

When running `npm run dev` from the repo root on a Pi/Linux device, the SoftAP
setup mode is started automatically (non-fatal). If `sudo` prompts for a
password, the hotspot will be skipped and the dev servers will still start.

Kiosk mode is also started automatically (non-fatal). If Chromium is missing or
the kiosk script fails, the dev servers will still start.

## Production Deployment

### Systemd Service for Neuroion

Create `/etc/systemd/system/neuroion.service`:

```ini
[Unit]
Description=Neuroion Homebase
After=network.target

[Service]
Type=simple
User=neuroion
WorkingDirectory=/opt/neuroion
Environment="PATH=/opt/neuroion/venv/bin"
ExecStart=/opt/neuroion/venv/bin/python -m neuroion.core.main
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable neuroion
sudo systemctl start neuroion
```

## Security Notes

- Change default SoftAP password in production
- Use strong WiFi passwords
- Keep system updated
- Review firewall rules
- Consider VPN for remote access

## Support

For issues, check:
- Logs: `journalctl -u neuroion -f`
- API health: http://neuroion.local:8000/health
- System status: http://neuroion.local:8000/api/status
