import React, { useState, useEffect } from 'react'
import { getTelegramInfo, saveNeuroionChannels } from '../services/api'
import '../styles/NeuroionTelegramStep.css'

function NeuroionTelegramStep({ onComplete, onBack, initialData }) {
  const saved = initialData || {}
  const [botUsername, setBotUsername] = useState(null)
  const [botConnected, setBotConnected] = useState(null)
  const [enabled, setEnabled] = useState(saved.enabled ?? true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

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

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    setSuccess(false)
    try {
      const payload = {
        enabled,
        dm_policy: 'pairing',
      }
      const res = await saveNeuroionChannels(payload)
      if (!res.success) {
        setError(res.message || 'Kon Telegram instellingen niet opslaan.')
        setLoading(false)
        return
      }
      setSuccess(true)
      onComplete?.(payload)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Kon Telegram instellingen niet opslaan.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="neuroion-telegram-step">
      <div className="config-header">
        <h3>Telegram</h3>
        <p>Telegram is het enige chatkanaal voor Neuroion.</p>
      </div>
      <form onSubmit={handleSubmit} className="telegram-form">
        <div className="telegram-card">
          <div className="telegram-row">
            <span>Bot</span>
            <strong>{botUsername ? `@${botUsername}` : 'Niet ingesteld'}</strong>
          </div>
          {botConnected === false && (
            <p className="telegram-warning">
              Telegram-bot token ontbreekt. Voeg deze toe aan de omgeving om Telegram te activeren.
            </p>
          )}
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              disabled={loading || success}
            />
            <span>Telegram kanaal inschakelen</span>
          </label>
          <p className="telegram-help">
            Gebruik DM policy “pairing” voor veilige toegang. Andere kanalen worden niet aangeboden.
          </p>
        </div>
        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">Telegram instellingen opgeslagen.</div>}
        <div className="form-actions">
          {onBack && (
            <button type="button" className="btn-secondary" onClick={onBack}>
              Back
            </button>
          )}
          <button
            type="button"
            className="btn-secondary"
            onClick={() => onComplete?.({ skip: true })}
            disabled={loading || success}
          >
            Standaard gebruiken
          </button>
          <button type="submit" className="btn-primary" disabled={loading || success}>
            {loading ? 'Opslaan…' : 'Doorgaan'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default NeuroionTelegramStep
