import React, { useState, useEffect } from 'react'
import { validateSetup, applyWifi } from '../services/api'
import '../styles/ValidateStep.css'

/**
 * Validate step: check connection, optionally apply WiFi and switch to LAN.
 * Shows clear errors; on WiFi failure: "Could not join network. Try again or skip."
 */
function ValidateStep({ onComplete, onBack }) {
  const [status, setStatus] = useState('idle') // idle | checking | applying | success | error
  const [error, setError] = useState(null)
  const [networkOk, setNetworkOk] = useState(false)
  const [modelOk, setModelOk] = useState(false)

  const runValidate = async () => {
    setStatus('checking')
    setError(null)
    try {
      const res = await validateSetup()
      setNetworkOk(res.network_ok)
      setModelOk(res.model_ok)
      if (res.error) setError(res.error)
      setStatus('idle')
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Validation failed')
      setStatus('error')
    }
  }

  const runApplyWifi = async () => {
    setStatus('applying')
    setError(null)
    try {
      const res = await applyWifi()
      if (res.success) {
        setStatus('success')
        setNetworkOk(true)
        setTimeout(() => onComplete?.({ validated: true }), 1500)
      } else {
        setError(res.message || 'Could not join network. Try again or skip.')
        setStatus('error')
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Could not join network. Try again or skip.')
      setStatus('error')
    }
  }

  useEffect(() => {
    runValidate()
  }, [])

  return (
    <div className="validate-step">
      <div className="config-header">
        <h3>Checking connection</h3>
        <p>Verifying network and model.</p>
      </div>
      {status === 'checking' && (
        <p className="validate-status">Checking…</p>
      )}
      {status === 'applying' && (
        <p className="validate-status">Connecting to Wi‑Fi…</p>
      )}
      {status === 'success' && (
        <p className="validate-success">All set. Continuing…</p>
      )}
      {status === 'error' && error && (
        <p className="validate-error">{error}</p>
      )}
      {status === 'idle' && (
        <>
          <p className="validate-result">
            Network: {networkOk ? 'OK' : 'Not connected'} · Model: {modelOk ? 'OK' : 'Not checked or failed'}
          </p>
          <div className="form-actions">
            {onBack && (
              <button type="button" className="btn-secondary" onClick={onBack}>
                Back
              </button>
            )}
            <button
              type="button"
              className="btn-primary"
              onClick={runApplyWifi}
            >
              Connect to home Wi‑Fi
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => onComplete?.({ validated: true, skipped: true })}
            >
              Skip
            </button>
          </div>
        </>
      )}
    </div>
  )
}

export default ValidateStep
