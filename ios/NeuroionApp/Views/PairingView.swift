//
//  PairingView.swift
//  NeuroionApp
//
//  Device pairing interface
//

import SwiftUI

struct PairingView: View {
    @EnvironmentObject var authManager: AuthManager
    @State private var pairingCode = ""
    @State private var isPairing = false
    @State private var errorMessage: String?
    
    var body: some View {
        VStack(spacing: 24) {
            Image(systemName: "house.fill")
                .font(.system(size: 60))
                .foregroundColor(.blue)
            
            Text("Neuroion")
                .font(.largeTitle)
                .fontWeight(.bold)
            
            Text("Pair with your Homebase")
                .font(.subheadline)
                .foregroundColor(.secondary)
            
            VStack(spacing: 16) {
                TextField("Enter pairing code", text: $pairingCode)
                    .textFieldStyle(RoundedBorderTextFieldStyle())
                    .keyboardType(.numberPad)
                    .padding(.horizontal)
                
                Button(action: pairDevice) {
                    if isPairing {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle())
                    } else {
                        Text("Pair Device")
                            .frame(maxWidth: .infinity)
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(pairingCode.isEmpty || isPairing)
                .padding(.horizontal)
                
                if let error = errorMessage {
                    Text(error)
                        .font(.caption)
                        .foregroundColor(.red)
                        .padding(.horizontal)
                }
            }
            
            Spacer()
        }
        .padding()
    }
    
    private func pairDevice() {
        isPairing = true
        errorMessage = nil
        
        Task {
            do {
                let deviceId = UIDevice.current.identifierForVendor?.uuidString ?? UUID().uuidString
                try await authManager.pair(deviceId: deviceId, pairingCode: pairingCode)
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                    isPairing = false
                }
            }
        }
    }
}
