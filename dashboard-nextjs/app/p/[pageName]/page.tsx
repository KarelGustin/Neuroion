'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  getByPage,
  unlockWithPasscode,
  setAuthToken,
  getUserStats,
} from '@/lib/api'
import ChatBadge from '@/components/ChatBadge'

const TOKEN_KEY = 'neuroion_token'
const PAGE_NAME_KEY = 'neuroion_user_page'

export default function PersonalPage() {
  const params = useParams()
  const pageName = params.pageName as string
  const [unlocked, setUnlocked] = useState(false)
  const [checking, setChecking] = useState(true)
  const [passcode, setPasscode] = useState('')
  const [unlockError, setUnlockError] = useState<string | null>(null)
  const [pageExists, setPageExists] = useState(false)
  const [displayName, setDisplayName] = useState<string | null>(null)
  const [stats, setStats] = useState<{ daily_requests: number; message_count: number } | null>(null)
  const [statsError, setStatsError] = useState<string | null>(null)

  useEffect(() => {
    if (!pageName) {
      setChecking(false)
      return
    }
    const token = typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null
    const storedPage = typeof window !== 'undefined' ? localStorage.getItem(PAGE_NAME_KEY) : null
    if (token && storedPage === pageName) {
      setAuthToken(token)
      setUnlocked(true)
      setChecking(false)
      return
    }
    getByPage(pageName)
      .then((data: { exists: boolean; display_name?: string }) => {
        setPageExists(data.exists)
        setDisplayName(data.display_name || null)
      })
      .catch(() => setPageExists(false))
      .finally(() => setChecking(false))
  }, [pageName])

  useEffect(() => {
    if (!unlocked || !pageName) return
    getUserStats()
      .then((data: { daily_requests: number; message_count: number }) => setStats(data))
      .catch(() => setStatsError('Could not load stats'))
  }, [unlocked, pageName])

  const handleUnlock = async (e: React.FormEvent) => {
    e.preventDefault()
    setUnlockError(null)
    if (!passcode.trim() || passcode.length < 4 || passcode.length > 6) {
      setUnlockError('Voer een passcode van 4-6 cijfers in')
      return
    }
    try {
      const data = await unlockWithPasscode(pageName, passcode)
      const token = data.token
      if (typeof window !== 'undefined') {
        localStorage.setItem(TOKEN_KEY, token)
        localStorage.setItem(PAGE_NAME_KEY, pageName)
      }
      setAuthToken(token)
      setUnlocked(true)
      setPasscode('')
    } catch (err: any) {
      setUnlockError(err.response?.data?.detail || 'Ongeldige passcode')
    }
  }

  const handleLogout = () => {
    setAuthToken(null)
    if (typeof window !== 'undefined') {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(PAGE_NAME_KEY)
    }
    setUnlocked(false)
  }

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted">Loading...</p>
      </div>
    )
  }

  if (!pageExists && !unlocked) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="text-center max-w-md">
          <h1 className="text-2xl font-semibold mb-4">Pagina niet gevonden</h1>
          <p className="text-muted mb-4">Deze persoonlijke pagina bestaat niet.</p>
          <Link href="/" className="text-blue-500 hover:underline">Naar start</Link>
        </div>
      </div>
    )
  }

  if (!unlocked) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-semibold mb-1">
            {displayName ? `${displayName}` : 'Neuroion'}
          </h1>
          <p className="text-muted text-sm mb-6">Voer je passcode in om door te gaan</p>
          <form onSubmit={handleUnlock} className="space-y-4">
            <input
              type="password"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={6}
              placeholder="4-6 cijfers"
              value={passcode}
              onChange={(e) => setPasscode(e.target.value.replace(/\D/g, ''))}
              className="w-full px-4 py-3 bg-[#111] border border-[var(--border)] rounded-lg focus:outline-none focus:border-blue-500"
              autoFocus
            />
            {unlockError && (
              <p className="text-sm text-red-400">{unlockError}</p>
            )}
            <button
              type="submit"
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition-colors"
            >
              Openen
            </button>
          </form>
          <p className="text-muted text-xs mt-6 text-center">
            Sla deze pagina op: <span className="break-all">{typeof window !== 'undefined' ? window.location.href : ''}</span>
          </p>
          <p className="text-muted text-xs mt-2 text-center">Voeg toe aan startscherm voor snelle toegang</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen p-6 max-w-2xl mx-auto pb-24">
      <header className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-semibold">{displayName || 'Mijn dashboard'}</h1>
          <p className="text-muted text-sm">Neuroion</p>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          className="text-sm text-muted hover:text-white transition-colors"
        >
          Uitloggen
        </button>
      </header>

      {statsError && (
        <p className="text-sm text-amber-500 mb-4">{statsError}</p>
      )}

      {stats && (
        <div className="grid grid-cols-2 gap-4 mb-8">
          <div className="p-4 bg-[#111] border border-[var(--border)] rounded-xl">
            <p className="text-xs text-muted uppercase tracking-wider">Requests vandaag</p>
            <p className="text-2xl font-semibold mt-1">{stats.daily_requests}</p>
          </div>
          <div className="p-4 bg-[#111] border border-[var(--border)] rounded-xl">
            <p className="text-xs text-muted uppercase tracking-wider">Chatberichten</p>
            <p className="text-2xl font-semibold mt-1">{stats.message_count}</p>
          </div>
        </div>
      )}

      <nav className="grid grid-cols-1 gap-3">
        <Link
          href="/integrations"
          className="p-4 bg-[#111] border border-[var(--border)] rounded-xl hover:border-[#555] transition-colors flex items-center gap-4"
        >
          <span className="text-2xl">🔗</span>
          <div>
            <div className="font-medium">Integrations</div>
            <div className="text-sm text-muted">Connect services</div>
          </div>
        </Link>
        <Link
          href="/privacy"
          className="p-4 bg-[#111] border border-[var(--border)] rounded-xl hover:border-[#555] transition-colors flex items-center gap-4"
        >
          <span className="text-2xl">🔒</span>
          <div>
            <div className="font-medium">Privacy</div>
            <div className="text-sm text-muted">Data settings</div>
          </div>
        </Link>
      </nav>

      <ChatBadge />
    </div>
  )
}
