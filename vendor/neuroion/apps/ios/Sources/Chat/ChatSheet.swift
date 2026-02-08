import NeuroionChatUI
import NeuroionKit
import SwiftUI

struct ChatSheet: View {
    @Environment(\.dismiss) private var dismiss
    @State private var viewModel: NeuroionChatViewModel
    private let userAccent: Color?

    init(gateway: GatewayNodeSession, sessionKey: String, userAccent: Color? = nil) {
        let transport = IOSGatewayChatTransport(gateway: gateway)
        self._viewModel = State(
            initialValue: NeuroionChatViewModel(
                sessionKey: sessionKey,
                transport: transport))
        self.userAccent = userAccent
    }

    var body: some View {
        NavigationStack {
            NeuroionChatView(
                viewModel: self.viewModel,
                showsSessionSwitcher: true,
                userAccent: self.userAccent)
                .navigationTitle("Chat")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button {
                            self.dismiss()
                        } label: {
                            Image(systemName: "xmark")
                        }
                        .accessibilityLabel("Close")
                    }
                }
        }
    }
}
