//
//  WebSocketService.swift
//  NeuroionApp
//
//  WebSocket client for chat, heartbeat_ack, proactive messages, agenda_update.
//  Reconnect with exponential backoff. Prefer WebSocket when connected; fallback to HTTP/SSE.
//

import Combine
import Foundation

/// Incoming WebSocket frame (server -> client)
struct WSIncomingMessage {
    let type: String
    let payload: [String: Any]

    static func parse(_ data: Data) -> WSIncomingMessage? {
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = json["type"] as? String else { return nil }
        return WSIncomingMessage(type: type, payload: json)
    }
}

/// Delegate for WebSocket events (chat tokens, done, proactive, agenda_update)
protocol WebSocketServiceDelegate: AnyObject {
    func webSocket(_ service: WebSocketService, didReceiveChatToken text: String)
    func webSocket(_ service: WebSocketService, didReceiveChatDone message: String, actions: [[String: Any]], error: String?)
    func webSocket(_ service: WebSocketService, didReceiveChatError error: String)
    func webSocket(_ service: WebSocketService, didReceiveProactiveMessage message: String)
    func webSocket(_ service: WebSocketService, didReceiveAgendaUpdate events: [[String: Any]])
}

extension WebSocketServiceDelegate {
    func webSocket(_ service: WebSocketService, didReceiveChatToken text: String) {}
    func webSocket(_ service: WebSocketService, didReceiveChatDone message: String, actions: [[String: Any]], error: String?) {}
    func webSocket(_ service: WebSocketService, didReceiveChatError error: String) {}
    func webSocket(_ service: WebSocketService, didReceiveProactiveMessage message: String) {}
    func webSocket(_ service: WebSocketService, didReceiveAgendaUpdate events: [[String: Any]]) {}
}

final class WebSocketService: NSObject, ObservableObject {
    static let shared = WebSocketService()

    @Published private(set) var isConnected = false
    @Published private(set) var connectionState: String = "disconnected" // disconnected | connecting | connected

    weak var delegate: WebSocketServiceDelegate?

    private var webSocketTask: URLSessionWebSocketTask?
    private var urlSession: URLSession?
    private var receiveTask: Task<Void, Never>?
    private var baseURL: String = ""
    private var token: String = ""
    private var reconnectAttempts = 0
    private let maxReconnectDelay: TimeInterval = 60
    private let idleTimeout: TimeInterval = 120
    private var lastReceivedTime: Date = .distantPast
    private var reconnectWorkItem: DispatchWorkItem?
    private let queue = DispatchQueue(label: "neuroion.ws")

    private override init() {
        super.init()
    }

    /// Build WebSocket URL from base URL (http -> ws, https -> wss) and token
    private static func webSocketURL(baseURL: String, token: String) -> URL? {
        let trimmed = baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, !token.isEmpty else { return nil }
        let noSlash = trimmed.hasSuffix("/") ? String(trimmed.dropLast()) : trimmed
        let scheme: String
        if noSlash.lowercased().hasPrefix("https://") {
            scheme = "wss"
        } else {
            scheme = "ws"
        }
        let hostPath = noSlash
            .replacingOccurrences(of: "https://", with: "", options: .caseInsensitive)
            .replacingOccurrences(of: "http://", with: "", options: .caseInsensitive)
        let path = hostPath.contains("/") ? hostPath : "\(hostPath)/"
        let pathWithWs = path.hasSuffix("/") ? "\(path)ws" : "\(path)/ws"
        let encodedToken = token.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? token
        let urlString = "\(scheme)://\(pathWithWs)?token=\(encodedToken)"
        return URL(string: urlString)
    }

    func connect(baseURL: String, token: String) {
        queue.async { [weak self] in
            self?._connect(baseURL: baseURL, token: token)
        }
    }

    private func _connect(baseURL: String, token: String) {
        guard connectionState != "connected" else { return }
        connectionState = "connecting"
        DispatchQueue.main.async { self.objectWillChange.send() }

        guard let url = Self.webSocketURL(baseURL: baseURL, token: token) else {
            connectionState = "disconnected"
            DispatchQueue.main.async { self.objectWillChange.send(); self.isConnected = false }
            return
        }
        self.baseURL = baseURL
        self.token = token
        let session = URLSession(configuration: .default, delegate: self, delegateQueue: nil)
        urlSession = session
        webSocketTask = session.webSocketTask(with: url)
        webSocketTask?.resume()
        lastReceivedTime = Date()
        receiveTask = Task { [weak self] in await self?._receiveLoop() }
    }

