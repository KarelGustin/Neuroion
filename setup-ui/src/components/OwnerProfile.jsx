import React, { useState } from 'react'
import { setupOwner } from '../services/api'
import '../styles/OwnerProfile.css'

function OwnerProfile({ onComplete, onBack, initialData }) {
  const loadFromStorage = () => {
    try {
      const saved = localStorage.getItem('neuroion_setup_owner')
      if (saved) {
        return JSON.parse(saved)
      }
    } catch (err) {
      console.error('Failed to load owner profile from storage:', err)
    }
    return null
  }

  const savedData = initialData || loadFromStorage()
  const [name, setName] = useState(savedData?.name || '')
  const [language, setLanguage] = useState(savedData?.language || 'nl')
  const [timezone, setTimezone] = useState(savedData?.timezone || 'Europe/Amsterdam')
  
  // Communication style preferences (multiple choice)
  const [communicationStyles, setCommunicationStyles] = useState(
    savedData?.communicationStyles || []
  )
  
  // Interests/preferences (multiple choice)
  const [interests, setInterests] = useState(savedData?.interests || [])
  
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)
  
  // Available options
  const communicationStyleOptions = [
    { value: 'short', label: 'Short & concise' },
    { value: 'normal', label: 'Normal length' },
    { value: 'detailed', label: 'Detailed explanations' },
    { value: 'formal', label: 'Formal tone' },
    { value: 'casual', label: 'Casual tone' },
  ]
  
  const interestOptions = [
    { value: 'cooking', label: 'Cooking' },
    { value: 'fitness', label: 'Fitness & Health' },
    { value: 'technology', label: 'Technology' },
    { value: 'reading', label: 'Reading' },
    { value: 'music', label: 'Music' },
    { value: 'travel', label: 'Travel' },
    { value: 'sports', label: 'Sports' },
    { value: 'gaming', label: 'Gaming' },
    { value: 'art', label: 'Art & Creativity' },
    { value: 'home_automation', label: 'Home Automation' },
  ]
  
  const toggleCommunicationStyle = (value) => {
    setCommunicationStyles((prev) =>
      prev.includes(value)
        ? prev.filter((v) => v !== value)
        : [...prev, value]
    )
  }
  
  const toggleInterest = (value) => {
    setInterests((prev) =>
      prev.includes(value)
        ? prev.filter((v) => v !== value)
        : [...prev, value]
    )
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(false)

    try {
      // Prepare style_prefs and preferences
      const style_prefs = {
        communication_styles: communicationStyles,
      }
      const preferences = {
        interests: interests,
      }
      
      const result = await setupOwner(name, language, timezone, style_prefs, preferences)
      if (result.success) {
        setSuccess(true)
        const ownerData = {
          name,
          language,
          timezone,
          communicationStyles,
          interests,
          style_prefs,
          preferences,
        }
        try {
          localStorage.setItem('neuroion_setup_owner', JSON.stringify(ownerData))
        } catch (err) {
          console.error('Failed to save owner profile:', err)
        }
        setTimeout(() => {
          onComplete(ownerData)
        }, 1000)
      } else {
        setError(result.message || 'Failed to setup owner profile')
      }
    } catch (err) {
      setError(err.message || 'Failed to setup owner profile')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="owner-profile">
      <div className="config-header">
        <h3>Owner Profile</h3>
        <p>Set up your profile as the household owner</p>
      </div>

      <form onSubmit={handleSubmit} className="owner-form">
        <div className="form-group">
          <label htmlFor="name">Your Name *</label>
          <input
            type="text"
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="Enter your name"
            disabled={loading || success}
          />
        </div>

        <div className="form-group">
          <label htmlFor="language">Language</label>
          <select
            id="language"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            disabled={loading || success}
          >
            <option value="nl">Nederlands</option>
            <option value="en">English</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="timezone">Timezone</label>
          <select
            id="timezone"
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
            disabled={loading || success}
          >
            <option value="Europe/Amsterdam">Europe/Amsterdam</option>
            <option value="Europe/London">Europe/London</option>
            <option value="America/New_York">America/New_York</option>
            <option value="America/Los_Angeles">America/Los_Angeles</option>
          </select>
        </div>

        <div className="form-group">
          <label>Communication Style *</label>
          <p className="form-help">Select one or more communication preferences</p>
          <div className="checkbox-group">
            {communicationStyleOptions.map((option) => (
              <label key={option.value} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={communicationStyles.includes(option.value)}
                  onChange={() => toggleCommunicationStyle(option.value)}
                  disabled={loading || success}
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label>Interests & Preferences</label>
          <p className="form-help">Select your interests (optional)</p>
          <div className="checkbox-group">
            {interestOptions.map((option) => (
              <label key={option.value} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={interests.includes(option.value)}
                  onChange={() => toggleInterest(option.value)}
                  disabled={loading || success}
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        </div>

        {error && <div className="error-message">{error}</div>}
        {success && (
          <div className="success-message">Owner profile created successfully!</div>
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
            disabled={loading || success || !name || communicationStyles.length === 0}
          >
            {loading ? 'Creating...' : success ? 'Success!' : 'Continue'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default OwnerProfile
