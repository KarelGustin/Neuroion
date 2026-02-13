import React, { useState, useEffect, useMemo } from 'react'
import { verifyJoinToken, consumeJoinToken, getPairingCode } from '../services/api'
import '../styles/JoinFlow.css'

function JoinFlow() {
  const token = useMemo(() => {
    return new URLSearchParams(window.location.search).get('token')
  }, [])

  const [step, setStep] = useState('verify')
  const [loading, setLoading] = useState(!!token)
  const [error, setError] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    language: 'nl',
    timezone: 'Europe/Amsterdam',
  })
  const [submitting, setSubmitting] = useState(false)
  const [pageName, setPageName] = useState(null)
  const [householdId, setHouseholdId] = useState(null)
  const [memberId, setMemberId] = useState(null)
  const [pairingCode, setPairingCode] = useState(null)
  const [pairingError, setPairingError] = useState(null)
  const [copied, setCopied] = useState(false)

  // Step 1: verify token
  useEffect(() => {
    if (!token) {
      setLoading(false)
      setError('Geen token. Scan de QR-code of gebruik de join-link.')
      return
    }
    if (step !== 'verify') return

    let cancelled = false
    verifyJoinToken(token)
      .then((result) => {
        if (cancelled) return
        if (result.valid) {
          setStep('form')
        } else {
          setError(result.message || 'Ongeldige of verlopen token.')
        }
      })
      .catch((err) => {
        if (cancelled) return
        setError(err.response?.data?.detail || err.message || 'Kon token niet verifiëren.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [token, step])

  // Step 3: fetch pairing code when complete (member_id binds code to this member so Telegram links to same user)
  useEffect(() => {
    if (step !== 'complete' || !householdId || pairingCode != null) return

    let cancelled = false
    getPairingCode(householdId, 'telegram_join', 'telegram', 'Telegram', memberId)
      .then((code) => {
        if (!cancelled) setPairingCode(code)
      })
      .catch((err) => {
        if (!cancelled) setPairingError(err.response?.data?.detail || err.message || 'Kon koppelcode niet ophalen.')
      })
    return () => { cancelled = true }
  }, [step, householdId, memberId, pairingCode])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!token || !formData.name.trim()) return
    setSubmitting(true)
    setError(null)
    try {
      const result = await consumeJoinToken(token, {
        name: formData.name.trim(),
        language: formData.language,
        timezone: formData.timezone,
      })
      setPageName(result.page_name)
      setHouseholdId(result.household_id)
      setMemberId(result.member_id)
      setStep('complete')
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Lid toevoegen mislukt.')
    } finally {
      setSubmitting(false)
    }
  }

  if (!token) {
    return (
      <div className="join-flow">
        <div className="join-flow-card">
          <h1 className="join-flow-title">Ongeldige link</h1>
          <p className="join-flow-message">Geen join-token. Scan de QR-code op het dashboard of gebruik de join-link.</p>
        </div>
      </div>
    )
  }

  if (loading && step === 'verify') {
    return (
      <div className="join-flow">
        <div className="join-flow-card">
          <p className="join-flow-message">Token controleren...</p>
        </div>
      </div>
    )
  }

  if (step === 'verify' && error) {
    return (
      <div className="join-flow">
        <div className="join-flow-card">
          <h1 className="join-flow-title">Ongeldige of verlopen token</h1>
          <p className="join-flow-message">{error}</p>
          <p className="join-flow-hint">Vraag een nieuwe link of QR-code aan op het Neuroion-dashboard.</p>
        </div>
      </div>
    )
  }

  if (step === 'form') {
    return (
      <div className="join-flow">
        <div className="join-flow-card">
          <h1 className="join-flow-title">Word lid van Neuroion</h1>
          <p className="join-flow-subtitle">Vul je gegevens in om het huishouden te joinen.</p>

          <form onSubmit={handleSubmit} className="join-flow-form">
            <div className="join-flow-field">
              <label htmlFor="join-name">Naam *</label>
              <input
                id="join-name"
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                placeholder="Je naam"
                className="join-flow-input"
              />
            </div>
            <div className="join-flow-field">
              <label htmlFor="join-language">Taal</label>
              <select
                id="join-language"
                value={formData.language}
                onChange={(e) => setFormData((prev) => ({ ...prev, language: e.target.value }))}
                className="join-flow-input"
              >
                <option value="nl">Nederlands</option>
                <option value="en">English</option>
              </select>
            </div>
            <div className="join-flow-field">
              <label htmlFor="join-timezone">Tijdzone</label>
              <select
                id="join-timezone"
                value={formData.timezone}
                onChange={(e) => setFormData((prev) => ({ ...prev, timezone: e.target.value }))}
                className="join-flow-input"
              >
                <option value="Europe/Amsterdam">Europe/Amsterdam</option>
                <option value="Europe/London">Europe/London</option>
                <option value="America/New_York">America/New_York</option>
                <option value="America/Los_Angeles">America/Los_Angeles</option>
              </select>
            </div>
            {error && <p className="join-flow-error">{error}</p>}
            <button type="submit" disabled={submitting || !formData.name.trim()} className="join-flow-submit">
              {submitting ? 'Bezig...' : 'Lid worden'}
            </button>
          </form>
        </div>
      </div>
    )
  }

  const copyCommand = pairingCode ? `/start ${pairingCode}` : ''
  const handleCopy = () => {
    if (!copyCommand) return
    navigator.clipboard.writeText(copyCommand).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }).catch(() => {})
  }

  if (step === 'complete') {
    return (
      <div className="join-flow">
        <div className="join-flow-card">
          <h1 className="join-flow-title">Welkom bij Neuroion!</h1>
          <p className="join-flow-message">Je account is aangemaakt. Koppel Telegram om met de Neuroion-bot te chatten.</p>

          <section className="join-flow-telegram">
            <h2 className="join-flow-telegram-title">Telegram koppelen</h2>
            {pairingError && <p className="join-flow-error">{pairingError}</p>}
            {pairingCode ? (
              <>
                <p className="join-flow-telegram-hint">
                  <a href="https://t.me/Neuroion_bot" target="_blank" rel="noopener noreferrer" className="join-flow-bot-link">
            Open de Neuroion-bot in Telegram
          </a>
                  {' '}en voer daar in:
                </p>
                <div className="join-flow-code-row">
                  <div className="join-flow-code-block">
                    <code className="join-flow-code">{copyCommand}</code>
                  </div>
                  <button type="button" className="join-flow-copy-btn" onClick={handleCopy} disabled={copied}>
                    {copied ? 'Gekopieerd!' : 'Kopiëren'}
                  </button>
                </div>
                <p className="join-flow-telegram-alt">Of gebruik: /pair {pairingCode}</p>
              </>
            ) : (
              <p className="join-flow-message">Koppelcode ophalen...</p>
            )}
          </section>

          {pageName && (
            <p className="join-flow-page-hint">
              Je persoonlijke pagina: <span className="join-flow-page-name">/p/{pageName}</span>
            </p>
          )}
        </div>
      </div>
    )
  }

  return null
}

export default JoinFlow
