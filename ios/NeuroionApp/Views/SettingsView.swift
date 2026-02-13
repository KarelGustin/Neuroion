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
    
    var body: some View {
        NavigationView {
            Form {
                Section {
                    TextField("Homebase URL", text: $connectionManager.baseURL)
                        .keyboardType(.URL)
                        .autocapitalization(.none)
                        .autocorrectionDisabled()
                } header: {
                    Text("Connection")
                } footer: {
                    Text("URL of your Neuroion Homebase (e.g. http://192.168.1.1:8000). Change only if your server address changed.")
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
        }
    }
}
