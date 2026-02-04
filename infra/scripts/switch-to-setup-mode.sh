#!/bin/bash
# Switch Neuroion to Setup Mode (SoftAP)
# This script starts hostapd and dnsmasq for SoftAP with captive portal

set -e

WIFI_INTERFACE="${WIFI_INTERFACE:-wlan0}"
SOFTAP_SSID="${SOFTAP_SSID:-Neuroion-Setup}"
SOFTAP_PASSWORD="${SOFTAP_PASSWORD:-neuroion123}"
SOFTAP_IP="192.168.4.1"

echo "Switching to Setup Mode (SoftAP)..."

# Stop normal mode services
systemctl stop neuroion-normal-mode 2>/dev/null || true
systemctl stop wpa_supplicant 2>/dev/null || true
systemctl stop NetworkManager 2>/dev/null || true

# Configure static IP for SoftAP
ip addr flush dev "$WIFI_INTERFACE" 2>/dev/null || true
ip addr add "$SOFTAP_IP/24" dev "$WIFI_INTERFACE" 2>/dev/null || true
ip link set "$WIFI_INTERFACE" up

# Configure hostapd
cat > /etc/hostapd/hostapd.conf <<EOF
interface=$WIFI_INTERFACE
driver=nl80211
ssid=$SOFTAP_SSID
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$SOFTAP_PASSWORD
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

# Configure dnsmasq for captive portal
cat > /etc/dnsmasq.d/neuroion-setup.conf <<EOF
interface=$WIFI_INTERFACE
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
dhcp-option=3,192.168.4.1
dhcp-option=6,192.168.4.1
server=8.8.8.8
address=/#/192.168.4.1
EOF

# Start services
systemctl restart dnsmasq
systemctl restart hostapd

echo "Setup Mode (SoftAP) activated. SSID: $SOFTAP_SSID"
