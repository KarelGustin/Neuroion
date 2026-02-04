import React, { useState } from 'react'
import { setupModelPreset } from '../services/api'
import '../styles/ModelPreset.css'

function ModelPreset({ onComplete, onBack, initialData }) {
  const loadFromStorage = () => {
    try {
      const saved = localStorage.getItem('neuroion_setup_model')
      if (saved) {
        return JSON.parse(saved)
      }
    } catch (err) {
      console.error('Failed to load model preset from storage:', err)
    }
    return null
  }

  const savedData = initialData || loadFromStorage()
  const [preset, setPreset] = useState(savedData?.preset || 'balanced')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)
  const [testResult, setTestResult] = useState(null)

  const presets = {
    fast: {
      name: 'Fast',
      description: 'Smaller model, faster responses',
      model: 'llama3.2:1b',
    },
    balanced: {
      name: 'Balanced',
      description: 'Good balance of speed and quality',
      model: 'llama3.2',
    },
    quality: {
      name: 'Quality',
      description: 'Larger model, higher quality responses',
      model: 'llama3.2:3b',
    },
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(false)
    setTestResult(null)

    try {
      const result = await setupModelPreset(preset)
      if (result.success) {
        setSuccess(true)
        setTestResult(result.message)
        const modelData = { preset, model_name: result.model_name }
        try {
          localStorage.setItem('neuroion_setup_model', JSON.stringify(modelData))
        } catch (err) {
          console.error('Failed to save model preset:', err)
        }
        setTimeout(() => {
          onComplete(modelData)
        }, 1500)
      } else {
        setError(result.message || 'Failed to configure model preset')
      }
    } catch (err) {
      setError(err.message || 'Failed to configure model preset')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="model-preset">
      <div className="config-header">
        <h3>LLM Model Preset</h3>
        <p>Choose the model preset that best fits your needs</p>
      </div>

      <form onSubmit={handleSubmit} className="preset-form">
        <div className="preset-selection">
          {Object.entries(presets).map(([key, presetInfo]) => (
            <label key={key} className="preset-option">
              <input
                type="radio"
                name="preset"
                value={key}
                checked={preset === key}
                onChange={(e) => setPreset(e.target.value)}
                disabled={loading || success}
              />
              <div className="preset-content">
                <strong>{presetInfo.name}</strong>
                <span>{presetInfo.description}</span>
                <span className="preset-model">Model: {presetInfo.model}</span>
              </div>
            </label>
          ))}
        </div>

        {error && <div className="error-message">{error}</div>}
        {success && (
          <div className="success-message">
            Model preset configured successfully!
            {testResult && <div className="test-result">{testResult}</div>}
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
            disabled={loading || success}
          >
            {loading ? 'Configuring...' : success ? 'Success!' : 'Continue'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default ModelPreset
