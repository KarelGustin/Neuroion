import React, { useState } from 'react'
import { setupDevice, setupHousehold } from '../services/api'
import '../styles/DeviceHouseholdStep.css'

const TIMEZONES = [
  'Europe/Amsterdam',
  'Europe/Brussels',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'America/New_York',
  'America/Los_Angeles',
  'Asia/Tokyo',
  'Australia/Sydney',
]

function DeviceHouseholdStep({ onComplete, onBack, initialData }) {
  const saved = initialData || {}
  const [deviceName, setDeviceName] = useState(saved.device_name ?? 'Neuroion Core')
  const [timezone, setTimezone] = useState(saved.timezone ?? 'Europe/Amsterdam')
  const [householdName, setHouseholdName] = useState(saved.householdName ?? '')
  const [ownerName, setOwnerName] = useState(saved.ownerName ?? '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    const trimmedDeviceName = (deviceName || 'Neuroion Core').trim()
    const trimmedHousehold = (householdName || '').trim()
    const trimmedOwner = (ownerName || '').trim()
    if (!trimmedDeviceName) {
      setError('Vul een apparaatnaam in.')
      return
    }
    if (!trimmedHousehold) {
      setError('Vul een huishoudnaam in.')
      return
    }
    if (!trimmedOwner) {
      setError('Vul je naam in.')
      return
    }
    setLoading(true)
    try {
      const deviceRes = await setupDevice(trimmedDeviceName, timezone)
      if (!deviceRes.success) {
        setError(deviceRes.message || 'Kon apparaatinstellingen niet opslaan.')
        setLoading(false)
        return
      }
      const householdRes = await setupHousehold(trimmedHousehold, trimmedOwner)
      if (!householdRes.success) {
        setError(householdRes.message || 'Kon household niet instellen.')
        setLoading(false)
        return
      }
      const data = {
        device_name: trimmedDeviceName,
        timezone,
        householdName: trimmedHousehold,
        ownerName: trimmedOwner,
        householdId: householdRes.household_id,
        userId: householdRes.user_id,
      }
      try {
        localStorage.setItem('neuroion_setup_core', JSON.stringify(data))
      } catch (_) {}
      onComplete?.(data)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Kon setup niet opslaan.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="device-household-step">
      <div className="config-header">
        <h3>Basic settings</h3>
        <p>Set up your device and household for Neuroion.</p>
      </div>
      <form onSubmit={handleSubmit} className="device-household-form">
        <div className="form-group">
          <label htmlFor="device-name">Device name</label>
          <input
            type="text"
            id="device-name"
            value={deviceName}
            onChange={(e) => setDeviceName(e.target.value)}
            placeholder="Neuroion Core"
            maxLength={64}
            disabled={loading}
          />
        </div>
        <div className="form-group">
          <label htmlFor="timezone">Your timezone</label>
          <select
            id="timezone"
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
            disabled={loading}
          >
            {TIMEZONES.map((tz) => (
              <option key={tz} value={tz}>
                {tz}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label htmlFor="household-name">Household name</label>
          <input
            type="text"
            id="household-name"
            value={householdName}
            onChange={(e) => setHouseholdName(e.target.value)}
            placeholder="e.g. Family Jansen"
            disabled={loading}
          />
        </div>
        <div className="form-group">
          <label htmlFor="owner-name">Your name</label>
          <input
            type="text"
            id="owner-name"
            value={ownerName}
            onChange={(e) => setOwnerName(e.target.value)}
            placeholder="e.g. Karel"
            disabled={loading}
          />
        </div>
        {error && <div className="error-message">{error}</div>}
        <div className="form-actions">
          {onBack && (
            <button type="button" className="btn-secondary" onClick={onBack}>
              Back
            </button>
          )}
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Saving...' : 'Continue'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default DeviceHouseholdStep
