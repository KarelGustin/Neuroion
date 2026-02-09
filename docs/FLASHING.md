# Flashing Neuroion OS Image

This document describes how to package and deploy the Neuroion appliance as a pre‑built OS image for Raspberry Pi.

## 1. Build a Pre‑flashed SD Image

We use a pi‑gen pipeline to produce a single `.img` that includes:

- Raspberry Pi OS base
- Neuroion gateway & API services installed
- Setup UI and kiosk scripts (auto‑start)
- Preconfigured systemd service for `start-kiosk.sh`
- `neuroion onboard` wizard script (`neuroion-wizard.sh`) ready for non‑interactive CI
- Automatic hotspot setup for first‑run mobile onboarding
- Pre‑pulled Ollama 3.2 3b offline model included in the Neuroion image for immediate offline AI inference.

```bash
# From project root, using pi-gen subdirectory:
./infra/pi-gen/build.sh
#   → outputs: out/2026-02-09-neuroion-pi.img
```

## 2. Flash the Image onto microSD

Use `dd` or `balenaEtcher` to write the generated image:

```bash
sudo dd if=out/2026-02-09-neuroion-pi.img of=/dev/rdisk2 bs=4M conv=fsync
```

## 3. First‑boot Experience

1. Insert the flashed microSD into the Pi and power on (press the power button).
2. The Pi boots directly into kiosk mode:
   - **Before onboarding:** QR code for mobile onboarding wizard (HTTP hotspot).
   - **After onboarding:** Core dashboard UI in fullscreen.

## 4. Auto‑Recovery & Updates

- On network changes, hotspot and UI self‑heal automatically via systemd `neuroion-kiosk.service`.
- To apply a new image release, simply flash the updated `.img` and reboot.

---
*This guide ensures a seamless “plug & play” Neuroion OS experience for end users.*