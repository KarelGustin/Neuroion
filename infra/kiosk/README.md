# Kiosk Mode Setup

This directory contains scripts for running the Neuroion setup UI in kiosk mode on a Raspberry Pi with HDMI display.

## Setup

1. Install Chromium on Raspberry Pi:
   ```bash
   sudo apt-get update
   sudo apt-get install chromium-browser
   ```

2. Make the script executable:
   ```bash
   chmod +x start-kiosk.sh
   ```

3. Configure auto-start (optional):
   - Add to `/etc/xdg/lxsession/LXDE-pi/autostart`:
     ```
     @/path/to/start-kiosk.sh
     ```

## Usage

Run manually:
```bash
./start-kiosk.sh
```

The setup UI will open in fullscreen kiosk mode, displaying the pairing QR code.
