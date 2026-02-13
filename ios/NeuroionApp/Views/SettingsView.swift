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
                    TextField("Remote Homebase URL", text: $connectionManager.remoteBaseURL)
                        .keyboardType(.URL)
                        .autocapitalization(.none)
                        .autocorrectionDisabled()
                    Toggle("Use remote connection", isOn: $connectionManager.useRemoteURL)
                } header: {
                    Text("Connection")
                } footer: {
                    Text("Homebase URL: your Pi on local Wi‑Fi (e.g. http://192.168.1.1:8000). Remote URL: use when away (e.g. Tailscale: http://neuroion-pi:8000). Turn on \"Use remote connection\" when not at home.")
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
        isPairing = true

        Task {
            do {
                let deviceId = UIDevice.current.identifierForVendor?.uuidString ?? UUID().uuidString
                try await authManager.pair(deviceId: deviceId, pairingCode: payload.pairingCode)
                await MainActor.run { isPairing = false }
            } catch {
                await MainActor.run {
                    pairingError = error.localizedDescription
                    isPairing = false
                }
            }
        }
    }
}
