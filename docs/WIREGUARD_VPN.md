# WireGuard VPN + fixed IP 10.66.66.1

The Neuroion unit can act as a WireGuard server so the iOS app always connects to **https://10.66.66.1** over an encrypted tunnel. The app then never needs to know the home’s changing IP.

## Unit: WireGuard server

### Install WireGuard (Linux / Raspberry Pi)

```bash
sudo apt update
sudo apt install wireguard-tools
```

### Initial server config

Create `/etc/wireguard/wg0.conf` (or set `WIREGUARD_CONFIG` to your path):

```ini
[Interface]
Address = 10.66.66.1/24
ListenPort = 51820
PrivateKey = <server_private_key>

# Optional: allow forwarding for full tunnel
# PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
# PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
```

Generate server keys:

```bash
wg genkey | tee /tmp/server_private | wg pubkey > /tmp/server_public
# Put the private key in the [Interface] PrivateKey = ... line above.
```

Start WireGuard:

```bash
sudo wg-quick up wg0
# Enable on boot (systemd): sudo systemctl enable wg-quick@wg0
```

### Add peers (script)

The repo script adds a peer and prints the client config (JSON):

```bash
export WIREGUARD_CONFIG=/etc/wireguard/wg0.conf
export WIREGUARD_ENDPOINT=neuroion.local:51820   # or your unit's hostname/IP and port
./scripts/wireguard-add-peer.sh
```

Output: `{"client_config": "[Interface]...", "client_ip": "10.66.66.2", "client_public_key": "..."}`.

The API uses this (or the same logic) when issuing VPN config during pairing.

## Unit: HTTPS on 10.66.66.1

The iOS app requires HTTPS for 10.66.66.1 (App Transport Security). Two options:

### Option A: Reverse proxy (recommended)

Run a reverse proxy on the unit that listens on **10.66.66.1:443** (or on `0.0.0.0:443` so it also answers on the VPN interface) and proxies to `http://127.0.0.1:8000` (Neuroion API).

**Caddy** (self-signed cert for 10.66.66.1):

```bash
sudo apt install caddy
```

Create `/etc/caddy/Caddyfile`:

```
https://10.66.66.1 {
    tls internal
    reverse_proxy 127.0.0.1:8000
}
```

Then `sudo systemctl reload caddy`. Caddy’s `tls internal` generates a self-signed certificate. The iOS app should use **certificate pinning** for this host (see iOS section).

**Nginx** (self-signed):

```bash
sudo apt install nginx
sudo openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout /etc/ssl/private/neuroion-vpn.key \
  -out /etc/ssl/certs/neuroion-vpn.crt \
  -subj "/CN=10.66.66.1"
```

Server block listening on 443, `ssl_certificate` / `ssl_certificate_key` pointing to the above, and `proxy_pass http://127.0.0.1:8000;`.

### Option B: Uvicorn with SSL

Run the FastAPI app with SSL certificates bound to 10.66.66.1 (or 0.0.0.0). Possible but less flexible than a dedicated reverse proxy; not detailed here.

## Environment variables (unit)

| Variable | Description | Example |
|----------|-------------|---------|
| `WIREGUARD_VPN_CIDR` | VPN subnet | `10.66.66.0/24` |
| `VPN_SERVER_IP` | Unit’s VPN IP (used in responses) | `10.66.66.1` |
| `WIREGUARD_CONFIG` | Path to `wg0.conf` | `/etc/wireguard/wg0.conf` |
| `WIREGUARD_ENDPOINT` | Public endpoint for clients (host:port) | `neuroion.local:51820` |
| `WIREGUARD_ADD_PEER_SCRIPT` | Script that adds a peer and outputs JSON | `./scripts/wireguard-add-peer.sh` |

## iOS app

- Pair via QR; the API can return `wireguard_config` and `vpn_base_url: https://10.66.66.1`.
- The app installs the config, starts the WireGuard tunnel, and uses **https://10.66.66.1** as the base URL when the tunnel is active.
- Use **certificate pinning** for 10.66.66.1 (public key of the unit’s HTTPS cert).

## Revoke a peer

When a device is unpaired, the backend can remove the peer so that key can no longer connect:

- Remove the peer from `/etc/wireguard/wg0.conf` (the `[Peer]` block with that `PublicKey`).
- Apply: `sudo wg set wg0 peer <client_public_key> remove`.

The API exposes this via an endpoint (e.g. revoke by `device_id` or user).
