import React, { useState } from 'react'
import { setupHousehold } from '../services/api'
import '../styles/HouseholdSetup.css'

function HouseholdSetup({ onComplete, onBack, initialData }) {
  // Load from localStorage if initialData is not provided
  const loadFromStorage = () => {
    try {
      const saved = localStorage.getItem('neuroion_setup_household')
      if (saved) {
        return JSON.parse(saved)
      }
    } catch (err) {
      console.error('Failed to load household config from storage:', err)
    }
    return null
  }

  const savedData = initialData || loadFromStorage()
  const [householdName, setHouseholdName] = useState(
    savedData?.householdName || '',
  )
  const [ownerName, setOwnerName] = useState(savedData?.ownerName || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(false)

    try {
      const result = await setupHousehold(householdName, ownerName || householdName || 'Owner')
      if (result.success) {
        setSuccess(true)
        const householdData = {
          householdName,
          ownerName: ownerName || 'Owner',
          householdId: result.household_id,
          userId: result.user_id,
        }
        // Save to localStorage (will be cleared by SetupWizard on completion)
        try {
          localStorage.setItem('neuroion_setup_household', JSON.stringify(householdData))
        } catch (err) {
          console.error('Failed to save household config:', err)
        }
        setTimeout(() => {
          onComplete(householdData)
        }, 1000)
      } else {
        setError(result.message || 'Failed to setup household')
      }
    } catch (err) {
      setError(err.message || 'Failed to setup household')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="household-setup">
      <div className="config-header">
        <h3>Your name</h3>
        <p>Create your account (single-user).</p>
      </div>

      <form onSubmit={handleSubmit} className="household-form">
        <div className="form-group">
          <label htmlFor="household-name">Your name</label>
          <input
            type="text"
            id="household-name"
            value={householdName}
            onChange={(e) => setHouseholdName(e.target.value)}
            required
            placeholder="e.g., Jan"
            disabled={loading || success}
          />
        </div>

        {/* <div className="form-group">
          <label htmlFor="owner-name">Owner Name</label>
          <input
            type="text"
            id="owner-name"
            value={ownerName}
            onChange={(e) => setOwnerName(e.target.value)}
            required
            placeholder="Your name"
            disabled={loading || success}
          />
        </div> */}

        {error && <div className="error-message">{error}</div>}
        {success && (
          <div className="success-message">
            Account created successfully! Setup complete.
          </div>
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
            disabled={loading || success || !householdName}
          >
            {loading ? 'Creating...' : success ? 'Complete!' : 'Continue'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default HouseholdSetup
