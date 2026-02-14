//
//  ConnectionManager.swift
//  NeuroionApp
//
//  Manages Homebase URL and persistence for deployment on device.
//

import Combine
import Foundation

private let baseURLKey = "neuroion_base_url"
private let remoteBaseURLKey = "neuroion_remote_base_url"
private let useRemoteURLKey = "neuroion_use_remote_url"
private let useVPNBaseURLKey = "neuroion_use_vpn_base_url"
private let defaultBaseURL = "http://localhost:8000"

/// Fixed VPN base URL when WireGuard tunnel is active (unit is 10.66.66.1).
let neuroionVPNBaseURL = "https://10.66.66.1"

/// Provides tunnel active status so ConnectionManager does not depend on VPNTunnelManager directly (allows building without the VPN extension in the target).
protocol TunnelStatusProviding: AnyObject {
    var isTunnelActive: Bool { get }
    var isTunnelActivePublisher: AnyPublisher<Bool, Never> { get }
}

class ConnectionManager: ObservableObject {
    static let shared = ConnectionManager()
    
    @Published var baseURL: String {
        didSet {
            let trimmed = baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
            UserDefaults.standard.set(trimmed.isEmpty ? defaultBaseURL : trimmed, forKey: baseURLKey)
        }
    }
    
    /// Optional remote Homebase URL (e.g. Tailscale) for use when away from home.
    @Published var remoteBaseURL: String {
        didSet {
            UserDefaults.standard.set(remoteBaseURL, forKey: remoteBaseURLKey)
        }
    }
    
    /// When true, use remoteBaseURL for API requests (e.g. when on 4G).
    @Published var useRemoteURL: Bool {
        didSet {
            UserDefaults.standard.set(useRemoteURL, forKey: useRemoteURLKey)
        }
    }
    
    /// When true and the VPN tunnel is active, effectiveBaseURL is https://10.66.66.1.
    @Published var useVPNBaseURL: Bool {
        didSet {
            UserDefaults.standard.set(useVPNBaseURL, forKey: useVPNBaseURLKey)
        }
    }
    
    /// Set by the app when VPN support is available (e.g. VPNTunnelManager.shared). Nil when VPN extension is not in the target.
    weak var tunnelStatusProvider: TunnelStatusProviding? {
        didSet {
            guard let provider = tunnelStatusProvider else { return }
            provider.isTunnelActivePublisher
                .receive(on: DispatchQueue.main)
                .sink { [weak self] _ in self?.objectWillChange.send() }
                .store(in: &cancellables)
        }
    }
    
    private var cancellables = Set<AnyCancellable>()

    init() {
        let stored = UserDefaults.standard.string(forKey: baseURLKey)
        self.baseURL = stored ?? defaultBaseURL
        self.remoteBaseURL = UserDefaults.standard.string(forKey: remoteBaseURLKey) ?? ""
        self.useRemoteURL = UserDefaults.standard.bool(forKey: useRemoteURLKey)
        self.useVPNBaseURL = UserDefaults.standard.bool(forKey: useVPNBaseURLKey)
    }
    
    /// URL to use for API requests (no trailing slash). When useVPNBaseURL is true and the WireGuard tunnel is connected, returns https://10.66.66.1. When tunnel is inactive, falls back to remote or local base URL (relay/discovery).
    var effectiveBaseURL: String {
        if useVPNBaseURL, let provider = tunnelStatusProvider, provider.isTunnelActive {
            return neuroionVPNBaseURL
        }
        if useRemoteURL {
            let remote = remoteBaseURL.trimmingCharacters(in: .whitespacesAndNewlines)
            if !remote.isEmpty {
                return remote.hasSuffix("/") ? String(remote.dropLast()) : remote
            }
        }
        let url = baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        if url.isEmpty { return defaultBaseURL }
        return url.hasSuffix("/") ? String(url.dropLast()) : url
    }
}
