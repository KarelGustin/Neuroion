import React, { useState } from 'react'
import { setupHousehold } from '../services/api'
import '../styles/HouseholdSetup.css'

function HouseholdSetup({ onComplete, onBack, initialData }) {
  const [householdName, setHouseholdName] = useState(
    initialData?.householdName || '',
  )
  const [ownerName, setOwnerName] = useState(initialData?.ownerName || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(false)

    try {
      const result = await setupHousehold(householdName, ownerName)
      if (result.success) {
        setSuccess(true)
        setTimeout(() => {
          onComplete({
            householdName,
            ownerName,
            householdId: result.household_id,
            userId: result.user_id,
          })
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
        <h3>Household Setup</h3>
        <p>Create your household and set up the first user (owner)</p>
      </div>

      <form onSubmit={handleSubmit} className="household-form">
        <div className="form-group">
          <label htmlFor="household-name">Household Name</label>
          <input
            type="text"
            id="household-name"
            value={householdName}
            onChange={(e) => setHouseholdName(e.target.value)}
            required
            placeholder="e.g., Smith Family"
            disabled={loading || success}
          />
        </div>

        <div className="form-group">
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
        </div>

        {error && <div className="error-message">{error}</div>}
        {success && (
          <div className="success-message">
            Household created successfully! Setup complete.
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
            disabled={loading || success || !householdName || !ownerName}
          >
            {loading ? 'Creating...' : success ? 'Complete!' : 'Finish Setup'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default HouseholdSetup
