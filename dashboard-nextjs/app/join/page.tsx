'use client'

import { useEffect, useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { verifyJoinToken, consumeJoinToken } from '@/lib/api'
import Link from 'next/link'

export default function JoinPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const token = searchParams.get('token')
  
  const [step, setStep] = useState<'verify' | 'form' | 'complete'>('verify')
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
      await consumeJoinToken(token, formData)
      setStep('complete')
    } catch (err: any) {
      console.error('Failed to join:', err)
      alert(err.response?.data?.detail || 'Failed to join. Please try again.')
    } finally {
      setSubmitting(false)
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

  if (step === 'complete') {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="text-center max-w-md">
          <h1 className="text-3xl font-semibold mb-4">Welcome to Neuroion!</h1>
          <p className="text-muted mb-8">You've successfully joined the household.</p>
          <div className="space-y-4">
            <Link
              href="/integrations"
              className="block p-4 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition-colors"
            >
              Choose Integration
            </Link>
            <Link
              href="/"
              className="block p-4 bg-[#333] hover:bg-[#444] rounded-lg font-medium transition-colors"
            >
              Go to Dashboard
            </Link>
          </div>
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
