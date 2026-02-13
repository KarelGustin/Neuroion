# Neuroion Touchscreen UI

Dashboard UI for the Neuroion touchscreen (runs on port 3001). **This is the screen shown in kiosk mode** on the device display; the kiosk startup script opens this UI (see `infra/kiosk/start-kiosk.sh`).

**Custom API port:** If the Neuroion API runs on a different port (e.g. `API_PORT=8001` in the repo root `.env`), add **`VITE_API_PORT=8001`** to the same root `.env`. This app loads env from the repo root when you run `npm run dev`.

## Environment

- **`VITE_NEUROION_AUTOLAUNCH`** – Set to `1` or `true` to auto-redirect to the Neuroion UI when the dashboard loads (e.g. for kiosk mode). When unset, the app stays on the dashboard; use the "Open Neuroion" button to open the Neuroion UI.
