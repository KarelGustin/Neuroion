//
//  NeuroionApp.swift
//  NeuroionApp
//
//  Neuroion iOS App Entry Point
//

import SwiftUI

@main
struct NeuroionApp: App {
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var authManager = AuthManager()

    var body: some Scene {
        WindowGroup {
            RootContent(authManager: authManager)
                .onAppear {
                    setTunnelProviderIfNeeded()
                    ConnectionManager.shared.refreshEffectiveConnection()
                    connectWebSocketIfAuthenticated(authManager: authManager)
                }
                .onChange(of: scenePhase) { _, newPhase in
                    if newPhase == .active {
                        ConnectionManager.shared.refreshEffectiveConnection()
                        connectWebSocketIfAuthenticated(authManager: authManager)
                        WebSocketService.shared.tryReconnectIfNeeded()
                    }
                }
        }
    }

    private func setTunnelProviderIfNeeded() {
        #if NEUROION_VPN_ENABLED
        ConnectionManager.shared.tunnelStatusProvider = VPNTunnelManager.shared
        ConnectionManager.shared.tunnelStartRequester = VPNTunnelManager.shared
        #endif
    }

    private func connectWebSocketIfAuthenticated(authManager: AuthManager) {
        guard authManager.isAuthenticated,
              let token = authManager.token, !token.isEmpty else { return }
        let baseURL = ConnectionManager.shared.effectiveBaseURL
        WebSocketService.shared.connect(baseURL: baseURL, token: token)
    }
}

private struct RootContent: View {
    @ObservedObject var authManager: AuthManager

    var body: some View {
        if authManager.isAuthenticated {
            TabView {
                ChatView()
                    .tabItem { Label("Chat", systemImage: "bubble.left.and.bubble.right") }
                AgendaView()
                    .tabItem { Label("Agenda", systemImage: "calendar") }
                SettingsView()
                    .tabItem { Label("Settings", systemImage: "gearshape") }
            }
            .environmentObject(authManager)
            .onChange(of: WebSocketService.shared.isConnected) { _, connected in
                if connected, let token = authManager.token, !token.isEmpty {
                    AgendaStore.shared.syncToServer(token: token)
                }
            }
        } else {
            PairingView()
                .environmentObject(authManager)
        }
    }
}
