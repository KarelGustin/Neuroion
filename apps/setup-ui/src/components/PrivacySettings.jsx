import React, { useState } from 'react'
import '../styles/PrivacySettings.css'

function PrivacySettings({ onComplete, onBack, initialData }) {
  const loadFromStorage = () => {
    try {
      const saved = localStorage.getItem('neuroion_setup_privacy')
      if (saved) {
        return JSON.parse(saved)
      }
    } catch (err) {
      console.error('Failed to load privacy settings from storage:', err)
    }
    return null
  }

  const savedData = initialData || loadFromStorage()
  const [retentionDays, setRetentionDays] = useState(savedData?.retentionDays || 365)
  const [autoDelete, setAutoDelete] = useState(savedData?.autoDelete ?? true)
  
  // Available options
  const dataStorageOptions = [
    { value: 'location', label: 'Location summaries (arriving/leaving home)' },
    { value: 'health', label: 'Health summaries (sleep scores, recovery levels)' },
    { value: 'preferences', label: 'User preferences and settings' },
    { value: 'chat_history', label: 'Chat conversation history' },
    { value: 'context', label: 'Context snapshots and summaries' },
  ]
  
  const consentOptionsList = [
    { value: 'data_retention', label: 'I consent to local data retention' },
    { value: 'analytics', label: 'I consent to anonymous usage analytics (optional)' },
    { value: 'improvements', label: 'I consent to data being used for service improvements' },
    { value: 'backup', label: 'I consent to local backups of my data' },
  ]
  
  // Data storage preferences (multiple choice) - all checked by default
  const defaultDataStorage = dataStorageOptions.map(opt => opt.value)
  const [dataStorage, setDataStorage] = useState(
    savedData?.dataStorage || defaultDataStorage
  )
  
  // Privacy consent options (multiple choice) - all checked by default
  const defaultConsentOptions = consentOptionsList.map(opt => opt.value)
  const [consentOptions, setConsentOptions] = useState(
    savedData?.consentOptions || defaultConsentOptions
  )
  
  const toggleDataStorage = (value) => {
    setDataStorage((prev) =>
      prev.includes(value)
        ? prev.filter((v) => v !== value)
        : [...prev, value]
    )
  }
  
  const toggleConsent = (value) => {
    setConsentOptions((prev) =>
      prev.includes(value)
        ? prev.filter((v) => v !== value)
        : [...prev, value]
    )
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const privacyData = {
      retentionDays,
      autoDelete,
      dataStorage,
      consentOptions,
      // Backward compatibility
      storeLocation: dataStorage.includes('location'),
      storeHealth: dataStorage.includes('health'),
      retention_policy: {
        days: retentionDays,
        auto_delete: autoDelete,
      },
      consent: {
        data_retention: consentOptions.includes('data_retention'),
        analytics: consentOptions.includes('analytics'),
        improvements: consentOptions.includes('improvements'),
        backup: consentOptions.includes('backup'),
      },
    }
    try {
      localStorage.setItem('neuroion_setup_privacy', JSON.stringify(privacyData))
    } catch (err) {
      console.error('Failed to save privacy settings:', err)
    }
    onComplete(privacyData)
  }

  return (
    <div className="privacy-settings">
      <div className="config-header">
        <h3>Services & privacy</h3>
        <p>Core services are enabled by default. Choose how data is stored and retained.</p>
      </div>

      <form onSubmit={handleSubmit} className="privacy-form">
        <div className="form-group">
          <label htmlFor="retention-days">Data Retention Period (days)</label>
          <input
            type="number"
            id="retention-days"
            value={retentionDays}
            onChange={(e) => setRetentionDays(parseInt(e.target.value))}
            min="1"
            max="3650"
            required
          />
          <p className="form-help">Data older than this will be automatically deleted</p>
        </div>

        <div className="form-group checkbox-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={autoDelete}
              onChange={(e) => setAutoDelete(e.target.checked)}
            />
            <span>Automatically delete old data</span>
          </label>
        </div>

        <div className="form-group">
          <h4>What is stored locally: *</h4>
          <p className="form-help">Uncheck any data types you don't want to store (all enabled by default)</p>
          <div className="checkbox-group">
            {dataStorageOptions.map((option) => (
              <label key={option.value} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={dataStorage.includes(option.value)}
                  onChange={() => toggleDataStorage(option.value)}
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
          <p className="form-help">
            Note: Neuroion never stores raw health data, only derived summaries.
          </p>
        </div>

        <div className="form-group">
          <h4>Privacy Consent</h4>
          <p className="form-help">Uncheck any consents you don't want to grant (all enabled by default)</p>
          <div className="checkbox-group">
            {consentOptionsList.map((option) => (
              <label key={option.value} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={consentOptions.includes(option.value)}
                  onChange={() => toggleConsent(option.value)}
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="form-actions">
          {onBack && (
            <button type="button" onClick={onBack} className="btn-secondary">
              Back
            </button>
          )}
          <button
            type="submit"
            className="btn-primary"
            disabled={dataStorage.length === 0}
          >
            Continue
          </button>
        </div>
      </form>
    </div>
  )
}

export default PrivacySettings