    func disconnect() {
        queue.async { [weak self] in
            self?.reconnectWorkItem?.cancel()
            self?.reconnectWorkItem = nil
            self?.receiveTask?.cancel()
            self?.webSocketTask?.cancel(with: .goingAway, reason: nil)
            self?.webSocketTask = nil
            self?.connectionState = "disconnected"
            self?.isConnected = false
            DispatchQueue.main.async { self?.objectWillChange.send() }
        }
    }

    func send(_ dict: [String: Any]) {
        guard let data = try? JSONSerialization.data(withJSONObject: dict),
              let task = webSocketTask, connectionState == "connected" else { return }
        task.send(.data(data)) { [weak self] _ in
            // optional log
        }
    }

    /// Send chat_message to start a chat
    func sendChatMessage(_ message: String) {
        send(["type": "chat_message", "message": message])
    }

    func sendCancelGeneration() {
        send(["type": "cancel_generation"])
    }

    /// Call when app has agenda to sync (e.g. on connect or when agenda changes)
    func sendAgendaSync(events: [[String: Any]]) {
        send(["type": "agenda_sync", "events": events])
    }

    private func _receiveLoop() async {
        while let task = webSocketTask, !Task.isCancelled {
            do {
                let message = try await task.receive()
                lastReceivedTime = Date()
                switch message {
                case .data(let data):
                    await _handleData(data)
                case .string(let str):
                    if let data = str.data(using: .utf8) {
                        await _handleData(data)
                    }
                @unknown default:
                    break
                }
            } catch {
                if !Task.isCancelled {
                    await _onDisconnect()
                }
                return
            }
        }
    }

    @MainActor
    private func _handleData(_ data: Data) async {
        guard let msg = WSIncomingMessage.parse(data) else { return }
        switch msg.type {
        case "heartbeat":
            send(["type": "heartbeat_ack"])
        case "chat_token":
            let text = msg.payload["text"] as? String ?? ""
            if !text.isEmpty {
                delegate?.webSocket(self, didReceiveChatToken: text)
            }
        case "chat_done":
            let message = msg.payload["message"] as? String ?? ""
            let actions = msg.payload["actions"] as? [[String: Any]] ?? []
            let error = msg.payload["error"] as? String
            delegate?.webSocket(self, didReceiveChatDone: message, actions: actions, error: error)
        case "chat_error":
            let error = msg.payload["error"] as? String ?? "Unknown error"
            delegate?.webSocket(self, didReceiveChatError: error)
        case "proactive_message":
            let message = msg.payload["message"] as? String ?? ""
            delegate?.webSocket(self, didReceiveProactiveMessage: message)
        case "agenda_update":
            let events = msg.payload["events"] as? [[String: Any]] ?? []
            delegate?.webSocket(self, didReceiveAgendaUpdate: events)
        default:
            break
        }
    }

    private func _onConnect() {
        queue.async { [weak self] in
            guard let self = self else { return }
            self.connectionState = "connected"
            self.isConnected = true
            self.reconnectAttempts = 0
            DispatchQueue.main.async { self.objectWillChange.send() }
        }
    }

    private func _onDisconnect() async {
        await MainActor.run {
            connectionState = "disconnected"
            isConnected = false
            objectWillChange.send()
        }
        webSocketTask = nil
        receiveTask = nil

        let delay = min(pow(2.0, Double(reconnectAttempts)), maxReconnectDelay)
        reconnectAttempts += 1
        reconnectWorkItem = DispatchWorkItem { [weak self] in
            guard let self = self, !self.baseURL.isEmpty, !self.token.isEmpty else { return }
            self._connect(baseURL: self.baseURL, token: self.token)
        }
        queue.asyncAfter(deadline: .now() + delay, execute: reconnectWorkItem!)
    }

    /// Call when app enters foreground to try reconnect if disconnected
    func tryReconnectIfNeeded() {
        guard connectionState == "disconnected", !baseURL.isEmpty, !token.isEmpty else { return }
        connect(baseURL: baseURL, token: token)
    }
}

extension WebSocketService: URLSessionWebSocketDelegate {
    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didOpenWithProtocol protocol: String?) {
        _onConnect()
    }

    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didCloseWith closeCode: URLSessionWebSocketTask.CloseCode, reason: Data?) {
        Task { await _onDisconnect() }
    }

    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        if error != nil {
            Task { await _onDisconnect() }
        }
    }
}
