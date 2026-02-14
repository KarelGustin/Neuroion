//
//  ChatView.swift
//  NeuroionApp
//
//  Chat interface similar to ChatGPT/Ollama. Send messages, get replies, confirm actions with one tap.
//

import SwiftUI
import Combine

private let typingIndicatorId = UUID()

struct ChatView: View {
    @EnvironmentObject var authManager: AuthManager
    @ObservedObject private var store = ChatSessionStore.shared
    @FocusState private var isInputFocused: Bool
    @State private var messageText = ""

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 16) {
                            ForEach(store.messages) { message in
                                MessageBubble(message: message)
                                    .environmentObject(authManager)
                            }
                            if store.isSending {
                                TypingIndicatorView(statusText: store.statusText)
                                    .id(typingIndicatorId)
                            }
                        }
                        .padding()
                        .contentShape(Rectangle())
                        .onTapGesture {
                            isInputFocused = false
                        }
                    }
                    .scrollDismissesKeyboard(.interactively)
                    .onChange(of: store.messages.count) { _ in
                        scrollToBottom(proxy: proxy)
                    }
                    .onChange(of: store.isSending) { sending in
                        if sending { scrollToBottom(proxy: proxy) }
                    }
                }

                Divider()

                HStack(alignment: .bottom, spacing: 12) {
                    TextField("Message...", text: $messageText, axis: .vertical)
                        .textFieldStyle(.plain)
                        .padding(12)
                        .background(Color(.systemGray6))
                        .cornerRadius(20)
                        .lineLimit(1...6)
                        .focused($isInputFocused)
                        .onSubmit { sendOrStop() }

                    Button(action: sendOrStop) {
                        if store.isSending {
                            Image(systemName: "stop.circle.fill")
                                .font(.system(size: 32))
                                .foregroundColor(.red)
                        } else {
                            Image(systemName: "arrow.up.circle.fill")
                                .font(.system(size: 32))
                                .foregroundColor(messageText.isEmpty ? .gray : .blue)
                        }
                    }
                    .disabled(!store.isSending && messageText.isEmpty)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
            }
            .navigationTitle("Chat")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private func scrollToBottom(proxy: ScrollViewProxy) {
        if store.isSending {
            withAnimation(.easeOut(duration: 0.2)) {
                proxy.scrollTo(typingIndicatorId, anchor: .bottom)
            }
        } else if let lastMessage = store.messages.last {
            withAnimation(.easeOut(duration: 0.2)) {
                proxy.scrollTo(lastMessage.id, anchor: .bottom)
            }
        }
    }

    private func sendOrStop() {
        if store.isSending {
            store.cancelSend()
            return
        }
        guard !messageText.isEmpty else { return }
        let text = messageText
        messageText = ""
        let token = authManager.token ?? ""
        store.sendMessage(text, token: token)
    }

    private func sendMessage() {
        guard !messageText.isEmpty else { return }
        let text = messageText
        messageText = ""
        let token = authManager.token ?? ""
        store.sendMessage(text, token: token)
    }
}

struct TypingIndicatorView: View {
    var statusText: String = "Neuroion denkt na…"

    var body: some View {
        HStack(alignment: .top) {
            HStack(spacing: 8) {
                ProgressView()
                    .scaleEffect(0.8)
                Text(statusText)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color(.systemGray5))
            .cornerRadius(18)
            Spacer(minLength: 48)
        }
    }
}

struct MessageBubble: View {
    let message: Message
    @EnvironmentObject var authManager: AuthManager
    
    var body: some View {
        HStack(alignment: .top) {
            if message.isUser { Spacer(minLength: 48) }
            
            VStack(alignment: message.isUser ? .trailing : .leading, spacing: 8) {
                Text(message.text)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                    .background(message.isUser ? Color.blue : Color(.systemGray5))
                    .foregroundColor(message.isUser ? .white : .primary)
                    .cornerRadius(18)
                
                if let actions = message.actions, !actions.isEmpty {
                    ForEach(actions) { action in
                        ActionCard(action: action)
                            .environmentObject(authManager)
                    }
                }
            }
            
            if !message.isUser { Spacer(minLength: 48) }
        }
    }
}

struct ActionCard: View {
    let action: Action
    @EnvironmentObject var authManager: AuthManager
    @State private var showConfirm = false
    @State private var showResultAlert = false
    @State private var executeResultText = ""
    @State private var isExecuting = false
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(action.name)
                .font(.subheadline)
                .fontWeight(.semibold)
            if !action.reasoning.isEmpty {
                Text(action.reasoning)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Button {
                showConfirm = true
            } label: {
                if isExecuting {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        .scaleEffect(0.9)
                } else {
                    Text("Uitvoeren")
                }
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.small)
            .disabled(isExecuting)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.blue.opacity(0.08))
        .cornerRadius(12)
        .alert("Bevestigen", isPresented: $showConfirm) {
            Button("Annuleren", role: .cancel) { }
            Button("Uitvoeren") {
                performExecute()
            }
        } message: {
            Text("\(action.name) uitvoeren?")
        }
        .alert("Resultaat", isPresented: $showResultAlert) {
            Button("OK") { }
        } message: {
            Text(executeResultText)
        }
    }
    
    private func performExecute() {
        guard let token = authManager.token else { return }
        showConfirm = false
        isExecuting = true
        
        Task {
            do {
                let response = try await ChatService.shared.executeAction(actionId: action.id, token: token)
                await MainActor.run {
                    isExecuting = false
                    if response.success {
                        if let result = response.result, !result.isEmpty {
                            executeResultText = result.map { "\($0.key): \($0.value.value)" }.joined(separator: "\n")
                        } else {
                            executeResultText = "Gelukt."
                        }
                    } else {
                        executeResultText = response.error ?? "Onbekende fout"
                    }
                    showResultAlert = true
                }
            } catch {
                await MainActor.run {
                    isExecuting = false
                    executeResultText = error.localizedDescription
                    showResultAlert = true
                }
            }
        }
    }
}

