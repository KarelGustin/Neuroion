import React, { useState, useMemo } from 'react'
import { saveNeuroionGateway } from '../services/api'
import '../styles/NeuroionGatewayStep.css'

const BIND_OPTIONS = [
  { value: 'lan', label: 'LAN (recommended)' },
  { value: 'loopback', label: 'Local only' },
  { value: 'auto', label: 'Auto' },
]

function generateToken() {
  const bytes = new Uint8Array(24)
  window.crypto.getRandomValues(bytes)
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

function NeuroionGatewayStep({ onComplete, onBack, initialData }) {
  const saved = initialData || {}
  const [port, setPort] = useState(saved.port ?? 3141)
  const [bind, setBind] = useState(saved.bind ?? 'lan')
  const [token, setToken] = useState(saved.token ?? '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  const tokenValue = useMemo(() => token || generateToken(), [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    setSuccess(false)
    try {
      const gatewayPayload = {
        port: Number(port) || 3141,
        bind,
        token: tokenValue,
      }
      const res = await saveNeuroionGateway(gatewayPayload)
      if (!res.success) {
        setError(res.message || 'Kon gateway instellingen niet opslaan.')
        setLoading(false)
        return
      }
      setSuccess(true)
      onComplete?.(gatewayPayload)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Kon gateway instellingen niet opslaan.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="neuroion-gateway-step">
      <div className="config-header">
        <h3>Gateway basics</h3>
        <p>Configureer de Neuroion gateway (poort, bereik en toegangstoken).</p>
      </div>
      <form onSubmit={handleSubmit} className="gateway-form">
        <div className="form-group">
          <label htmlFor="gateway-port">Gateway port</label>
          <input
            type="number"
            id="gateway-port"
            value={port}
            onChange={(e) => setPort(e.target.value)}
            min={1}
            max={65535}
            disabled={loading || success}
          />
        </div>
        <div className="form-group">
          <label htmlFor="gateway-bind">Bind</label>
          <select
            id="gateway-bind"
            value={bind}
            onChange={(e) => setBind(e.target.value)}
            disabled={loading || success}
          >
            {BIND_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label htmlFor="gateway-token">Access token</label>
          <input
            type="text"
            id="gateway-token"
            value={tokenValue}
            readOnly
          />
          <p className="form-help">
            Dit token is nodig om de Neuroion UI te openen.
          </p>
        </div>
        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">Gateway opgeslagen.</div>}
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

export default NeuroionGatewayStep
