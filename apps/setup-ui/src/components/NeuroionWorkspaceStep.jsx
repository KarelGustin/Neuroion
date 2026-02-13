import React, { useState } from 'react'
import { saveNeuroionWorkspace } from '../services/api'
import '../styles/NeuroionWorkspaceStep.css'

const DEFAULT_WORKSPACE = '~/.neuroion/workspace'

function NeuroionWorkspaceStep({ onComplete, onBack, initialData }) {
  const saved = initialData || {}
  const [workspace, setWorkspace] = useState(saved.workspace ?? DEFAULT_WORKSPACE)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    setSuccess(false)
    try {
      const trimmed = (workspace || '').trim() || DEFAULT_WORKSPACE
      const res = await saveNeuroionWorkspace({ workspace: trimmed })
      if (!res.success) {
        setError(res.message || 'Kon workspace niet opslaan.')
        setLoading(false)
        return
      }
      setSuccess(true)
      onComplete?.({ workspace: trimmed })
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Kon workspace niet opslaan.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="neuroion-workspace-step">
      <div className="config-header">
        <h3>Workspace</h3>
        <p>Waar Neuroion je bestanden en sessies bewaart.</p>
      </div>
      <form onSubmit={handleSubmit} className="workspace-form">
        <div className="form-group">
          <label htmlFor="workspace-path">Workspace path</label>
          <input
            type="text"
            id="workspace-path"
            value={workspace}
            onChange={(e) => setWorkspace(e.target.value)}
            placeholder={DEFAULT_WORKSPACE}
            disabled={loading || success}
          />
        </div>
        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">Workspace opgeslagen.</div>}
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

export default NeuroionWorkspaceStep