// MARK: - ChatSessionStore (shared state so streaming continues when switching tabs)

final class ChatSessionStore: ObservableObject {
    static let shared = ChatSessionStore()

    @Published var messages: [Message] = []
    @Published var isSending = false
    @Published var statusText = "Neuroion denkt na…"

    private var currentTask: Task<Void, Never>?

    private init() {}

    func sendMessage(_ text: String, token: String) {
        guard !text.isEmpty else { return }
        neuroionLog("send message: \(text.prefix(200))\(text.count > 200 ? "…" : "")")

        let userMessage = Message(
            id: UUID(),
            text: text,
            isUser: true,
            timestamp: Date()
        )
        messages.append(userMessage)
        isSending = true
        statusText = "Neuroion denkt na…"

        currentTask = Task { @MainActor in
            await runStream(message: text, token: token)
            currentTask = nil
        }
    }

    func cancelSend() {
        neuroionLog("cancelSend")
        currentTask?.cancel()
        currentTask = nil
        isSending = false
        let stoppedMessage = Message(
            id: UUID(),
            text: NSLocalizedString("Gestopt. Je kunt een nieuw bericht sturen.", comment: "Chat stopped"),
            isUser: false,
            timestamp: Date()
        )
        messages.append(stoppedMessage)
    }

    private func runStream(message: String, token: String) async {
        do {
            let stream = ChatService.shared.sendMessageStreaming(message: message, token: token)
            for try await event in stream {
                if Task.isCancelled { break }
                switch event {
                case .status(let text):
                    statusText = text
                    neuroionLog("stream status: \(text)")
                case .done(let response):
                    let actions: [Action] = response.actions.map { ar in
                        Action(
                            id: ar.id ?? 0,
                            name: ar.name,
                            description: ar.description,
                            parameters: Dictionary(uniqueKeysWithValues: ar.parameters.map { ($0.key, $0.value.value) }),
                            reasoning: ar.reasoning
                        )
                    }
                    let botMessage = Message(
                        id: UUID(),
                        text: response.message.isEmpty ? NSLocalizedString("Geen antwoord ontvangen.", comment: "Chat") : response.message,
                        isUser: false,
                        timestamp: Date(),
                        actions: actions.isEmpty ? nil : actions
                    )
                    messages.append(botMessage)
                    neuroionLog("stream done: \(response.message.prefix(100))...")
                    isSending = false
                    return
                }
            }
            if Task.isCancelled {
                isSending = false
                return
            }
            isSending = false
        } catch is CancellationError {
            neuroionLog("stream cancelled")
            isSending = false
        } catch {
            if let apiError = error as? APIError, case .httpError(404) = apiError {
                do {
                    let response = try await ChatService.shared.sendMessage(message: message, token: token)
                    let actions: [Action] = response.actions.map { ar in
                        Action(
                            id: ar.id ?? 0,
                            name: ar.name,
                            description: ar.description,
                            parameters: Dictionary(uniqueKeysWithValues: ar.parameters.map { ($0.key, $0.value.value) }),
                            reasoning: ar.reasoning
                        )
                    }
                    let botMessage = Message(
                        id: UUID(),
                        text: response.message.isEmpty ? NSLocalizedString("Geen antwoord ontvangen.", comment: "Chat") : response.message,
                        isUser: false,
                        timestamp: Date(),
                        actions: actions.isEmpty ? nil : actions
                    )
                    await MainActor.run {
                        messages.append(botMessage)
                        neuroionLog("non-stream done")
                    }
                } catch {
                    await MainActor.run { appendErrorMessage(for: error) }
                }
            } else {
                await MainActor.run { appendErrorMessage(for: error) }
            }
            await MainActor.run { isSending = false }
        }
    }

    private func appendErrorMessage(for error: Error) {
        let errorMessage = Message(
            id: UUID(),
            text: userFacingErrorMessage(for: error),
            isUser: false,
            timestamp: Date()
        )
        messages.append(errorMessage)
        neuroionLog("chat error: \(error.localizedDescription)")
    }

    private func userFacingErrorMessage(for error: Error) -> String {
        if let urlError = error as? URLError {
            switch urlError.code {
            case .timedOut:
                return NSLocalizedString("Het duurde te lang. Tik op Stop en stuur opnieuw, of controleer VPN/verbinding in Instellingen.", comment: "Chat timeout")
            case .notConnectedToInternet, .networkConnectionLost:
                return NSLocalizedString("Geen internetverbinding. Controleer WiFi of mobiele data.", comment: "Chat error")
            case .cannotFindHost, .cannotConnectToHost:
                return NSLocalizedString("Kan Homebase niet bereiken. Klopt het adres in Instellingen?", comment: "Chat error")
            default:
                break
            }
        }
        return error.localizedDescription
    }
}

private func neuroionLog(_ message: String) {
    NSLog("[Neuroion] %@", message)
}
