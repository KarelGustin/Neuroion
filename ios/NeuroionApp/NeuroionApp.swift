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
                ChatView()
                    .environmentObject(authManager)
            } else {
                PairingView()
                    .environmentObject(authManager)
            }
        }
    }
}
