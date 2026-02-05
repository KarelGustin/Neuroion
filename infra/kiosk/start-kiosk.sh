#!/bin/bash

# Start Chromium in kiosk mode for Neuroion setup UI
# Run this on Raspberry Pi with HDMI display

DISPLAY=:0
export DISPLAY

# Kill any existing Chromium instances
pkill chromium-browser || true

# Wait a moment
sleep 2

# Setup UI port: 5173 (Vite dev) or 3000 (production build)
SETUP_UI_PORT="${SETUP_UI_PORT:-5173}"
# Kiosk URL: ?kiosk=1 shows config QR when setup incomplete, then core dashboard when complete
chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-restore-session-state \
    --autoplay-policy=no-user-gesture-required \
    "http://localhost:${SETUP_UI_PORT}/?kiosk=1" &

# Wait for Chromium to start
sleep 5

echo "Kiosk mode started. Press Ctrl+C to stop."

# Keep script running
wait
