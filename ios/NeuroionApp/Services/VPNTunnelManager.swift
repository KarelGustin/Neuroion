//
//  VPNTunnelManager.swift
//  NeuroionApp
//
//  Manages the WireGuard VPN tunnel (Network Extension). Uses NETunnelProviderManager
//  to install and start the tunnel with config received at pairing.
//

import Combine
import Foundation
import NetworkExtension

/// Bundle ID of the Packet Tunnel Extension (add .NeuroionTunnel or your extension name).
private let tunnelExtensionBundleId = "com.neuroion.NeuroionOne.NeuroionTunnel"

/// App Group for sharing config between app and extension (must match capability in Xcode).
let neuroionVPNAppGroupId = "group.com.neuroion.NeuroionOne"

class VPNTunnelManager: ObservableObject, TunnelStatusProviding {
    static let shared = VPNTunnelManager()

    @Published private(set) var tunnelStatus: NEVPNStatus = .invalid
    @Published private(set) var isTunnelActive: Bool = false

    var isTunnelActivePublisher: AnyPublisher<Bool, Never> { $isTunnelActive.eraseToAnyPublisher() }

    private var manager: NETunnelProviderManager?
    private var statusObserver: NSObjectProtocol?

    private init() {
        loadManagerAndObserveStatus()
    }

    deinit {
        if let obs = statusObserver {
            NotificationCenter.default.removeObserver(obs)
        }
    }

    /// Load the saved tunnel manager and observe status changes.
    private func loadManagerAndObserveStatus() {
        NETunnelProviderManager.loadAllFromPreferences { [weak self] managers, error in
            guard let self = self else { return }
            if let error = error {
                NSLog("Neuroion VPN: load preferences error %@", error.localizedDescription)
                return
            }
            let matching = managers?.first { $0.protocolConfiguration?.providerBundleIdentifier == tunnelExtensionBundleId }
            DispatchQueue.main.async {
                self.manager = matching
                if let connection = matching?.connection {
                    self.tunnelStatus = connection.status
                    self.isTunnelActive = (connection.status == .connected)
                }
                self.observeStatus()
            }
        }
    }

    private func observeStatus() {
        statusObserver = NotificationCenter.default.addObserver(
            forName: .NEVPNStatusDidChange,
            object: nil,
            queue: .main
        ) { [weak self] note in
            guard let self = self,
                  let connection = note.object as? NEVPNConnection else { return }
            self.tunnelStatus = connection.status
            self.isTunnelActive = (connection.status == .connected)
        }
    }

    /// Save WireGuard config and create/update the tunnel manager. Call before startTunnel().
    func setConfiguration(wireguardConfig: String) {
        let proto = NETunnelProviderProtocol()
        proto.providerBundleIdentifier = tunnelExtensionBundleId
        proto.providerConfiguration = ["wireguard-config": wireguardConfig]
        proto.serverAddress = "10.66.66.1"

        let newManager = NETunnelProviderManager()
        newManager.protocolConfiguration = proto
        newManager.localizedDescription = "Neuroion Homebase"

        newManager.saveToPreferences { [weak self] error in
            if let error = error {
                NSLog("Neuroion VPN: save error %@", error.localizedDescription)
                return
            }
            DispatchQueue.main.async {
                self?.manager = newManager
                self?.loadManagerAndObserveStatus()
            }
        }
    }

    /// Start the VPN tunnel. Call setConfiguration first.
    func startTunnel() {
        guard let manager = manager else {
            NSLog("Neuroion VPN: no manager, call setConfiguration first")
            return
        }
        manager.loadFromPreferences { [weak self] error in
            if let error = error {
                NSLog("Neuroion VPN: load before start error %@", error.localizedDescription)
                return
            }
            do {
                try manager.connection.startVPNTunnel()
            } catch {
                NSLog("Neuroion VPN: start error %@", error.localizedDescription)
            }
        }
    }

    /// Stop the VPN tunnel.
    func stopTunnel() {
        manager?.connection.stopVPNTunnel()
    }

    /// Remove the tunnel configuration from the system (e.g. on unpair).
    func removeConfiguration() {
        manager?.removeFromPreferences { [weak self] _ in
            DispatchQueue.main.async {
                self?.manager = nil
                self?.tunnelStatus = .invalid
                self?.isTunnelActive = false
            }
        }
    }
}

extension VPNTunnelManager: TunnelStartRequesting {
    /// Called by ConnectionManager when auto-connection finds local unreachable and VPN is preferred.
    func startTunnelIfConfigured() {
        guard manager != nil else { return }
        startTunnel()
    }
}
