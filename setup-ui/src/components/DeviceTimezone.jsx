import React, { useState } from 'react'
import { setupDevice } from '../services/api'
import '../styles/DeviceTimezone.css'

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

function DeviceTimezone({ onComplete, onBack, initialData }) {
  const [deviceName, setDeviceName] = useState(initialData?.device_name ?? 'Neuroion Core')
  const [timezone, setTimezone] = useState(initialData?.timezone ?? 'Europe/Amsterdam')
  const [error, setError] = useState(null)

  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    const name = (deviceName || 'Neuroion Core').trim()
    if (!name) {
      setError('Please enter a device name.')
      return
    }
    setLoading(true)
    try {
      const res = await setupDevice(name, timezone)
      if (res.success) {
        onComplete?.({ device_name: name, timezone })
      } else {
        setError(res.message || 'Failed to save')
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to save')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="device-timezone">
      <div className="config-header">
        <h3>Device & timezone</h3>
        <p>Name your Neuroion Core and set your timezone.</p>
      </div>
      <form onSubmit={handleSubmit}>
        <label className="field-label">Device name</label>
        <input
          type="text"
          className="field-input"
          value={deviceName}
          onChange={(e) => setDeviceName(e.target.value)}
          placeholder="Neuroion Core"
          maxLength={64}
        />
        <label className="field-label">Timezone</label>
        <select
          className="field-select"
          value={timezone}
          onChange={(e) => setTimezone(e.target.value)}
        >
          {TIMEZONES.map((tz) => (
            <option key={tz} value={tz}>{tz}</option>
          ))}
        </select>
        {error && <p className="field-error">{error}</p>}
        <div className="form-actions">
          {onBack && (
            <button type="button" className="btn-secondary" onClick={onBack}>
              Back
            </button>
          )}
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Saving…' : 'Continue'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default DeviceTimezone
