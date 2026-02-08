'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getMe } from '@/lib/api'

interface Me {
  id: number
  name: string
  role: string
  language: string | null
  timezone: string | null
  household_id: number
  created_at: string
  last_seen_at: string | null
}

export default function UserDashboardPage() {
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)
  const [unauth, setUnauth] = useState(false)

  useEffect(() => {
    let cancelled = false
    getMe()
      .then((data) => {
        if (!cancelled) setMe(data)
      })
      .catch((err) => {
        if (!cancelled && err.response?.status === 401) setUnauth(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-muted">Loading...</div>
      </div>
    )
  }

  if (unauth || !me) {
    return (
      <div className="min-h-screen p-6 max-w-md mx-auto flex flex-col items-center justify-center">
        <p className="text-muted text-center mb-4">
          Log in with your passcode via your personal dashboard link (from your join completion).
        </p>
        <Link href="/" className="px-6 py-3 bg-[#333] hover:bg-[#444] rounded-lg font-medium">
          Naar start
        </Link>
      </div>
    )
  }

  return (
    <div className="min-h-screen p-4 md:p-6 max-w-4xl mx-auto">
      <header className="mb-6 md:mb-8">
        <Link href="/" className="text-muted hover:text-foreground mb-4 inline-block">← Dashboard</Link>
        <h1 className="text-3xl md:text-4xl font-semibold mb-2">Mijn dashboard</h1>
        <p className="text-muted">Je context, services en Neuroion Agent</p>
      </header>

      <div className="space-y-4 md:space-y-6">
        {/* Mijn profiel */}
        <section className="bg-[#111] border border-border rounded-xl p-4 md:p-6">
          <h2 className="text-lg font-semibold mb-3">Mijn profiel</h2>
          <dl className="space-y-2 text-sm">
            <div><dt className="text-muted">Naam</dt><dd className="font-medium">{me.name}</dd></div>
            <div><dt className="text-muted">Rol</dt><dd className="font-medium">{me.role}</dd></div>
            {me.language && <div><dt className="text-muted">Taal</dt><dd className="font-medium">{me.language}</dd></div>}
            {me.timezone && <div><dt className="text-muted">Tijdzone</dt><dd className="font-medium">{me.timezone}</dd></div>}
          </dl>
        </section>

        {/* Mijn context */}
        <section className="bg-[#111] border border-border rounded-xl p-4 md:p-6">
          <h2 className="text-lg font-semibold mb-3">Mijn context</h2>
          <p className="text-sm text-muted mb-3">Je opgeslagen context en notities voor Neuroion.</p>
          <Link href="/integrations" className="inline-block px-4 py-2 bg-[#333] hover:bg-[#444] rounded-lg text-sm font-medium">
            Bekijken
          </Link>
        </section>

        {/* Mijn services */}
        <section className="bg-[#111] border border-border rounded-xl p-4 md:p-6">
          <h2 className="text-lg font-semibold mb-3">Mijn services</h2>
          <p className="text-sm text-muted mb-3">Telegram en andere gekoppelde diensten.</p>
          <Link href="/integrations" className="inline-block px-4 py-2 bg-[#333] hover:bg-[#444] rounded-lg text-sm font-medium">
            Integraties
          </Link>
        </section>

        {/* Agent / Geplande taken */}
        <section className="bg-[#111] border border-border rounded-xl p-4 md:p-6">
          <h2 className="text-lg font-semibold mb-3">Neuroion Agent</h2>
          <p className="text-sm text-muted mb-3">Geplande taken en instellingen voor de agent (binnenkort).</p>
          <p className="text-xs text-muted">Coming soon</p>
        </section>
      </div>
    </div>
  )
}
