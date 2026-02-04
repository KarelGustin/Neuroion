#!/bin/bash
# Switch between Setup Mode (SoftAP) and Normal Mode (LAN)
# Usage: switch-network-mode.sh [setup|normal]

set -e

MODE="${1:-normal}"

if [ "$MODE" = "setup" ]; then
    echo "Switching to Setup Mode..."
    /usr/local/bin/neuroion-switch-to-setup-mode.sh
    systemctl start neuroion-setup-mode
    systemctl stop neuroion-normal-mode
elif [ "$MODE" = "normal" ]; then
    echo "Switching to Normal Mode..."
    /usr/local/bin/neuroion-switch-to-normal-mode.sh
    systemctl start neuroion-normal-mode
    systemctl stop neuroion-setup-mode
else
    echo "Usage: $0 [setup|normal]"
    exit 1
fi

echo "Network mode switched to: $MODE"
