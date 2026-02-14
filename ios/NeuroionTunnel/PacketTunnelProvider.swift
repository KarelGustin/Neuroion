//
//  PacketTunnelProvider.swift
//  NeuroionTunnel
//
//  WireGuard Packet Tunnel Extension. Requires WireGuardKit (Swift Package:
//  https://github.com/WireGuard/wireguard-apple, product WireGuardKit).
//  Add this file to a "Packet Tunnel Extension" target in Xcode and link WireGuardKit.
//

import NetworkExtension
import WireGuardKit

class PacketTunnelProvider: NEPacketTunnelProvider {

    private var adapter: WireGuardAdapter?

    override func startTunnel(options: [String: NSObject]?, completionHandler: @escaping (Error?) -> Void) {
        guard let protocolConfig = protocolConfiguration as? NETunnelProviderProtocol,
              let configString = protocolConfig.providerConfiguration?["wireguard-config"] as? String else {
            completionHandler(NSError(domain: "NeuroionTunnel", code: -1, userInfo: [NSLocalizedDescriptionKey: "Missing wireguard-config"]))
            return
        }

        guard let config = try? TunnelConfiguration(fromWgQuickConfig: configString) else {
            completionHandler(NSError(domain: "NeuroionTunnel", code: -2, userInfo: [NSLocalizedDescriptionKey: "Invalid WireGuard config"]))
            return
        }

        adapter = WireGuardAdapter(with: self)
        adapter?.start(tunnelConfiguration: config) { [weak self] error in
            if let error = error {
                completionHandler(error)
                return
            }
            completionHandler(nil)
        }
    }

    override func stopTunnel(with reason: NEProviderStopReason, completionHandler: @escaping () -> Void) {
        adapter?.stop { completionHandler() }
    }

    override func handleAppMessage(_ messageData: Data, completionHandler: ((Data?) -> Void)?) {
        completionHandler?(nil)
    }

    override func sleep(completionHandler: @escaping () -> Void) {
        adapter?.sleep(completionHandler: completionHandler)
    }

    override func wake() {
        adapter?.wake()
    }
}
