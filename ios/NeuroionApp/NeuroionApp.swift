//
//  NeuroionApp.swift
//  NeuroionApp
//
//  Neuroion iOS App Entry Point
//

import SwiftUI

@main
struct NeuroionApp: App {
    @StateObject private var authManager = AuthManager()
    
    var body: some Scene {
        WindowGroup {
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
}
