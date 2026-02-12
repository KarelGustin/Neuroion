'use client'

import Link from 'next/link'

export default function IntegrationsPage() {
  return (
    <div className="min-h-screen p-6 max-w-4xl mx-auto">
      <header className="mb-8">
        <Link href="/" className="text-muted hover:text-foreground mb-4 inline-block">
          ← Back to Dashboard
        </Link>
        <h1 className="text-4xl font-semibold mb-2">Integrations</h1>
        <p className="text-muted">Connect Neuroion to your services</p>
      </header>

      <div className="space-y-4">
        {/* Telegram Integration */}
        <div className="p-6 bg-[#111] border border-border rounded-xl hover:border-[#555] transition-colors cursor-pointer">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="text-3xl">💬</div>
              <div>
                <h3 className="text-lg font-semibold mb-1">Telegram</h3>
                <p className="text-sm text-muted">Chat with Neuroion via Telegram bot</p>
              </div>
            </div>
            <div className="text-green-500">✓ Enabled</div>
          </div>
        </div>

        {/* Web Dashboard Integration */}
        <div className="p-6 bg-[#111] border border-border rounded-xl hover:border-[#555] transition-colors cursor-pointer">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="text-3xl">🌐</div>
              <div>
                <h3 className="text-lg font-semibold mb-1">Web Dashboard</h3>
                <p className="text-sm text-muted">Access Neuroion via web browser</p>
              </div>
            </div>
            <div className="text-green-500">✓ Enabled</div>
          </div>
        </div>

        {/* Native App Integration - Disabled */}
        <div className="p-6 bg-[#111] border border-border rounded-xl opacity-50 cursor-not-allowed">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="text-3xl">📱</div>
              <div>
                <h3 className="text-lg font-semibold mb-1">Native App</h3>
                <p className="text-sm text-muted">iOS and Android app</p>
              </div>
            </div>
            <div className="text-muted">Coming later</div>
          </div>
        </div>
      </div>
    </div>
  )
}
