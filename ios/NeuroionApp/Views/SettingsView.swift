//
//  SettingsView.swift
//  NeuroionApp
//
//  App settings: Homebase URL, location/health toggles, unpair.
//

import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var authManager: AuthManager
    @ObservedObject private var connectionManager = ConnectionManager.shared
    @StateObject private var locationService = LocationService()
    @StateObject private var healthKitService = HealthKitService()
    @State private var showPairingScanner = false
    @State private var isPairing = false
    @State private var pairingError: String?

    var body: some View {
        NavigationView {
            Form {
                Section {
                    Button {
                        pairingError = nil
                        showPairingScanner = true
                    } label: {
                        Label("Connect to another Neuroion One", systemImage: "qrcode.viewfinder")
                    }
                    .disabled(isPairing)
                    if isPairing {
                        HStack {
                            ProgressView()
                                .scaleEffect(0.9)
                            Text("Koppelen…")
                                .foregroundColor(.secondary)
                        }
                    }
                    if let err = pairingError {
                        Text(err)
                            .font(.caption)
                            .foregroundColor(.red)
                    }
                } header: {
                    Text("Switch Homebase")
                } footer: {
                    Text("Scan de QR-code op het touchscreen of setup-scherm van een andere Neuroion One om met dat apparaat te koppelen.")
                }

                Section {
                    TextField("Homebase URL", text: $connectionManager.baseURL)
                        .keyboardType(.URL)
                        .autocapitalization(.none)
                        .autocorrectionDisabled()
                    TextField("Remote / VPN URL", text: $connectionManager.remoteBaseURL)
                        .keyboardType(.URL)
                        .autocapitalization(.none)
                        .autocorrectionDisabled()
                    Toggle("Use remote connection", isOn: $connectionManager.useRemoteURL)
                    Toggle("Use VPN tunnel", isOn: $connectionManager.useVPNBaseURL)
                    Text("In use: \(ConnectionManager.shared.effectiveBaseURL)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                } header: {
                    Text("Connection")
                } footer: {
                    Text("Homebase URL: local network (e.g. http://neuroion.local:8000). Remote/VPN URL: tunnel or Tailscale. \"Use VPN tunnel\" uses 10.66.66.1 when the tunnel is connected.")
                }
                
                Section("Location") {
                    Toggle("Track Location", isOn: $locationService.isEnabled)
                    if locationService.isEnabled {
                        Text("Sends arrival/departure events to Homebase")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
                
                Section("Health") {
                    Toggle("Share Health Summaries", isOn: $healthKitService.isEnabled)
                    if healthKitService.isEnabled {
                        Text("Only derived summaries are shared, never raw data")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
                
                Section("Account") {
                    Button("Unpair Device", role: .destructive) {
                        authManager.unpair()
                    }
                }
            }
            .navigationTitle("Settings")
            .sheet(isPresented: $showPairingScanner) {
                QRScannerView(
                    onScan: handleScannedPayload,
                    onCancel: { showPairingScanner = false }
                )
            }
        }
    }

    private func handleScannedPayload(_ payload: NeuroionPairQRPayload) {
        showPairingScanner = false
        pairingError = nil
        connectionManager.baseURL = payload.baseURL
        if payload.useVPN {
            connectionManager.remoteBaseURL = payload.vpnBaseURL ?? neuroionVPNBaseURL
            connectionManager.useVPNBaseURL = true
        }
        isPairing = true

        Task {
            do {
                let deviceId = UIDevice.current.identifierForVendor?.uuidString ?? UUID().uuidString
                let response = try await authManager.pair(
                    deviceId: deviceId,
                    pairingCode: payload.pairingCode,
                    includeVpn: payload.useVPN
                )
                await MainActor.run {
                    if payload.useVPN, let config = response.wireguardConfig, !config.isEmpty {
                        #if NEUROION_VPN_ENABLED
                        VPNTunnelManager.shared.setConfiguration(wireguardConfig: config)
                        VPNTunnelManager.shared.startTunnel()
                        #endif
                    }
                    isPairing = false
                }
            } catch {
                await MainActor.run {
                    pairingError = error.localizedDescription
                    isPairing = false
                }
            }
        }
    }
}
