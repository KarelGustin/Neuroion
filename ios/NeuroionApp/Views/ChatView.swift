//
//  ChatView.swift
//  NeuroionApp
//
//  Main chat interface for Neuroion
//

import SwiftUI

struct ChatView: View {
    @EnvironmentObject var authManager: AuthManager
    @StateObject private var chatService = ChatService()
    @State private var messageText = ""
    @State private var messages: [Message] = []
    
    var body: some View {
        NavigationView {
            VStack {
                // Messages list
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 12) {
                            ForEach(messages) { message in
                                MessageBubble(message: message)
                            }
                        }
                        .padding()
                    }
                    .onChange(of: messages.count) { _ in
                        if let lastMessage = messages.last {
                            withAnimation {
                                proxy.scrollTo(lastMessage.id, anchor: .bottom)
                            }
                        }
                    }
                }
                
                // Input area
                HStack {
                    TextField("Message...", text: $messageText)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                        .onSubmit {
                            sendMessage()
                        }
                    
                    Button(action: sendMessage) {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.title2)
                            .foregroundColor(.blue)
                    }
                    .disabled(messageText.isEmpty)
                }
                .padding()
            }
            .navigationTitle("Neuroion")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Settings") {
                        // Navigate to settings
                    }
                }
            }
        }
        .onAppear {
            loadMessages()
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
        
        Task {
            do {
                let response = try await chatService.sendMessage(
                    message: messageToSend,
                    token: authManager.token ?? ""
                )
                
                await MainActor.run {
                    let botMessage = Message(
                        id: UUID(),
                        text: response.message,
                        isUser: false,
                        timestamp: Date(),
                        actions: response.actions
                    )
                    messages.append(botMessage)
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
                }
            }
        }
    }
    
    private func loadMessages() {
        // Load conversation history if needed
    }
}

struct MessageBubble: View {
    let message: Message
    
    var body: some View {
        HStack {
            if message.isUser {
                Spacer()
            }
            
            VStack(alignment: message.isUser ? .trailing : .leading, spacing: 4) {
                Text(message.text)
                    .padding()
                    .background(message.isUser ? Color.blue : Color.gray.opacity(0.2))
                    .foregroundColor(message.isUser ? .white : .primary)
                    .cornerRadius(16)
                
                if let actions = message.actions, !actions.isEmpty {
                    ForEach(actions) { action in
                        ActionCard(action: action)
                    }
                }
            }
            
            if !message.isUser {
                Spacer()
            }
        }
    }
}

struct ActionCard: View {
    let action: Action
    @State private var showConfirm = false
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(action.name)
                .font(.headline)
            Text(action.reasoning)
                .font(.caption)
                .foregroundColor(.secondary)
            
            Button("Execute") {
                showConfirm = true
            }
            .buttonStyle(.borderedProminent)
        }
        .padding()
        .background(Color.blue.opacity(0.1))
        .cornerRadius(12)
        .alert("Confirm Action", isPresented: $showConfirm) {
            Button("Cancel", role: .cancel) { }
            Button("Execute") {
                executeAction()
            }
        } message: {
            Text("Execute \(action.name)?")
        }
    }
    
    private func executeAction() {
        // Execute action via API
    }
}
