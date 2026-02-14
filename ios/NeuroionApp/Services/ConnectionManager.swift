//
//  ConnectionManager.swift
//  NeuroionApp
//
//  Manages Homebase URL and persistence for deployment on device.
//  When "Automatic connection" is on: same WiFi (local reachable) → local URL; 4G/other → tunnel or remote.
//

import Combine
import Foundation
import Network

private let baseURLKey = "neuroion_base_url"
private let remoteBaseURLKey = "neuroion_remote_base_url"
private let useRemoteURLKey = "neuroion_use_remote_url"
private let useVPNBaseURLKey = "neuroion_use_vpn_base_url"
private let useAutoConnectionKey = "neuroion_use_auto_connection"
private let defaultBaseURL = "http://localhost:8000"

/// Fixed VPN base URL when WireGuard tunnel is active (unit is 10.66.66.1).
let neuroionVPNBaseURL = "https://10.66.66.1"

/// Health check path (no auth required).
private let healthPath = "/health"

/// How long to consider local reachability cache valid.
private let localReachabilityCacheInterval: TimeInterval = 45

/// Timeout for local reachability check.
private let localReachabilityTimeout: TimeInterval = 2.0

/// Provides tunnel active status so ConnectionManager does not depend on VPNTunnelManager directly (allows building without the VPN extension in the target).
protocol TunnelStatusProviding: AnyObject {
    var isTunnelActive: Bool { get }
    var isTunnelActivePublisher: AnyPublisher<Bool, Never> { get }
}

/// Called when auto-connection prefers tunnel but tunnel is not active (e.g. app can start it).
protocol TunnelStartRequesting: AnyObject {
    func startTunnelIfConfigured()
}

class ConnectionManager: ObservableObject {
    static let shared = ConnectionManager()

    @Published var baseURL: String {
        didSet {
            let trimmed = baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
            UserDefaults.standard.set(trimmed.isEmpty ? defaultBaseURL : trimmed, forKey: baseURLKey)
            invalidateLocalReachability()
        }
    }

    /// Optional remote Homebase URL (e.g. Tailscale) for use when away from home.
    @Published var remoteBaseURL: String {
        didSet {
            UserDefaults.standard.set(remoteBaseURL, forKey: remoteBaseURLKey)
        }
    }

    /// When true, use remoteBaseURL for API requests (manual mode only).
    @Published var useRemoteURL: Bool {
        didSet {
            UserDefaults.standard.set(useRemoteURL, forKey: useRemoteURLKey)
        }
    }

    /// When true and the VPN tunnel is active, effectiveBaseURL is https://10.66.66.1 (manual mode). In auto mode, tunnel is used when local is unreachable.
    @Published var useVPNBaseURL: Bool {
        didSet {
            UserDefaults.standard.set(useVPNBaseURL, forKey: useVPNBaseURLKey)
        }
    }

    /// When true, connection is chosen automatically: local URL if reachable (same WiFi), otherwise tunnel or remote.
    @Published var useAutoConnection: Bool {
        didSet {
            UserDefaults.standard.set(useAutoConnection, forKey: useAutoConnectionKey)
            if useAutoConnection {
                refreshEffectiveConnection()
            } else {
                invalidateLocalReachability()
            }
            objectWillChange.send()
        }
    }

    /// Cached result of last local reachability check. Nil = not yet checked or invalidated.
    @Published private(set) var localReachable: Bool?

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

    /// Set by the app so ConnectionManager can request tunnel start when auto mode and local unreachable (e.g. VPNTunnelManager.shared).
    weak var tunnelStartRequester: TunnelStartRequesting?

    private var cancellables = Set<AnyCancellable>()
    private var lastLocalCheckTime: Date?
    private var pathMonitor: NWPathMonitor?
    private let monitorQueue = DispatchQueue(label: "neuroion.connection.monitor")

