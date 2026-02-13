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
    static let shared = ChatService()
    private let apiClient = APIClient.shared

    private init() {}

    /// Send message and wait for full response (can timeout on long research).
    func sendMessage(message: String, token: String) async throws -> ChatResponse {
        let request = ChatRequest(message: message, conversationHistory: nil)

        return try await apiClient.request(
            endpoint: "/chat",
            method: "POST",
            body: request,
            token: token
        )
    }

    /// Event yielded while streaming chat (status updates and final response).
    enum ChatStreamEvent {
        case status(String)
        case done(ChatResponse)
    }

    /// Stream chat: yields status updates then .done(response). Consume in a single Task to avoid Reporter disconnected.
    func sendMessageStreaming(message: String, token: String) -> AsyncThrowingStream<ChatStreamEvent, Error> {
        let request = ChatRequest(message: message, conversationHistory: nil)
        return AsyncThrowingStream { continuation in
            Task {
                do {
                    let stream = try await apiClient.streamEvents(
                        endpoint: "/chat/stream",
                        method: "POST",
                        body: request,
                        token: token
                    )
                    var lastMessage = ""
                    var lastActions: [ActionResponse] = []
                    for try await ev in stream {
                        guard let type = ev["type"] as? String else { continue }
                        switch type {
                        case "status":
                            if let text = ev["text"] as? String {
                                continuation.yield(.status(text))
                            }
                        case "tool_start":
                            if let tool = ev["tool"] as? String {
                                continuation.yield(.status("Bezig met \(tool)…"))
                            }
                        case "tool_done":
                            if let tool = ev["tool"] as? String {
                                continuation.yield(.status("\(tool) klaar. Volgende stap…"))
                            }
                        case "done":
                            if let err = ev["error"] as? String, !err.isEmpty {
                                lastMessage = NSLocalizedString("Er ging iets mis. Probeer het opnieuw.", comment: "Stream error")
                            } else {
                                lastMessage = ev["message"] as? String ?? ""
                            }
                            if let rawActions = ev["actions"] as? [[String: Any]] {
                                lastActions = rawActions.compactMap { dict in try? ActionResponse(from: dict) }
                            }
                            continuation.yield(.done(ChatResponse(message: lastMessage, reasoning: "", actions: lastActions)))
                        default:
                            break
                        }
                    }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
        }
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

extension ActionResponse {
    init(from dict: [String: Any]) throws {
        self.id = dict["id"] as? Int
        self.name = dict["name"] as? String ?? ""
        self.description = dict["description"] as? String ?? ""
        self.parameters = (dict["parameters"] as? [String: Any]).map { params in
            params.mapValues { AnyCodable($0) }
        } ?? [:]
        self.reasoning = dict["reasoning"] as? String ?? ""
    }
}
