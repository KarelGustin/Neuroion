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
                }
                .onChange(of: scenePhase) { _, newPhase in
                    if newPhase == .active {
                        ConnectionManager.shared.refreshEffectiveConnection()
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
        } else {
            PairingView()
                .environmentObject(authManager)
        }
    }
}
