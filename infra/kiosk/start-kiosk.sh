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

# Touchscreen UI: same port as touchscreen-ui/vite.config.js (3001 in dev)
TOUCHSCREEN_UI_PORT="${TOUCHSCREEN_UI_PORT:-3001}"
# Use 127.0.0.1 so Chromium connects via IPv4; localhost can resolve to ::1 and cause white/blank page
KIOSK_URL="http://127.0.0.1:${TOUCHSCREEN_UI_PORT}/"

# Wait for the touchscreen UI dev server to be ready (avoids white screen)
echo "Waiting for touchscreen UI at $KIOSK_URL..."
WAIT_MAX=60
WAIT_N=0
while ! (echo >/dev/tcp/127.0.0.1/${TOUCHSCREEN_UI_PORT}) 2>/dev/null; do
  sleep 1
  WAIT_N=$((WAIT_N + 1))
  if [ "$WAIT_N" -ge "$WAIT_MAX" ]; then
    echo "Warning: port $TOUCHSCREEN_UI_PORT not ready after ${WAIT_MAX}s, starting Chromium anyway."
    break
  fi
done
[ "$WAIT_N" -lt "$WAIT_MAX" ] && echo "Touchscreen UI ready at $KIOSK_URL"

chromium \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-restore-session-state \
    --autoplay-policy=no-user-gesture-required \
    "$KIOSK_URL" &

# Wait for Chromium to start
sleep 5

echo "Kiosk mode started. Press Ctrl+Shift+Q to exit."

# Keep script running
wait