    init() {
        let stored = UserDefaults.standard.string(forKey: baseURLKey)
        self.baseURL = stored ?? defaultBaseURL
        self.remoteBaseURL = UserDefaults.standard.string(forKey: remoteBaseURLKey) ?? ""
        self.useRemoteURL = UserDefaults.standard.bool(forKey: useRemoteURLKey)
        self.useVPNBaseURL = UserDefaults.standard.bool(forKey: useVPNBaseURLKey)
        self.useAutoConnection = UserDefaults.standard.object(forKey: useAutoConnectionKey) as? Bool ?? true
        startPathMonitoring()
    }

    deinit {
        pathMonitor?.cancel()
    }

    // MARK: - Effective URL (auto or manual)

    /// URL to use for API requests (no trailing slash).
    /// Auto mode: local if reachable, else tunnel if active, else remote if set, else local.
    /// Manual mode: VPN URL if tunnel active and useVPNBaseURL, else remote if useRemoteURL, else base URL.
    var effectiveBaseURL: String {
        if useAutoConnection {
            return effectiveBaseURLAuto
        }
        return effectiveBaseURLManual
    }

    private var effectiveBaseURLManual: String {
        if useVPNBaseURL, let provider = tunnelStatusProvider, provider.isTunnelActive {
            return neuroionVPNBaseURL
        }
        if useRemoteURL {
            let remote = remoteBaseURL.trimmingCharacters(in: .whitespacesAndNewlines)
            if !remote.isEmpty {
                return remote.hasSuffix("/") ? String(remote.dropLast()) : remote
            }
        }
        return normalizedBaseURL
    }

    private var effectiveBaseURLAuto: String {
        let tunnelActive = tunnelStatusProvider?.isTunnelActive ?? false
        let remote = remoteBaseURL.trimmingCharacters(in: .whitespacesAndNewlines)

        if localReachable == true {
            return normalizedBaseURL
        }
        if tunnelActive {
            return neuroionVPNBaseURL
        }
        if !remote.isEmpty {
            return remote.hasSuffix("/") ? String(remote.dropLast()) : remote
        }
        return normalizedBaseURL
    }

    /// Human-readable label for current connection type (Local / Tunnel / Remote).
    var effectiveConnectionLabel: String {
        if useAutoConnection {
            if localReachable == true { return "Local" }
            if tunnelStatusProvider?.isTunnelActive == true { return "Tunnel" }
            let remote = remoteBaseURL.trimmingCharacters(in: .whitespacesAndNewlines)
            if !remote.isEmpty { return "Remote" }
            return "Local"
        }
        if useVPNBaseURL, tunnelStatusProvider?.isTunnelActive == true { return "Tunnel" }
        if useRemoteURL, !remoteBaseURL.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { return "Remote" }
        return "Local"
    }

    private var normalizedBaseURL: String {
        let url = baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        if url.isEmpty { return defaultBaseURL }
        return url.hasSuffix("/") ? String(url.dropLast()) : url
    }

    // MARK: - Local reachability

    private func invalidateLocalReachability() {
        DispatchQueue.main.async { [weak self] in
            self?.localReachable = nil
            self?.lastLocalCheckTime = nil
            self?.objectWillChange.send()
        }
    }

    /// Call on app launch or when coming to foreground. Runs reachability check and updates effective URL; may request tunnel start when auto and local unreachable.
    func refreshEffectiveConnection() {
        guard useAutoConnection else {
            objectWillChange.send()
            return
        }
        Task {
            let reachable = await checkLocalReachability()
            await MainActor.run {
                self.localReachable = reachable
                self.lastLocalCheckTime = Date()
                self.objectWillChange.send()
                if !reachable, useVPNBaseURL, tunnelStatusProvider?.isTunnelActive != true {
                    tunnelStartRequester?.startTunnelIfConfigured()
                }
            }
        }
    }

