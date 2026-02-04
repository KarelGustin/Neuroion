#!/bin/bash

# Start Chromium in kiosk mode for Neuroion setup UI
# Run this on Raspberry Pi with HDMI display

DISPLAY=:0
export DISPLAY

# Kill any existing Chromium instances
pkill chromium-browser || true

# Wait a moment
sleep 2

# Start Chromium in kiosk mode
chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-restore-session-state \
    --autoplay-policy=no-user-gesture-required \
    http://localhost:3000 &

# Wait for Chromium to start
sleep 5

echo "Kiosk mode started. Press Ctrl+C to stop."

# Keep script running
wait
