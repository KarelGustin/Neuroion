#!/bin/bash
# Neuroion Installation Script
# Supports Raspberry Pi 5, Jetson Nano, and Mac (demo)

set -e

PLATFORM="${1:-auto}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Neuroion Installation Script"
echo "============================"

# Detect platform if auto
if [ "$PLATFORM" = "auto" ]; then
    if [ -f "/proc/device-tree/model" ]; then
        MODEL=$(cat /proc/device-tree/model | tr '\0' '\n')
        if echo "$MODEL" | grep -qi "raspberry"; then
            PLATFORM="raspberry_pi"
        elif echo "$MODEL" | grep -qi "jetson"; then
            PLATFORM="jetson"
        else
            PLATFORM="linux"
        fi
    elif [ "$(uname)" = "Darwin" ]; then
        PLATFORM="macos"
    else
        PLATFORM="linux"
    fi
fi

echo "Detected platform: $PLATFORM"

# Install system dependencies
if [ "$PLATFORM" != "macos" ]; then
    echo "Installing system dependencies..."
    
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y \
            python3 python3-pip python3-venv \
            hostapd dnsmasq avahi-daemon avahi-utils \
            nginx nodejs npm \
            sqlite3
    elif command -v yum &> /dev/null; then
        sudo yum install -y \
            python3 python3-pip \
            hostapd dnsmasq avahi avahi-tools \
            nginx nodejs npm \
            sqlite
    fi
fi

# Install Python dependencies
echo "Installing Python dependencies..."
cd "$PROJECT_ROOT"
python3 -m venv venv || true
source venv/bin/activate || true
pip install -r neuroion/core/requirements.txt

# Install Node.js dependencies and build UIs
echo "Building setup UI..."
cd "$PROJECT_ROOT/apps/setup-ui"
npm install
npm run build

echo "Building touchscreen UI..."
cd "$PROJECT_ROOT/apps/touchscreen-ui"
npm install
npm run build

echo "Building Next.js dashboard..."
cd "$PROJECT_ROOT/apps/dashboard"
npm install
npm run build

# Install systemd services (Linux only)
if [ "$PLATFORM" != "macos" ]; then
    echo "Installing systemd services..."
    
    # Copy service files
    sudo cp "$SCRIPT_DIR/../systemd/neuroion-setup-mode.service" /etc/systemd/system/
    sudo cp "$SCRIPT_DIR/../systemd/neuroion-normal-mode.service" /etc/systemd/system/
    
    # Copy scripts (names expected by systemd and dev-softap.js)
    sudo cp "$SCRIPT_DIR/switch-to-setup-mode.sh" /usr/local/bin/neuroion-switch-to-setup-mode.sh
    sudo cp "$SCRIPT_DIR/switch-to-normal-mode.sh" /usr/local/bin/neuroion-switch-to-normal-mode.sh
    sudo cp "$SCRIPT_DIR/switch-network-mode.sh" /usr/local/bin/neuroion-switch-network-mode.sh
    sudo chmod +x /usr/local/bin/neuroion-switch-*.sh /usr/local/bin/neuroion-switch-network-mode.sh
    
    # Setup SoftAP
    sudo "$SCRIPT_DIR/setup-softap.sh"
    
    # Setup mDNS
    sudo "$SCRIPT_DIR/setup-mdns.sh"
    
    # Reload systemd and enable setup mode for first boot (no WiFi configured => start in AP)
    sudo systemctl daemon-reload
    sudo systemctl enable neuroion-setup-mode
fi

echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "1. Configure Neuroion by running: python3 -m neuroion.core.main"
echo "2. On first boot, device will start in Setup Mode (SoftAP)"
echo "3. Connect to 'Neuroion-Setup' WiFi network"
echo "4. Complete setup via captive portal"
echo "5. Device will switch to Normal Mode (LAN) after setup"
