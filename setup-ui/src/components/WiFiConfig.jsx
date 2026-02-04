import React, { useState } from 'react'
import { configureWiFi } from '../services/api'
import '../styles/WiFiConfig.css'

function WiFiConfig({ onComplete, onBack, initialData }) {
  const [ssid, setSsid] = useState(initialData?.ssid || '')
  const [password, setPassword] = useState(initialData?.password || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(false)

    try {
      const result = await configureWiFi(ssid, password)
      if (result.success) {
        setSuccess(true)
        setTimeout(() => {
          onComplete({ ssid, password })
        }, 1000)
      } else {
        setError(result.message || 'Failed to configure WiFi')
      }
    } catch (err) {
      setError(err.message || 'Failed to configure WiFi')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="wifi-config">
      <div className="config-header">
        <h3>WiFi Configuration</h3>
        <p>Connect your Neuroion Homebase to your WiFi network</p>
      </div>

      <form onSubmit={handleSubmit} className="wifi-form">
        <div className="form-group">
          <label htmlFor="ssid">Network Name (SSID)</label>
          <input
            type="text"
            id="ssid"
            value={ssid}
            onChange={(e) => setSsid(e.target.value)}
            required
            placeholder="Enter WiFi network name"
            disabled={loading || success}
          />
        </div>

        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            placeholder="Enter WiFi password"
            disabled={loading || success}
          />
        </div>

        {error && <div className="error-message">{error}</div>}
        {success && (
          <div className="success-message">WiFi configured successfully!</div>
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
            disabled={loading || success || !ssid || !password}
          >
            {loading ? 'Configuring...' : success ? 'Success!' : 'Continue'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default WiFiConfig
