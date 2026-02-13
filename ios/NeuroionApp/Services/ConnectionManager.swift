//
//  ConnectionManager.swift
//  NeuroionApp
//
//  Manages Homebase URL and persistence for deployment on device.
//

import Combine
import Foundation

private let baseURLKey = "neuroion_base_url"
private let defaultBaseURL = "http://localhost:8000"

class ConnectionManager: ObservableObject {
    static let shared = ConnectionManager()
    
    @Published var baseURL: String {
        didSet {
            let trimmed = baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
            UserDefaults.standard.set(trimmed.isEmpty ? defaultBaseURL : trimmed, forKey: baseURLKey)
        }
    }
    
    init() {
        let stored = UserDefaults.standard.string(forKey: baseURLKey)
        self.baseURL = stored ?? defaultBaseURL
    }
    
    /// URL to use for API requests (no trailing slash).
    var effectiveBaseURL: String {
        let url = baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        if url.isEmpty { return defaultBaseURL }
        return url.hasSuffix("/") ? String(url.dropLast()) : url
    }
}
