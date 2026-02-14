#!/usr/bin/env bash
# Add a WireGuard peer and output client config.
# Usage: WIREGUARD_CONFIG=/etc/wireguard/wg0.conf WIREGUARD_ENDPOINT=host:51820 [DEVICE_ID=optional] ./wireguard-add-peer.sh
# Outputs JSON to stdout: {"client_config": "...", "client_ip": "10.66.66.x", "client_public_key": "..."}
# Requires: wg (wireguard-tools), jq

set -e

CONFIG="${WIREGUARD_CONFIG:-/etc/wireguard/wg0.conf}"
ENDPOINT="${WIREGUARD_ENDPOINT:-}"
DEVICE_ID="${DEVICE_ID:-}"

if [[ -z "$ENDPOINT" ]]; then
  echo '{"error": "WIREGUARD_ENDPOINT (host:port) is required"}' >&2
  exit 1
fi

if [[ ! -f "$CONFIG" ]]; then
  echo "{\"error\": \"Config file not found: $CONFIG\"}" >&2
  exit 1
fi

# Generate client keypair
CLIENT_PRIVATE=$(wg genkey)
CLIENT_PUBLIC=$(echo -n "$CLIENT_PRIVATE" | wg pubkey)

# Read server public key from config (Interface section has PrivateKey; we need PublicKey)
# So we need the server's public key. Common practice: store server public in env or derive from private in config.
SERVER_PRIVATE=$(awk '/^\[Interface\]/{f=1;next} /^\[/{f=0} f && /^PrivateKey *=/{print $3; exit}' "$CONFIG")
if [[ -z "$SERVER_PRIVATE" ]]; then
  echo '{"error": "Could not read server PrivateKey from config"}' >&2
  exit 1
fi
SERVER_PUBLIC=$(echo -n "$SERVER_PRIVATE" | wg pubkey)

# Find next free client IP (10.66.66.2 .. 10.66.66.254)
USED_IPS=$(awk '/AllowedIPs/ { gsub(/.*=.*10\.66\.66\./, ""); gsub(/\/.*/, ""); if ($0 != "" && $0+0 >= 2 && $0+0 <= 254) print "10.66.66."$0 }' "$CONFIG" 2>/dev/null || true)
for i in $(seq 2 254); do
  IP="10.66.66.$i"
  if ! echo "$USED_IPS" | grep -q "^${IP}$"; then
    CLIENT_IP="$IP"
    break
  fi
done

if [[ -z "$CLIENT_IP" ]]; then
  echo '{"error": "No free client IP in 10.66.66.0/24"}' >&2
  exit 1
fi

# Append peer to config (persist across reboot)
PEER_BLOCK="
[Peer]
PublicKey = $CLIENT_PUBLIC
AllowedIPs = ${CLIENT_IP}/32
"
echo "$PEER_BLOCK" >> "$CONFIG"

# Apply peer live (so no need to restart wg0)
if command -v wg &>/dev/null; then
  wg set wg0 peer "$CLIENT_PUBLIC" allowed-ips "${CLIENT_IP}/32" 2>/dev/null || true
fi

# Build client config (split tunnel: only 10.66.66.0/24 through VPN)
CLIENT_CONFIG="[Interface]
PrivateKey = $CLIENT_PRIVATE
Address = ${CLIENT_IP}/32
DNS = 10.66.66.1

[Peer]
PublicKey = $SERVER_PUBLIC
Endpoint = $ENDPOINT
AllowedIPs = 10.66.66.0/24
PersistentKeepalive = 25
"

# Output JSON (escape newlines in config for JSON)
CONFIG_ESC=$(echo "$CLIENT_CONFIG" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || echo "\"$(echo "$CLIENT_CONFIG" | sed 's/\\/\\\\/g; s/"/\\"/g; s/$/\\n/' | tr -d '\n' | sed 's/\\n$//')\"")
if command -v jq &>/dev/null; then
  jq -n --arg config "$CLIENT_CONFIG" --arg ip "$CLIENT_IP" --arg pubkey "$CLIENT_PUBLIC" '{client_config: $config, client_ip: $ip, client_public_key: $pubkey}'
else
  echo "{\"client_config\": $CONFIG_ESC, \"client_ip\": \"$CLIENT_IP\", \"client_public_key\": \"$CLIENT_PUBLIC\"}"
fi
