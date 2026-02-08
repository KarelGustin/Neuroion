import React, { useState, useEffect } from 'react'
import { saveOwnerContext, getPairingCode, getTelegramInfo } from '../services/api'
import '../styles/ProfileTelegramStep.css'

/**
 * Personal profile wizard step for the first user (owner).
 * Collects context for the Neuroion Agent (ion) and guides Telegram connection.
 */
function ProfileTelegramStep({ onComplete, onBack, initialData }) {
  const saved = initialData || {}
  const [contextSummary, setContextSummary] = useState(saved.contextSummary || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)
  const [pairingCode, setPairingCode] = useState(null)
  const [pairingLoading, setPairingLoading] = useState(false)
  const [botUsername, setBotUsername] = useState(null)
  const [botConnected, setBotConnected] = useState(null)

  const householdId = saved.householdId || 1
  const ownerName = saved.ownerName || 'Owner'

  useEffect(() => {
    let cancelled = false
    const loadTelegramInfo = async () => {
      try {
        const info = await getTelegramInfo()
        if (cancelled) return
        setBotUsername(info?.bot_username || null)
        setBotConnected(Boolean(info?.connected))
      } catch (_) {
        if (!cancelled) {
          setBotUsername(null)
          setBotConnected(null)
        }
      }
    }
    loadTelegramInfo()
    return () => {
      cancelled = true
    }
  }, [])

  const handleShowPairingCode = async () => {
    setPairingLoading(true)
    setError(null)
    try {
      const code = await getPairingCode(
        householdId,
        `telegram_owner_${Date.now()}`,
        'telegram',
        ownerName
      )
      setPairingCode(code)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Could not get pairing code')
    } finally {
      setPairingLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(false)
    try {
      if (contextSummary.trim()) {
        await saveOwnerContext(contextSummary.trim())
      }
      setSuccess(true)
      const data = {
        contextSummary: contextSummary.trim() || null,
        contextSaved: !!contextSummary.trim(),
      }
      try {
        localStorage.setItem('neuroion_setup_profile_telegram', JSON.stringify(data))
      } catch (_) {}
      setTimeout(() => onComplete?.(data), 800)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to save')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="profile-telegram-step">
      <div className="config-header">
        <h3>Profiel & kanaal</h3>
        <p>Optionele context voor de Neuroion Agent (ion) en Telegram koppelen.</p>
      </div>

      <form onSubmit={handleSubmit} className="profile-telegram-form">
        <div className="form-group">
          <label htmlFor="context">Context voor ion (optioneel)</label>
          <p className="form-help">
            Hoe wil je aangesproken worden? Wat is belangrijk voor jou? De agent gebruikt dit om persoonlijker te reageren.
          </p>
          <textarea
            id="context"
            value={contextSummary}
            onChange={(e) => setContextSummary(e.target.value)}
            placeholder="Bijv. Ik heet Karel, ik werk thuis en hou van korte antwoorden."
            rows={4}
            disabled={loading || success}
            className="context-textarea"
          />
        </div>

        <section className="telegram-section">
          <h4>Telegram koppelen (aanbevolen)</h4>
          <p className="telegram-explanation">
            Koppel Telegram om met de Neuroion Agent (ion) te chatten. Open Telegram, zoek de bot en voer de koppelcode in. Je kunt dit ook later doen.
          </p>
          {botUsername ? (
            <p className="telegram-bot-name">
              Gebruik bot: <strong>@{botUsername}</strong>
            </p>
          ) : (
            <p className="telegram-bot-name">
              Telegram-bot is niet geconfigureerd. Vraag je beheerder om dit in te stellen.
            </p>
          )}
          {botConnected === false && (
            <p className="telegram-bot-status">
              Bot-token ontbreekt in de omgeving. Koppelen werkt pas na configuratie.
            </p>
          )}
          {!pairingCode ? (
            <button
              type="button"
              className="btn-secondary"
              onClick={handleShowPairingCode}
              disabled={pairingLoading}
            >
              {pairingLoading ? 'Ophalen…' : 'Toon koppelcode'}
            </button>
          ) : (
            <div className="pairing-code-block">
              <p className="code-label">Koppelcode</p>
              <p className="code-value">{pairingCode}</p>
              <p className="code-instructions">
                Open Telegram → start de Neuroion-bot → voer deze code in. Je kunt nu overslaan en later koppelen.
              </p>
            </div>
          )}
        </section>

        {error && <div className="error-message">{error}</div>}
        {success && (
          <div className="success-message">Opgeslagen. Ga verder.</div>
        )}

        <div className="form-actions">
          {onBack && (
            <button type="button" onClick={onBack} className="btn-secondary">
              Back
            </button>
          )}
          <button
            type="submit"
            className="btn-primary"
            disabled={loading || success}
          >
            {loading ? 'Opslaan…' : success ? 'Doorgaan' : 'Doorgaan'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default ProfileTelegramStep
