'use client'

import Link from 'next/link'

export default function JoinCompletePage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="text-center max-w-md">
        <h1 className="text-3xl font-semibold mb-4">Welcome to Neuroion!</h1>
        <p className="text-muted mb-8">You've successfully joined the household. Choose how you want to interact with Neuroion:</p>

        <div className="space-y-4 mb-8">
          {/* Telegram - Enabled */}
          <Link
            href="/integrations?setup=telegram"
            className="block p-6 bg-[#111] border border-border rounded-xl hover:border-[#555] transition-colors"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="text-3xl">💬</div>
                <div className="text-left">
                  <h3 className="text-lg font-semibold mb-1">Telegram</h3>
                  <p className="text-sm text-muted">Chat with Neuroion via Telegram bot</p>
                </div>
              </div>
              <div className="text-green-500">✓</div>
            </div>
          </Link>

          {/* Web Dashboard - Enabled */}
          <Link
            href="/"
            className="block p-6 bg-[#111] border border-border rounded-xl hover:border-[#555] transition-colors"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="text-3xl">🌐</div>
                <div className="text-left">
                  <h3 className="text-lg font-semibold mb-1">Web Dashboard</h3>
                  <p className="text-sm text-muted">Access Neuroion via web browser</p>
                </div>
              </div>
              <div className="text-green-500">✓</div>
            </div>
          </Link>

          {/* Native App - Disabled */}
          <div className="p-6 bg-[#111] border border-border rounded-xl opacity-50 cursor-not-allowed">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="text-3xl">📱</div>
                <div className="text-left">
                  <h3 className="text-lg font-semibold mb-1">Native App</h3>
                  <p className="text-sm text-muted">iOS and Android app</p>
                </div>
              </div>
              <div className="text-muted text-sm">Coming later</div>
            </div>
          </div>
        </div>

        <Link
          href="/"
          className="inline-block px-6 py-3 bg-[#333] hover:bg-[#444] rounded-lg font-medium transition-colors"
        >
          Continue to Dashboard
        </Link>
      </div>
    </div>
  )
}
