# Neuroion Setup UI

React-based setup UI for Neuroion Homebase pairing. Designed to run in kiosk mode on HDMI displays.

## Features

- Pairing QR code display
- System status monitoring
- Fullscreen kiosk mode support

## Development

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
```

## Docker

See `Dockerfile` for containerized deployment.

## Configuration

Set `VITE_API_URL` environment variable to point to your Homebase API:

```bash
VITE_API_URL=http://localhost:8000 npm run dev
```
