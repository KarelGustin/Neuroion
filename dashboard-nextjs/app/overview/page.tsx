'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getSetupSummary, updateDevice } from '@/lib/api'

interface SetupSummaryMember {
  name: string
  role: string
}

interface SetupSummary {
  device_name: string
  timezone: string
  wifi_ssid: string | null
  wifi_configured: boolean
  household_name: string
  members: SetupSummaryMember[]
  llm_preset: string
  llm_model: string
  retention_policy: Record<string, unknown> | null
}

export default function OverviewPage() {
  const [summary, setSummary] = useState<SetupSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingDevice, setEditingDevice] = useState(false)
  const [deviceName, setDeviceName] = useState('')
  const [timezone, setTimezone] = useState('')
  const [savingDevice, setSavingDevice] = useState(false)

  const fetchSummary = async () => {
    try {
      const data = await getSetupSummary()
      setSummary(data)
      setDeviceName(data.device_name)
      setTimezone(data.timezone)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load overview')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSummary()
  }, [])

  const handleSaveDevice = async (e: React.FormEvent) => {
    e.preventDefault()
    setSavingDevice(true)
    try {
      await updateDevice(deviceName, timezone)
      await fetchSummary()
      setEditingDevice(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save device')
    } finally {
      setSavingDevice(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-muted">Loading...</div>
      </div>
    )
  }

  if (error && !summary) {
    return (
      <div className="min-h-screen p-6 max-w-4xl mx-auto">
        <Link href="/" className="text-muted hover:text-foreground mb-4 inline-block">← Back to Dashboard</Link>
        <p className="text-red-500">{error}</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen p-4 md:p-6 max-w-4xl mx-auto">
      <header className="mb-6 md:mb-8">
        <Link href="/" className="text-muted hover:text-foreground mb-4 inline-block">← Back to Dashboard</Link>
        <h1 className="text-3xl md:text-4xl font-semibold mb-2">Overzicht</h1>
        <p className="text-muted">Onboarding- en wizardgegevens (bewerkbaar)</p>
      </header>

      <div className="space-y-4 md:space-y-6">
        {/* Apparaat */}
        <section className="bg-[#111] border border-border rounded-xl p-4 md:p-6">
          <h2 className="text-lg font-semibold mb-3">Apparaat</h2>
          {editingDevice ? (
            <form onSubmit={handleSaveDevice} className="space-y-3">
              <div>
                <label className="block text-sm text-muted mb-1">Naam</label>
                <input
                  type="text"
                  value={deviceName}
                  onChange={(e) => setDeviceName(e.target.value)}
                  className="w-full px-3 py-2 bg-[#0a0a0a] border border-border rounded-lg text-foreground"
                />
              </div>
              <div>
                <label className="block text-sm text-muted mb-1">Tijdzone</label>
                <input
                  type="text"
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="w-full px-3 py-2 bg-[#0a0a0a] border border-border rounded-lg text-foreground"
                />
              </div>
              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={savingDevice}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium disabled:opacity-50"
                >
                  {savingDevice ? 'Opslaan...' : 'Opslaan'}
                </button>
                <button
                  type="button"
                  onClick={() => setEditingDevice(false)}
                  className="px-4 py-2 bg-[#333] hover:bg-[#444] rounded-lg font-medium"
                >
                  Annuleren
                </button>
              </div>
            </form>
          ) : (
            <>
              <dl className="space-y-2 text-sm">
                <div><dt className="text-muted">Naam</dt><dd className="font-medium">{summary?.device_name ?? '—'}</dd></div>
                <div><dt className="text-muted">Tijdzone</dt><dd className="font-medium">{summary?.timezone ?? '—'}</dd></div>
              </dl>
              <button
                type="button"
                onClick={() => setEditingDevice(true)}
                className="mt-3 px-4 py-2 bg-[#333] hover:bg-[#444] rounded-lg text-sm font-medium"
              >
                Bewerken
              </button>
            </>
          )}
        </section>

        {/* Netwerk */}
        <section className="bg-[#111] border border-border rounded-xl p-4 md:p-6">
          <h2 className="text-lg font-semibold mb-3">Netwerk</h2>
          <dl className="space-y-2 text-sm">
            <div><dt className="text-muted">Status</dt><dd className="font-medium">{summary?.wifi_configured ? 'Verbonden' : 'Niet geconfigureerd'}</dd></div>
            {summary?.wifi_ssid && <div><dt className="text-muted">SSID</dt><dd className="font-medium">{summary.wifi_ssid}</dd></div>}
          </dl>
        </section>

        {/* Huishouden */}
        <section className="bg-[#111] border border-border rounded-xl p-4 md:p-6">
          <h2 className="text-lg font-semibold mb-3">Huishouden</h2>
          <dl className="space-y-2 text-sm mb-3">
            <div><dt className="text-muted">Naam</dt><dd className="font-medium">{summary?.household_name ?? '—'}</dd></div>
          </dl>
          {summary?.members && summary.members.length > 0 && (
            <div className="mt-2">
              <dt className="text-muted text-sm mb-1">Leden</dt>
              <ul className="space-y-1">
                {summary.members.map((m, i) => (
                  <li key={i} className="font-medium">{m.name} <span className="text-muted">({m.role})</span></li>
                ))}
              </ul>
            </div>
          )}
          <Link href="/household" className="inline-block mt-3 px-4 py-2 bg-[#333] hover:bg-[#444] rounded-lg text-sm font-medium">
            Leden beheren
          </Link>
        </section>

        {/* Model */}
        <section className="bg-[#111] border border-border rounded-xl p-4 md:p-6">
          <h2 className="text-lg font-semibold mb-3">Model (LLM)</h2>
          <dl className="space-y-2 text-sm">
            <div><dt className="text-muted">Preset</dt><dd className="font-medium">{summary?.llm_preset ?? '—'}</dd></div>
            <div><dt className="text-muted">Model</dt><dd className="font-medium">{summary?.llm_model ?? '—'}</dd></div>
          </dl>
        </section>

        {/* Privacy */}
        <section className="bg-[#111] border border-border rounded-xl p-4 md:p-6">
          <h2 className="text-lg font-semibold mb-3">Privacy</h2>
          <p className="text-sm text-muted">
            {summary?.retention_policy
              ? `Bewaarbeleid: ${JSON.stringify(summary.retention_policy)}`
              : 'Geen bewaarbeleid ingesteld.'}
          </p>
          <Link href="/privacy" className="inline-block mt-3 px-4 py-2 bg-[#333] hover:bg-[#444] rounded-lg text-sm font-medium">
            Privacy-instellingen
          </Link>
        </section>
      </div>
    </div>
  )
}
