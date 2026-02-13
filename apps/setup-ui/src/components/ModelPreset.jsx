import React, { useState } from 'react'
import { setupModelChoice } from '../services/api'
import '../styles/ModelPreset.css'

const OPTIONS = {
  local: {
    name: 'Ollama 3.2 3B (local)',
    description: 'Runs on this device, works offline',
    model: 'llama3.2:3b',
    disabled: false,
  },
  openai: {
    name: 'OpenAI API',
    description: 'Use your OpenAI API key',
    model: null,
    disabled: false,
  },
  custom: {
    name: 'OpenAI-compatible API',
    description: 'Use any OpenAI-compatible API endpoint',
    model: null,
    disabled: false,
  },
}

function ModelPreset({ onComplete, onBack, initialData }) {
  const loadFromStorage = () => {
    try {
      const saved = localStorage.getItem('neuroion_setup_model')
      if (saved) {
        return JSON.parse(saved)
      }
    } catch (err) {
      console.error('Failed to load model choice from storage:', err)
    }
    return null
  }

  const savedData = initialData || loadFromStorage()
  const initialChoice = savedData?.choice ?? savedData?.preset ?? 'local'
  const [choice, setChoice] = useState(OPTIONS[initialChoice] ? initialChoice : 'local')
  const [apiKey, setApiKey] = useState(savedData?.api_key ? '••••••••••••' : '')
  const [customModel, setCustomModel] = useState(savedData?.model ?? 'gpt-4o-mini')
  const [customBaseUrl, setCustomBaseUrl] = useState(
    savedData?.base_url ?? 'https://api.openai.com/v1',
  )
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)
  const [testResult, setTestResult] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(false)
    setTestResult(null)

    try {
      const options = {}
      if (choice === 'openai' || choice === 'custom') {
        const key = apiKey.trim()
        if (!key && savedData?.api_key !== '(saved)') {
          setError('Please enter your OpenAI API key.')
          setLoading(false)
          return
        }
        if (key && key !== '••••••••••••') options.api_key = key
        if (customModel.trim()) options.model = customModel.trim()
        if (choice === 'custom' && customBaseUrl.trim()) {
          options.base_url = customBaseUrl.trim()
        }
      }
      const result = await setupModelChoice(choice, options)
      if (result.success) {
        setSuccess(true)
        setTestResult(result.message)
        const modelData = { choice, model_name: result.model_name }
        if ((choice === 'openai' || choice === 'custom') && apiKey && apiKey !== '••••••••••••') {
          modelData.model = customModel
          if (choice === 'custom') {
            modelData.base_url = customBaseUrl
          }
          modelData.api_key = '(saved)'
        }
        try {
          localStorage.setItem('neuroion_setup_model', JSON.stringify(modelData))
        } catch (err) {
          console.error('Failed to save model choice:', err)
        }
        setTimeout(() => {
          onComplete(modelData)
        }, 1500)
      } else {
        setError(result.message || 'Failed to configure model')
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to configure model')
    } finally {
      setLoading(false)
    }
  }

  const showApiFields = choice === 'openai' || choice === 'custom'
  const showBaseUrl = choice === 'custom'

  return (
    <div className="model-preset">
      <div className="config-header">
        <h3>AI model</h3>
        <p>Kies lokaal (Ollama 3.2 3B) of een API-provider.</p>
      </div>

      <form onSubmit={handleSubmit} className="preset-form">
        <div className="preset-selection">
          {Object.entries(OPTIONS).map(([key, info]) => (
            <label
              key={key}
              className={`preset-option ${info.disabled ? 'preset-option--disabled' : ''}`}
            >
              <input
                type="radio"
                name="choice"
                value={key}
                checked={choice === key}
                onChange={(e) => !info.disabled && setChoice(e.target.value)}
                disabled={loading || success || info.disabled}
              />
              <div className="preset-content">
                <strong>{info.name}</strong>
                <span>{info.description}</span>
                {info.model && <span className="preset-model">Model: {info.model}</span>}
              </div>
            </label>
          ))}
        </div>

        {showApiFields && (
          <div className="custom-fields">
            <label>
              <span>OpenAI API key</span>
              <input
                type="password"
                placeholder={savedData?.api_key === '(saved)' ? 'Leave blank to keep saved key' : 'sk-...'}
                value={apiKey === '••••••••••••' ? '' : apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                disabled={loading || success}
                autoComplete="off"
              />
            </label>
            <label>
              <span>Model (optional)</span>
              <input
                type="text"
                placeholder="gpt-4o-mini"
                value={customModel}
                onChange={(e) => setCustomModel(e.target.value)}
                disabled={loading || success}
              />
            </label>
            {showBaseUrl && (
              <label>
                <span>Base URL</span>
                <input
                  type="text"
                  placeholder="https://api.openai.com/v1"
                  value={customBaseUrl}
                  onChange={(e) => setCustomBaseUrl(e.target.value)}
                  disabled={loading || success}
                />
              </label>
            )}
          </div>
        )}

        {error && <div className="error-message">{error}</div>}
        {success && (
          <div className="success-message">
            Model configured successfully!
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
