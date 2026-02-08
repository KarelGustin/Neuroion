#!/bin/bash
# Stop kiosk mode: kill Chromium and the key listener.
# Can be run by Ctrl+Shift+Q (via xbindkeys) or manually.

DISPLAY="${DISPLAY:-:0}"
export DISPLAY

# Stop Chromium kiosk
pkill -f "chromium.*--kiosk" || pkill chromium || true

# Stop xbindkeys and unclutter (started by start-kiosk.sh) so next start is clean
pkill xbindkeys || true
pkill unclutter || true

echo "Kiosk mode stopped."
