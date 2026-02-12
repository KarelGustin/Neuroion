'use client'

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { verifyJoinToken, consumeJoinToken, setPasscode } from '@/lib/api'
import Link from 'next/link'

export default function JoinPage() {
  const searchParams = useSearchParams()
  const token = searchParams.get('token')

  const [step, setStep] = useState<'verify' | 'form' | 'passcode' | 'complete'>('verify')
  const [valid, setValid] = useState(false)
  const [loading, setLoading] = useState(true)
  const [formData, setFormData] = useState({
    name: '',
    language: 'nl',
    timezone: 'Europe/Amsterdam',
    style_prefs: {},
    preferences: {},
    consent: {},
  })
  const [submitting, setSubmitting] = useState(false)
  const [pageName, setPageName] = useState<string | null>(null)
  const [setupToken, setSetupToken] = useState<string | null>(null)
  const [passcodeForm, setPasscodeForm] = useState({ passcode: '', confirm: '' })
  const [passcodeError, setPasscodeError] = useState<string | null>(null)
  const [settingPasscode, setSettingPasscode] = useState(false)

  useEffect(() => {
    if (token) {
      verifyToken()
    } else {
      setLoading(false)
    }
  }, [token])

  const verifyToken = async () => {
    if (!token) return
    
    try {
      const result = await verifyJoinToken(token)
      if (result.valid) {
        setValid(true)
        setStep('form')
      } else {
        setValid(false)
      }
    } catch (err) {
      console.error('Failed to verify token:', err)
      setValid(false)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token) return

    setSubmitting(true)
    try {
      const result = await consumeJoinToken(token, formData)
      setPageName(result.page_name)
      setSetupToken(result.setup_token)
      setStep('passcode')
    } catch (err: any) {
      console.error('Failed to join:', err)
      alert(err.response?.data?.detail || 'Failed to join. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const handlePasscodeSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!setupToken) return
    const { passcode, confirm } = passcodeForm
    if (passcode.length < 4 || passcode.length > 6 || !/^\d+$/.test(passcode)) {
      setPasscodeError('Voer 4-6 cijfers in')
      return
    }
    if (passcode !== confirm) {
      setPasscodeError('Passcodes komen niet overeen')
      return
    }
    setPasscodeError(null)
    setSettingPasscode(true)
    try {
      await setPasscode(setupToken, passcode)
      setStep('complete')
    } catch (err: any) {
      setPasscodeError(err.response?.data?.detail || 'Kon passcode niet opslaan')
    } finally {
      setSettingPasscode(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-muted">Verifying token...</div>
      </div>
    )
  }

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="text-center">
          <h1 className="text-2xl font-semibold mb-4">Invalid Join Link</h1>
          <p className="text-muted mb-4">No join token provided.</p>
          <Link href="/" className="text-blue-500 hover:underline">
            Go to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  if (!valid && step === 'verify') {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="text-center">
          <h1 className="text-2xl font-semibold mb-4">Invalid or Expired Token</h1>
          <p className="text-muted mb-4">The join token is invalid or has expired. Please request a new one.</p>
          <Link href="/" className="text-blue-500 hover:underline">
            Go to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  if (step === 'passcode' && pageName && setupToken) {
    const personalUrl = typeof window !== 'undefined' ? `${window.location.origin}/p/${pageName}` : `/p/${pageName}`
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="max-w-md w-full">
          <h1 className="text-2xl font-semibold mb-2">Kies je passcode</h1>
          <p className="text-muted mb-6">
            Voer 4-6 cijfers in. Hiermee open je straks je persoonlijke pagina.
          </p>
          <form onSubmit={handlePasscodeSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Passcode</label>
              <input
                type="password"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                value={passcodeForm.passcode}
                onChange={(e) =>
                  setPasscodeForm((prev) => ({ ...prev, passcode: e.target.value.replace(/\D/g, '') }))
                }
                className="w-full px-4 py-3 bg-[#111] border border-[var(--border)] rounded-lg focus:outline-none focus:border-blue-500"
                placeholder="4-6 cijfers"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Bevestig passcode</label>
              <input
                type="password"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                value={passcodeForm.confirm}
                onChange={(e) =>
                  setPasscodeForm((prev) => ({ ...prev, confirm: e.target.value.replace(/\D/g, '') }))
                }
                className="w-full px-4 py-3 bg-[#111] border border-[var(--border)] rounded-lg focus:outline-none focus:border-blue-500"
                placeholder="Herhaal"
              />
            </div>
            {passcodeError && <p className="text-sm text-red-400">{passcodeError}</p>}
            <button
              type="submit"
              disabled={settingPasscode || passcodeForm.passcode.length < 4 || passcodeForm.passcode !== passcodeForm.confirm}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {settingPasscode ? 'Opslaan...' : 'Doorgaan'}
            </button>
          </form>
          <p className="text-muted text-sm mt-4">
            Jouw pagina: <span className="font-mono text-foreground">/p/{pageName}</span>
          </p>
        </div>
      </div>
    )
  }

  if (step === 'complete' && pageName) {
    const personalUrl = typeof window !== 'undefined' ? `${window.location.origin}/p/${pageName}` : `/p/${pageName}`
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="text-center max-w-md">
          <h1 className="text-3xl font-semibold mb-4">Welkom bij Neuroion!</h1>
          <p className="text-muted mb-6">Je bent toegevoegd. Open je persoonlijke dashboard of sla de pagina op.</p>
          <div className="space-y-4 mb-8">
            <Link
              href={`/p/${pageName}`}
              className="block p-4 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition-colors"
            >
              Open je dashboard
            </Link>
            <div className="p-4 bg-[#111] border border-[var(--border)] rounded-lg text-left">
              <p className="text-sm font-medium mb-2">Sla deze pagina op</p>
              <p className="text-xs text-muted break-all">{personalUrl}</p>
              <p className="text-xs text-muted mt-2">Voeg toe aan startscherm voor snelle toegang. Log in met je passcode.</p>
            </div>
          </div>
          <Link href="/" className="text-muted hover:text-white text-sm">
            Naar hoofdpagina
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="max-w-md w-full">
        <h1 className="text-3xl font-semibold mb-2">Join Neuroion</h1>
        <p className="text-muted mb-8">Complete your profile to get started</p>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium mb-2">Name *</label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-4 py-3 bg-[#111] border border-border rounded-lg focus:outline-none focus:border-blue-500"
              placeholder="Your name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Language</label>
            <select
              value={formData.language}
              onChange={(e) => setFormData({ ...formData, language: e.target.value })}
              className="w-full px-4 py-3 bg-[#111] border border-border rounded-lg focus:outline-none focus:border-blue-500"
            >
              <option value="nl">Nederlands</option>
              <option value="en">English</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Timezone</label>
            <select
              value={formData.timezone}
              onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
              className="w-full px-4 py-3 bg-[#111] border border-border rounded-lg focus:outline-none focus:border-blue-500"
            >
              <option value="Europe/Amsterdam">Europe/Amsterdam</option>
              <option value="Europe/London">Europe/London</option>
              <option value="America/New_York">America/New_York</option>
              <option value="America/Los_Angeles">America/Los_Angeles</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={submitting || !formData.name}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? 'Joining...' : 'Join Household'}
          </button>
        </form>
      </div>
    </div>
  )
}
