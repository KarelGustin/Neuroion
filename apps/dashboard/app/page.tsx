'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getStatus } from '@/lib/api'
import StatusCard from '@/components/StatusCard'

export default function DashboardPage() {
  const [status, setStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStatus()
  }, [])

  const fetchStatus = async () => {
    try {
      const data = await getStatus()
      setStatus(data)
    } catch (err) {
      console.error('Failed to fetch status:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-muted">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen p-6 max-w-6xl mx-auto">
      <header className="mb-8">
        <h1 className="text-4xl font-semibold mb-2">Neuroion</h1>
        <p className="text-muted">Home Intelligence Platform</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {status?.network && (
          <StatusCard
            title="Network"
            status={status.network.wifi_configured ? 'Connected' : 'Disconnected'}
            details={{
              SSID: status.network.ssid,
              IP: status.network.ip,
              Hostname: status.network.hostname,
            }}
          />
        )}

        {status?.model && (
          <StatusCard
            title="LLM"
            status={status.model.status}
            details={{
              Preset: status.model.preset,
              Model: status.model.name,
              Health: status.model.health,
            }}
          />
        )}

        {status?.user?.name && (
          <StatusCard
            title="User"
            status="Active"
            details={{
              Name: status.user.name,
            }}
          />
        )}
      </div>

      <nav className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Link
          href="/overview"
          className="p-6 bg-[#111] border border-border rounded-xl hover:border-[#555] transition-colors"
        >
          <div className="text-2xl mb-2">📋</div>
          <div className="font-medium">Overzicht</div>
          <div className="text-sm text-muted mt-1">Onboarding &amp; instellingen</div>
        </Link>

        <Link
          href="/household"
          className="p-6 bg-[#111] border border-border rounded-xl hover:border-[#555] transition-colors"
        >
          <div className="text-2xl mb-2">👤</div>
          <div className="font-medium">Profile</div>
          <div className="text-sm text-muted mt-1">Single-user account</div>
        </Link>

        <Link
          href="/integrations"
          className="p-6 bg-[#111] border border-border rounded-xl hover:border-[#555] transition-colors"
        >
          <div className="text-2xl mb-2">🔗</div>
          <div className="font-medium">Integrations</div>
          <div className="text-sm text-muted mt-1">Connect services</div>
        </Link>

        <Link
          href="/user"
          className="p-6 bg-[#111] border border-border rounded-xl hover:border-[#555] transition-colors"
        >
          <div className="text-2xl mb-2">👤</div>
          <div className="font-medium">Mijn dashboard</div>
          <div className="text-sm text-muted mt-1">Profiel, context, agent</div>
        </Link>

        <Link
          href="/privacy"
          className="p-6 bg-[#111] border border-border rounded-xl hover:border-[#555] transition-colors"
        >
          <div className="text-2xl mb-2">🔒</div>
          <div className="font-medium">Privacy</div>
          <div className="text-sm text-muted mt-1">Data settings</div>
        </Link>

        <div className="p-6 bg-[#111] border border-border rounded-xl opacity-50 cursor-not-allowed">
          <div className="text-2xl mb-2">⚙️</div>
          <div className="font-medium">Settings</div>
          <div className="text-sm text-muted mt-1">Coming soon</div>
        </div>
      </nav>
    </div>
  )
}
