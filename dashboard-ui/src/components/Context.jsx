import React, { useState, useEffect } from 'react'
import { getContextList, deleteContext, addContext } from '../services/api'
import './Context.css'

function Context({ userId }) {
  const [snapshots, setSnapshots] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [newSummary, setNewSummary] = useState('')
  const [adding, setAdding] = useState(false)

  useEffect(() => {
    loadContext()
  }, [userId])

  const loadContext = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getContextList(50)
      setSnapshots(data.snapshots || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load context')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = async (e) => {
    e.preventDefault()
    if (!newSummary.trim()) return

    setAdding(true)
    setError(null)
    try {
      await addContext(newSummary.trim())
      setNewSummary('')
      await loadContext()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add context')
    } finally {
      setAdding(false)
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Remove this context?')) return
    try {
      await deleteContext(id)
      await loadContext()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete')
    }
  }

  const formatDate = (ts) => {
    if (!ts) return ''
    const d = new Date(ts)
    return d.toLocaleString(undefined, {
      dateStyle: 'short',
      timeStyle: 'short',
    })
  }

  if (loading) {
    return (
      <div className="context">
        <div className="context-loading">Loading context...</div>
      </div>
    )
  }

  return (
    <div className="context">
      <div className="context-header">
        <h2 className="context-title">Context</h2>
        <p className="context-description">
          Notes and events used to personalize your experience. Add notes or remove items you no longer need.
        </p>
      </div>

      {error && <div className="context-error">{error}</div>}

      <form onSubmit={handleAdd} className="context-add-form">
        <input
          type="text"
          className="context-input"
          placeholder="Add a note (e.g. Working from home today)"
          value={newSummary}
          onChange={(e) => setNewSummary(e.target.value)}
        />
        <button type="submit" className="context-add-button" disabled={adding}>
          {adding ? 'Adding...' : 'Add'}
        </button>
      </form>

      <div className="context-list">
        {snapshots.length === 0 ? (
          <div className="context-empty">No context yet. Add a note above.</div>
        ) : (
          snapshots.map((s) => (
            <div key={s.id} className="context-item">
              <div className="context-item-main">
                <span className="context-item-type">{s.event_type}</span>
                {s.event_subtype && (
                  <span className="context-item-subtype">{s.event_subtype}</span>
                )}
                <p className="context-item-summary">{s.summary}</p>
                <time className="context-item-time">{formatDate(s.timestamp)}</time>
              </div>
              <button
                type="button"
                className="context-item-delete"
                onClick={() => handleDelete(s.id)}
                title="Remove"
              >
                ×
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default Context
