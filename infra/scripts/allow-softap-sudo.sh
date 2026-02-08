#!/bin/bash
# One-time setup: allow running the Neuroion SoftAP (setup mode) script without sudo password.
# Run from repo root: sudo ./infra/scripts/allow-softap-sudo.sh
# Then 'npm run dev' can start the hotspot on Pi 5.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SETUP_SCRIPT="$SCRIPT_DIR/switch-to-setup-mode.sh"
NORMAL_SCRIPT="$SCRIPT_DIR/switch-to-normal-mode.sh"
INSTALLED_SETUP="/usr/local/bin/neuroion-switch-to-setup-mode.sh"
INSTALLED_NORMAL="/usr/local/bin/neuroion-switch-to-normal-mode.sh"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: sudo $0"
  exit 1
fi

if [ ! -f "$SETUP_SCRIPT" ] || [ ! -f "$NORMAL_SCRIPT" ]; then
  echo "Error: switch-to-setup-mode.sh or switch-to-normal-mode.sh not found. Run from repo root."
  exit 1
fi

echo "Installing Neuroion SoftAP scripts for passwordless start/stop..."
cp "$SETUP_SCRIPT" "$INSTALLED_SETUP"
cp "$NORMAL_SCRIPT" "$INSTALLED_NORMAL"
chmod +x "$INSTALLED_SETUP" "$INSTALLED_NORMAL"

SUDOERS_FILE="/etc/sudoers.d/neuroion-softap"
echo "Adding sudoers rules (scripts + NetworkManager restore on Ctrl+C)..."
{
  echo "# Neuroion SoftAP: switch scripts and restore WiFi on exit"
  echo "%sudo ALL=(ALL) NOPASSWD: $INSTALLED_SETUP"
  echo "%sudo ALL=(ALL) NOPASSWD: $INSTALLED_NORMAL"
  echo "%sudo ALL=(ALL) NOPASSWD: /usr/bin/systemctl start NetworkManager"
  echo "%sudo ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart NetworkManager"
} > "$SUDOERS_FILE"
chmod 440 "$SUDOERS_FILE"

echo "Done. You can now run 'npm run dev' and the hotspot will start (connect to 'Neuroion-Core wizard', then open http://neuroion.core:3000)."
exit 0
