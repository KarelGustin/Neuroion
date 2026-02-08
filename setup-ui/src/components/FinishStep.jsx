import React, { useState } from 'react'
import { markSetupComplete } from '../services/api'
import '../styles/FinishStep.css'

/**
 * Finish step: "You're all set" and call POST /setup/complete, then onComplete.
 */
function FinishStep({ onComplete, onBack }) {
  const [status, setStatus] = useState('idle') // idle | submitting | done | error
  const [error, setError] = useState(null)

  const handleFinish = async () => {
    setStatus('submitting')
    setError(null)
    try {
      await markSetupComplete()
      setStatus('done')
      if (onComplete) setTimeout(() => onComplete(), 1200)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Could not complete setup.')
      setStatus('error')
    }
  }

  return (
    <div className="finish-step">
      <div className="config-header">
        <h3>You are all set</h3>
        <p>Tap Finish to complete setup. We will start Neuroion Agent and switch to your Wi‑Fi.</p>
      </div>
      {status === 'idle' && (
        <div className="form-actions">
          {onBack && (
            <button type="button" className="btn-secondary" onClick={onBack}>
              Back
            </button>
          )}
          <button type="button" className="btn-primary" onClick={handleFinish}>
            Finish
          </button>
        </div>
      )}
      {status === 'submitting' && <p className="finish-status">Completing setup…</p>}
      {status === 'done' && <p className="finish-done">Setup complete.</p>}
      {status === 'error' && (
        <>
          <p className="finish-error">{error}</p>
          <button type="button" className="btn-primary" onClick={handleFinish}>
            Retry
          </button>
        </>
      )}
    </div>
  )
}

export default FinishStep
