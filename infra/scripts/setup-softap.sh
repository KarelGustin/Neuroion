#!/bin/bash
# Setup SoftAP configuration for Neuroion
# Installs and configures hostapd and dnsmasq

set -e

echo "Setting up SoftAP for Neuroion..."

# Install dependencies
if command -v apt-get &> /dev/null; then
    apt-get update
    apt-get install -y hostapd dnsmasq iptables
elif command -v yum &> /dev/null; then
    yum install -y hostapd dnsmasq iptables
else
    echo "Error: Package manager not found (apt-get or yum required)"
    exit 1
fi

# Enable IP forwarding
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
sysctl -p

# Configure hostapd
cat > /etc/default/hostapd <<EOF
DAEMON_CONF="/etc/hostapd/hostapd.conf"
EOF

# Enable services
systemctl enable hostapd
systemctl enable dnsmasq

echo "SoftAP setup complete."
