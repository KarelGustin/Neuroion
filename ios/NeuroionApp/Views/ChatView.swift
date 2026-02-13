//
//  ChatView.swift
//  NeuroionApp
//
//  Chat interface similar to ChatGPT/Ollama. Send messages, get replies, confirm actions with one tap.
//

import SwiftUI

struct ChatView: View {
    @EnvironmentObject var authManager: AuthManager
    @State private var messageText = ""
    @State private var messages: [Message] = []
    @State private var isSending = false
    @State private var showSettings = false
    
    private let chatService = ChatService()
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 16) {
                            ForEach(messages) { message in
                                MessageBubble(message: message)
                                    .environmentObject(authManager)
                            }
                        }
                        .padding()
                    }
                    .onChange(of: messages.count) { _ in
                        if let lastMessage = messages.last {
                            withAnimation(.easeOut(duration: 0.2)) {
                                proxy.scrollTo(lastMessage.id, anchor: .bottom)
                            }
                        }
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
                        .onSubmit { sendMessage() }
                    
                    Button(action: sendMessage) {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.system(size: 32))
                            .foregroundColor(messageText.isEmpty ? .gray : .blue)
                    }
                    .disabled(messageText.isEmpty || isSending)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
            }
            .navigationTitle("Chat")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        showSettings = true
                    } label: {
                        Image(systemName: "gearshape")
                    }
                }
            }
            .sheet(isPresented: $showSettings) {
                SettingsView()
                    .environmentObject(authManager)
            }
        }
    }
    
    private func sendMessage() {
        guard !messageText.isEmpty else { return }
        
        let userMessage = Message(
            id: UUID(),
            text: messageText,
            isUser: true,
            timestamp: Date()
        )
        messages.append(userMessage)
        
        let messageToSend = messageText
        messageText = ""
        isSending = true
        
        Task {
            do {
                let response = try await chatService.sendMessage(
                    message: messageToSend,
                    token: authManager.token ?? ""
                )
                
                let actions: [Action] = response.actions.map { ar in
                    Action(
                        id: ar.id ?? 0,
                        name: ar.name,
                        description: ar.description,
                        parameters: Dictionary(uniqueKeysWithValues: ar.parameters.map { ($0.key, $0.value.value) }),
                        reasoning: ar.reasoning
                    )
                }
                
                await MainActor.run {
                    let botMessage = Message(
                        id: UUID(),
                        text: response.message,
                        isUser: false,
                        timestamp: Date(),
                        actions: actions.isEmpty ? nil : actions
                    )
                    messages.append(botMessage)
                    isSending = false
                }
            } catch {
                await MainActor.run {
                    let errorMessage = Message(
                        id: UUID(),
                        text: "Error: \(error.localizedDescription)",
                        isUser: false,
                        timestamp: Date()
                    )
                    messages.append(errorMessage)
                    isSending = false
                }
            }
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
                let response = try await ChatService().executeAction(actionId: action.id, token: token)
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
