#!/bin/bash
# Switch Neuroion to Setup Mode (SoftAP)
# Prefers NetworkManager (nmcli) on Bookworm/Pi 5; falls back to hostapd + dnsmasq

set -e

WIFI_INTERFACE="${WIFI_INTERFACE:-wlan0}"
SOFTAP_SSID="${SOFTAP_SSID:-Neuroion-Core wizard}"
SOFTAP_PASSWORD="${SOFTAP_PASSWORD:-neuroion123}"
SOFTAP_IP="192.168.4.1"
# Connection name for nmcli path (used by switch-to-normal-mode.sh to bring AP down)
NEUROION_AP_CON="Neuroion-Setup"

echo "Switching to Setup Mode (SoftAP)..."

# Prefer nmcli hotspot when available (Pi 5/Bookworm). Do NOT fall back to hostapd after nmcli
# failure, or we would stop NetworkManager and often have no working AP.
if command -v nmcli &>/dev/null; then
  # Ensure NetworkManager is running so nmcli can create the hotspot
  systemctl start NetworkManager 2>/dev/null || true
  if systemctl is-active NetworkManager &>/dev/null; then
    nmcli connection delete "$NEUROION_AP_CON" 2>/dev/null || true
    if nmcli device wifi hotspot ifname "$WIFI_INTERFACE" con-name "$NEUROION_AP_CON" ssid "$SOFTAP_SSID" password "$SOFTAP_PASSWORD"; then
      echo "Setup Mode (SoftAP) activated via NetworkManager. SSID: $SOFTAP_SSID"
      echo "Setup UI: http://10.42.0.1:3000 (or scan QR on kiosk)"
      exit 0
    fi
    echo "Error: nmcli hotspot failed (check: WiFi country in raspi-config, rfkill unblock wifi). NetworkManager left running." >&2
    exit 1
  fi
fi

# Hostapd path: only when nmcli not available. Stop NetworkManager and use hostapd + dnsmasq
systemctl stop neuroion-normal-mode 2>/dev/null || true
systemctl stop wpa_supplicant 2>/dev/null || true
systemctl stop NetworkManager 2>/dev/null || true

# Configure static IP for SoftAP
ip addr flush dev "$WIFI_INTERFACE" 2>/dev/null || true
ip addr add "$SOFTAP_IP/24" dev "$WIFI_INTERFACE" 2>/dev/null || true
ip link set "$WIFI_INTERFACE" up

# Configure hostapd (ensure dir exists so we don't fail silently)
mkdir -p /etc/hostapd
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