    /// Returns whether the local base URL is reachable (e.g. same WiFi). Uses short timeout.
    /// For HTTP URLs with IPv4 hosts, uses NWConnection with IPv4-only to avoid iOS IPv6 synthesis
    /// failures (64:ff9b::/96) that cause "No network route" for private addresses.
    private func checkLocalReachability() async -> Bool {
        let urlString = normalizedBaseURL + healthPath
        guard let url = URL(string: urlString) else { return false }
        let host = url.host ?? ""
        let port = UInt16(url.port ?? (url.scheme == "https" ? 443 : 80))
        let path = url.path.isEmpty ? "/" : url.path
        let isHTTP = (url.scheme ?? "").lowercased() == "http"

        // Use IPv4-only path for HTTP when host looks like IPv4 to avoid failed IPv6 synthesis.
        if isHTTP, Self.isIPv4Host(host) {
            return await checkReachabilityIPv4(host: host, port: port, path: path)
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = localReachabilityTimeout
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse else { return false }
            return (200...399).contains(http.statusCode)
        } catch {
            return false
        }
    }

    private static func isIPv4Host(_ host: String) -> Bool {
        var addr = in_addr()
        return host.withCString { inet_pton(AF_INET, $0, &addr) == 1 }
    }

    /// HTTP GET reachability over TCP with IPv4-only to avoid NAT64 synthesis failures for private IPs.
    private func checkReachabilityIPv4(host: String, port: UInt16, path: String) async -> Bool {
        let params = NWParameters.tcp
        if let ipOpts = params.defaultProtocolStack.internetProtocol as? NWProtocolIP.Options {
            ipOpts.version = .v4
        }
        let endpoint = NWEndpoint.Host(host)
        let portEndpoint = NWEndpoint.Port(integerLiteral: port)
        let conn = NWConnection(to: .hostPort(host: endpoint, port: portEndpoint), using: params)

        return await withCheckedContinuation { continuation in
            let lock = NSLock()
            var didResume = false
            func finish(_ result: Bool) {
                lock.lock()
                defer { lock.unlock() }
                guard !didResume else { return }
                didResume = true
                conn.cancel()
                continuation.resume(returning: result)
            }

            let deadline = DispatchTime.now() + localReachabilityTimeout

            conn.stateUpdateHandler = { [weak conn] state in
                guard let conn = conn else { return }
                switch state {
                case .ready:
                    let request = "GET \(path) HTTP/1.1\r\nHost: \(host):\(port)\r\nConnection: close\r\n\r\n"
                    conn.send(content: request.data(using: .utf8), completion: .contentProcessed { _ in })
                    var buffer = Data()
                    conn.receive(minimumIncompleteLength: 1, maximumLength: 1024) { data, _, _, _ in
                        if let data = data { buffer.append(data) }
                        let ok = buffer.prefix(12).withUnsafeBytes { bytes in
                            guard let str = String(bytes: bytes, encoding: .ascii) else { return false }
                            return str.hasPrefix("HTTP/1.") && (str.contains(" 2") || str.contains(" 3"))
                        }
                        finish(ok)
                    }
                case .failed, .cancelled:
                    finish(false)
                case .waiting:
                    break
                default:
                    break
                }
            }
            conn.start(queue: monitorQueue)

            monitorQueue.asyncAfter(deadline: deadline) {
                finish(false)
            }
        }
    }

    /// Whether we should run a new reachability check (cache expired or never set).
    private var shouldRefreshReachability: Bool {
        guard useAutoConnection else { return false }
        if localReachable == nil { return true }
        guard let last = lastLocalCheckTime else { return true }
        return Date().timeIntervalSince(last) > localReachabilityCacheInterval
    }

    // MARK: - Path monitoring

    private func startPathMonitoring() {
        pathMonitor = NWPathMonitor()
        pathMonitor?.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                self?.invalidateLocalReachability()
                self?.refreshEffectiveConnection()
            }
        }
        pathMonitor?.start(queue: monitorQueue)
    }
}
