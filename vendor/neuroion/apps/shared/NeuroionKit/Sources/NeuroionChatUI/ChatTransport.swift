import Foundation

public enum NeuroionChatTransportEvent: Sendable {
    case health(ok: Bool)
    case tick
    case chat(NeuroionChatEventPayload)
    case agent(NeuroionAgentEventPayload)
    case seqGap
}

public protocol NeuroionChatTransport: Sendable {
    func requestHistory(sessionKey: String) async throws -> NeuroionChatHistoryPayload
    func sendMessage(
        sessionKey: String,
        message: String,
        thinking: String,
        idempotencyKey: String,
        attachments: [NeuroionChatAttachmentPayload]) async throws -> NeuroionChatSendResponse

    func abortRun(sessionKey: String, runId: String) async throws
    func listSessions(limit: Int?) async throws -> NeuroionChatSessionsListResponse

    func requestHealth(timeoutMs: Int) async throws -> Bool
    func events() -> AsyncStream<NeuroionChatTransportEvent>

    func setActiveSessionKey(_ sessionKey: String) async throws
}

extension NeuroionChatTransport {
    public func setActiveSessionKey(_: String) async throws {}

    public func abortRun(sessionKey _: String, runId _: String) async throws {
        throw NSError(
            domain: "NeuroionChatTransport",
            code: 0,
            userInfo: [NSLocalizedDescriptionKey: "chat.abort not supported by this transport"])
    }

    public func listSessions(limit _: Int?) async throws -> NeuroionChatSessionsListResponse {
        throw NSError(
            domain: "NeuroionChatTransport",
            code: 0,
            userInfo: [NSLocalizedDescriptionKey: "sessions.list not supported by this transport"])
    }
}
