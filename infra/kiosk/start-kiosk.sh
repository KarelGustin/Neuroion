#!/bin/bash

# Start Chromium in kiosk mode for Neuroion touchscreen UI (Pi dashboard)
# Run this on Raspberry Pi with HDMI/touch display
# Press Ctrl+Shift+Q to exit kiosk (requires xbindkeys)

DISPLAY=:0
export DISPLAY

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXIT_SCRIPT="$SCRIPT_DIR/exit-kiosk.sh"

# Kill any existing Chromium, xbindkeys, and unclutter
pkill chromium || true
pkill xbindkeys || true
pkill unclutter || true

# Wait a moment
sleep 2

# Hide cursor after short idle (Apple-like kiosk feel)
if command -v unclutter &>/dev/null; then
	unclutter -idle 0.1 &
	sleep 0.5
else
	echo "Optional: install unclutter to hide cursor (sudo apt-get install unclutter)."
fi

# Bind Ctrl+Shift+Q to exit-kiosk.sh (global key grab)
if command -v xbindkeys &>/dev/null; then
	XBINDKEYS_RC="$(mktemp)"
	cat <<- EOF > "$XBINDKEYS_RC"
	"$EXIT_SCRIPT"
	  control+shift + q
	EOF
	DISPLAY=:0 xbindkeys -f "$XBINDKEYS_RC" &
	sleep 1
else
	echo "Warning: xbindkeys not installed. Install with: sudo apt-get install xbindkeys (Ctrl+Shift+Q will not work)."
fi

# Touchscreen UI port (dashboard on Pi): 3001 typical, or 5174 for Vite dev
TOUCHSCREEN_UI_PORT="${TOUCHSCREEN_UI_PORT:-3001}"
chromium \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-restore-session-state \
    --autoplay-policy=no-user-gesture-required \
    "http://localhost:${TOUCHSCREEN_UI_PORT}/" &

# Wait for Chromium to start
sleep 5

echo "Kiosk mode started. Press Ctrl+Shift+Q to exit."

# Keep script running
wait
