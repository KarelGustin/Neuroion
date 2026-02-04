#!/bin/bash
# Setup mDNS (Avahi) for neuroion.local hostname

set -e

echo "Setting up mDNS for Neuroion..."

# Install avahi-daemon
if command -v apt-get &> /dev/null; then
    apt-get update
    apt-get install -y avahi-daemon avahi-utils
elif command -v yum &> /dev/null; then
    yum install -y avahi avahi-tools
else
    echo "Error: Package manager not found (apt-get or yum required)"
    exit 1
fi

# Set hostname
hostnamectl set-hostname neuroion

# Configure Avahi service
cat > /etc/avahi/services/neuroion.service <<EOF
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">Neuroion</name>
  <service>
    <type>_http._tcp</type>
    <port>8000</port>
    <txt-record>path=/</txt-record>
  </service>
</service-group>
EOF

# Enable and start Avahi
systemctl enable avahi-daemon
systemctl restart avahi-daemon

echo "mDNS setup complete. Device accessible at http://neuroion.local"
