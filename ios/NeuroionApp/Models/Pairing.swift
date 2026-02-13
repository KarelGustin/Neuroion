//
//  Pairing.swift
//  NeuroionApp
//
//  Pairing models
//

import Combine
import Foundation
import UIKit

struct PairStartRequest: Codable {
    let householdId: Int
    let deviceId: String
    let deviceType: String
    let name: String
}

struct PairStartResponse: Codable {
    let pairingCode: String
    let expiresInMinutes: Int
}

struct PairConfirmRequest: Codable {
    let pairingCode: String
    let deviceId: String
}

struct PairConfirmResponse: Codable {
    let token: String
    let householdId: Int
    let userId: Int
    let expiresInHours: Int
}

struct LocationEvent: Codable {
    let eventType: String
    let timestamp: Date?
    let metadata: [String: AnyCodable]?
}

struct HealthSummaryEvent: Codable {
    let sleepScore: Double?
    let recoveryLevel: String?
    let activityLevel: String?
    let summary: String
    let timestamp: Date?
    let metadata: [String: AnyCodable]?
}

struct EventRequest: Codable {
    let eventType: String
    let location: LocationEvent?
    let healthSummary: HealthSummaryEvent?
}

struct EventResponse: Codable {
    let success: Bool
    let snapshotId: Int
    let message: String
}

private let tokenKey = "neuroion_token"

// Auth Manager
class AuthManager: ObservableObject {
    @Published var isAuthenticated = false
    @Published var token: String?
    
    private let apiClient = APIClient.shared
    private let deviceId = UIDevice.current.identifierForVendor?.uuidString ?? UUID().uuidString
    
    init() {
        if let storedToken = UserDefaults.standard.string(forKey: tokenKey) {
            token = storedToken
            isAuthenticated = true
        }
    }
    
    func pair(deviceId: String, pairingCode: String) async throws {
        let request = PairConfirmRequest(
            pairingCode: pairingCode,
            deviceId: deviceId
        )
        
        let response: PairConfirmResponse = try await apiClient.request(
            endpoint: "/pair/confirm",
            method: "POST",
            body: request
        )
        
        await MainActor.run {
            self.token = response.token
            self.isAuthenticated = true
            UserDefaults.standard.set(response.token, forKey: tokenKey)
        }
    }
    
    func unpair() {
        token = nil
        isAuthenticated = false
        UserDefaults.standard.removeObject(forKey: tokenKey)
    }
    
}

struct ActionExecuteRequest: Codable {
    let actionId: Int
    enum CodingKeys: String, CodingKey { case actionId = "action_id" }
}

struct ActionExecuteResponse: Codable {
    let success: Bool
    let result: [String: AnyCodable]?
    let error: String?
}

// Chat Service
class ChatService {
    private let apiClient = APIClient.shared
    
    func sendMessage(message: String, token: String) async throws -> ChatResponse {
        let request = ChatRequest(message: message, conversationHistory: nil)
        
        return try await apiClient.request(
            endpoint: "/chat",
            method: "POST",
            body: request,
            token: token
        )
    }
    
    func executeAction(actionId: Int, token: String) async throws -> ActionExecuteResponse {
        let request = ActionExecuteRequest(actionId: actionId)
        
        return try await apiClient.request(
            endpoint: "/chat/actions/execute",
            method: "POST",
            body: request,
            token: token
        )
    }
}
