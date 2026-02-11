# Neuroion Touchscreen UI

Dashboard UI for the Neuroion touchscreen (runs on port 3001). **This is the screen shown in kiosk mode** on the device display; the kiosk startup script opens this UI (see `infra/kiosk/start-kiosk.sh`).

## Environment

- **`VITE_NEUROION_AUTOLAUNCH`** – Set to `1` or `true` to auto-redirect to the Neuroion UI when the dashboard loads (e.g. for kiosk mode). When unset, the app stays on the dashboard; use the "Open Neuroion" button to open the Neuroion UI.
