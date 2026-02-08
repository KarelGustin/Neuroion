#!/bin/bash
# Switch Neuroion to Normal Mode (LAN)
# This script stops SoftAP (hostapd or nmcli) and restores WiFi

set -e

WIFI_INTERFACE="${WIFI_INTERFACE:-wlan0}"
NEUROION_AP_CON="Neuroion-Setup"

echo "Switching to Normal Mode (LAN)..."

# If we used nmcli hotspot, bring the AP connection down first
if command -v nmcli &>/dev/null; then
  nmcli connection down "$NEUROION_AP_CON" 2>/dev/null || true
fi

# Stop hostapd-based SoftAP services
systemctl stop hostapd 2>/dev/null || true
systemctl stop dnsmasq 2>/dev/null || true
systemctl stop neuroion-setup-mode 2>/dev/null || true

# Remove SoftAP configuration (hostapd path)
rm -f /etc/dnsmasq.d/neuroion-setup.conf

# Restart network services
systemctl restart NetworkManager 2>/dev/null || true
systemctl restart wpa_supplicant 2>/dev/null || true

# Wait for WiFi connection
sleep 5

echo "Normal Mode (LAN) activated."
