# Neuroion VPN Tunnel (WireGuard)

This folder contains the **Packet Tunnel Extension** used for WireGuard VPN to the Homebase (10.66.66.1).

## Xcode setup

1. Add the WireGuard Swift package: **File → Add Package Dependencies** → enter `https://github.com/WireGuard/wireguard-apple` (or `https://git.zx2c4.com/wireguard-apple`), add product **WireGuardKit** to the app and to this extension target.
2. Create a new target: **File → New → Target** → **iOS → Packet Tunnel Extension**. Name it e.g. `NeuroionTunnel`. Set the bundle ID to `com.neuroion.NeuroionOne.NeuroionTunnel` (or your app bundle ID + `.NeuroionTunnel`).
3. Replace the generated `PacketTunnelProvider.swift` with the one in this folder (or add this folder’s files to the extension target).
4. Set the extension’s **Info.plist** to use `NeuroionTunnel/Info.plist` if you use the one in this folder.
5. Enable **App Groups** for both the main app and the extension (e.g. `group.com.neuroion.NeuroionOne`) and use the same ID in `VPNTunnelManager.swift` (`neuroionVPNAppGroupId`).
6. If WireGuardKit’s API differs (e.g. `TunnelConfiguration` or `WireGuardAdapter`), adjust `PacketTunnelProvider.swift` to match the version you added.

The main app’s `VPNTunnelManager` uses the extension’s bundle ID to create and start the tunnel; keep `tunnelExtensionBundleId` in `VPNTunnelManager.swift` in sync with the extension target’s bundle ID.
