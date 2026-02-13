//
//  ConnectionManager.swift
//  NeuroionApp
//
//  Manages Homebase URL and persistence for deployment on device.
//

import Combine
import Foundation

private let baseURLKey = "neuroion_base_url"
private let remoteBaseURLKey = "neuroion_remote_base_url"
private let useRemoteURLKey = "neuroion_use_remote_url"
private let defaultBaseURL = "http://localhost:8000"

class ConnectionManager: ObservableObject {
    static let shared = ConnectionManager()
    
    @Published var baseURL: String {
        didSet {
            let trimmed = baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
            UserDefaults.standard.set(trimmed.isEmpty ? defaultBaseURL : trimmed, forKey: baseURLKey)
        }
    }
    
    /// Optional remote Homebase URL (e.g. Tailscale) for use when away from home.
    @Published var remoteBaseURL: String {
        didSet {
            UserDefaults.standard.set(remoteBaseURL, forKey: remoteBaseURLKey)
        }
    }
    
    /// When true, use remoteBaseURL for API requests (e.g. when on 4G).
    @Published var useRemoteURL: Bool {
        didSet {
            UserDefaults.standard.set(useRemoteURL, forKey: useRemoteURLKey)
        }
    }
    
    init() {
        let stored = UserDefaults.standard.string(forKey: baseURLKey)
        self.baseURL = stored ?? defaultBaseURL
        self.remoteBaseURL = UserDefaults.standard.string(forKey: remoteBaseURLKey) ?? ""
        self.useRemoteURL = UserDefaults.standard.bool(forKey: useRemoteURLKey)
    }
    
    /// URL to use for API requests (no trailing slash). Uses remote URL when useRemoteURL is true and remoteBaseURL is non-empty.
    var effectiveBaseURL: String {
        if useRemoteURL {
            let remote = remoteBaseURL.trimmingCharacters(in: .whitespacesAndNewlines)
            if !remote.isEmpty {
                return remote.hasSuffix("/") ? String(remote.dropLast()) : remote
            }
        }
        let url = baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        if url.isEmpty { return defaultBaseURL }
        return url.hasSuffix("/") ? String(url.dropLast()) : url
    }
}
