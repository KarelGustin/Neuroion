import React, { useState, useEffect } from 'react'
import { getUserPreferences, setUserPreference, deleteUserPreference, getHouseholdPreferences } from '../services/api'
import './Preferences.css'

function Preferences({ userId }) {
  const [userPrefs, setUserPrefs] = useState([])
  const [householdPrefs, setHouseholdPrefs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('user') // 'user' or 'household'
  const [newKey, setNewKey] = useState('')
  const [newValue, setNewValue] = useState('')
  const [newCategory, setNewCategory] = useState('')
  const [adding, setAdding] = useState(false)

  useEffect(() => {
    loadPreferences()
  }, [userId])

  const loadPreferences = async () => {
    setLoading(true)
    setError(null)
    try {
      const [userData, householdData] = await Promise.all([
        getUserPreferences(userId),
        getHouseholdPreferences(),
      ])
      setUserPrefs(userData.preferences || [])
      setHouseholdPrefs(householdData.preferences || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load preferences')
    } finally {
      setLoading(false)
    }
  }

  const handleAddPreference = async (e) => {
    e.preventDefault()
    if (!newKey.trim()) {
      setError('Key is required')
      return
    }

    setAdding(true)
    setError(null)
    try {
      await setUserPreference(userId, newKey, newValue || '', newCategory || null)
      setNewKey('')
      setNewValue('')
      setNewCategory('')
      await loadPreferences()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add preference')
    } finally {
      setAdding(false)
    }
  }

  const handleDeletePreference = async (key) => {
    if (!window.confirm(`Delete preference "${key}"?`)) {
      return
    }

    try {
      await deleteUserPreference(userId, key)
      await loadPreferences()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete preference')
    }
  }

  const handleUpdatePreference = async (key, newValue) => {
    try {
      const pref = userPrefs.find(p => p.key === key)
      await setUserPreference(userId, key, newValue, pref?.category || null)
      await loadPreferences()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update preference')
    }
  }

  if (loading) {
    return (
      <div className="preferences">
        <div className="preferences-loading">Loading preferences...</div>
      </div>
    )
  }

  return (
    <div className="preferences">
      <div className="preferences-header">
        <h2 className="preferences-title">Preferences</h2>
        <div className="preferences-tabs">
          <button
            className={`preferences-tab ${activeTab === 'user' ? 'active' : ''}`}
            onClick={() => setActiveTab('user')}
          >
            Your Preferences
          </button>
          <button
            className={`preferences-tab ${activeTab === 'household' ? 'active' : ''}`}
            onClick={() => setActiveTab('household')}
          >
            Household (Read-only)
          </button>
        </div>
      </div>

      {error && (
        <div className="preferences-error">
          {error}
        </div>
      )}

      {activeTab === 'user' && (
        <div className="preferences-content">
          <form onSubmit={handleAddPreference} className="preferences-add-form">
            <input
              type="text"
              className="preferences-input"
              placeholder="Key"
              value={newKey}
              onChange={(e) => setNewKey(e.target.value)}
              required
            />
            <input
              type="text"
              className="preferences-input"
              placeholder="Value"
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
            />
            <input
              type="text"
              className="preferences-input"
              placeholder="Category (optional)"
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value)}
            />
            <button
              type="submit"
              className="preferences-add-button"
              disabled={adding}
            >
              {adding ? 'Adding...' : 'Add'}
            </button>
          </form>

          <div className="preferences-list">
            {userPrefs.length === 0 ? (
              <div className="preferences-empty">No user preferences yet</div>
            ) : (
              userPrefs.map((pref) => (
                <div key={pref.key} className="preference-item">
                  <div className="preference-key">{pref.key}</div>
                  <div className="preference-value">
                    <input
                      type="text"
                      className="preference-value-input"
                      value={typeof pref.value === 'object' ? JSON.stringify(pref.value) : String(pref.value || '')}
                      onChange={(e) => handleUpdatePreference(pref.key, e.target.value)}
                    />
                  </div>
                  {pref.category && (
                    <div className="preference-category">{pref.category}</div>
                  )}
                  <button
                    className="preference-delete"
                    onClick={() => handleDeletePreference(pref.key)}
                    title="Delete preference"
                  >
                    ×
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {activeTab === 'household' && (
        <div className="preferences-content">
          <div className="preferences-list">
            {householdPrefs.length === 0 ? (
              <div className="preferences-empty">No household preferences</div>
            ) : (
              householdPrefs.map((pref) => (
                <div key={pref.key} className="preference-item readonly">
                  <div className="preference-key">{pref.key}</div>
                  <div className="preference-value">
                    {typeof pref.value === 'object' ? JSON.stringify(pref.value) : String(pref.value || '')}
                  </div>
                  {pref.category && (
                    <div className="preference-category">{pref.category}</div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default Preferences
