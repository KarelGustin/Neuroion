#!/bin/bash
# Switch Neuroion to Normal Mode (LAN)
# This script stops SoftAP and connects to configured WiFi

set -e

WIFI_INTERFACE="${WIFI_INTERFACE:-wlan0}"

echo "Switching to Normal Mode (LAN)..."

# Stop SoftAP services
systemctl stop hostapd 2>/dev/null || true
systemctl stop dnsmasq 2>/dev/null || true
systemctl stop neuroion-setup-mode 2>/dev/null || true

# Remove SoftAP configuration
rm -f /etc/dnsmasq.d/neuroion-setup.conf

# Restart network services
systemctl restart NetworkManager 2>/dev/null || true
systemctl restart wpa_supplicant 2>/dev/null || true

# Wait for WiFi connection
sleep 5

echo "Normal Mode (LAN) activated."
