//
//  SettingsView.swift
//  NeuroionApp
//
//  App settings and configuration
//

import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var authManager: AuthManager
    @StateObject private var locationService = LocationService()
    @StateObject private var healthKitService = HealthKitService()
    
    var body: some View {
        NavigationView {
            Form {
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
        }
    }
}
