import React, { useState } from 'react'
import { configureLLM } from '../services/api'
import '../styles/LLMConfig.css'

function LLMConfig({ onComplete, onBack, initialData }) {
  const [provider, setProvider] = useState(initialData?.provider || 'local')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)
  const [testResult, setTestResult] = useState(null)

  // Custom API fields
  const [customApiKey, setCustomApiKey] = useState(initialData?.customApiKey || '')
  const [customBaseUrl, setCustomBaseUrl] = useState(
    initialData?.customBaseUrl || 'https://api.openai.com/v1',
  )
  const [customModel, setCustomModel] = useState(
    initialData?.customModel || 'gpt-3.5-turbo',
  )

  // Local Ollama fields
  const [ollamaUrl, setOllamaUrl] = useState(
    initialData?.ollamaUrl || 'http://localhost:11434',
  )
  const [ollamaModel, setOllamaModel] = useState(
    initialData?.ollamaModel || 'llama3.2',
  )

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(false)
    setTestResult(null)

    try {
      let config = {}

      if (provider === 'local') {
        config = {
          base_url: ollamaUrl,
          model: ollamaModel,
          timeout: 120,
        }
      } else if (provider === 'cloud') {
        config = {
          model: 'mistralai/Mixtral-8x7B-Instruct-v0.1',
          timeout: 120,
        }
      } else if (provider === 'custom') {
        if (!customApiKey) {
          setError('API key is required for custom provider')
          setLoading(false)
          return
        }
        config = {
          api_key: customApiKey,
          base_url: customBaseUrl,
          model: customModel,
          timeout: 120,
        }
      }

      const result = await configureLLM(provider, config)
      if (result.success) {
        setSuccess(true)
        setTestResult(result.test_result)
        setTimeout(() => {
          onComplete({
            provider,
            config,
            customApiKey,
            customBaseUrl,
            customModel,
            ollamaUrl,
            ollamaModel,
          })
        }, 1500)
      } else {
        setError(result.message || 'Failed to configure LLM')
      }
    } catch (err) {
      setError(err.message || 'Failed to configure LLM')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="llm-config">
      <div className="config-header">
        <h3>LLM Provider Configuration</h3>
        <p>Choose how Neuroion will process your requests</p>
      </div>

      <form onSubmit={handleSubmit} className="llm-form">
        <div className="provider-selection">
          <label className="radio-option">
            <input
              type="radio"
              name="provider"
              value="local"
              checked={provider === 'local'}
              onChange={(e) => setProvider(e.target.value)}
              disabled={loading || success}
            />
            <div className="radio-content">
              <strong>Local (Ollama)</strong>
              <span>Runs on your device, works offline</span>
            </div>
          </label>

          <label className="radio-option">
            <input
              type="radio"
              name="provider"
              value="cloud"
              checked={provider === 'cloud'}
              onChange={(e) => setProvider(e.target.value)}
              disabled={loading || success}
            />
            <div className="radio-content">
              <strong>Cloud (Free)</strong>
              <span>Uses free HuggingFace API, requires internet</span>
            </div>
          </label>

          <label className="radio-option">
            <input
              type="radio"
              name="provider"
              value="custom"
              checked={provider === 'custom'}
              onChange={(e) => setProvider(e.target.value)}
              disabled={loading || success}
            />
            <div className="radio-content">
              <strong>Custom API</strong>
              <span>Use your own OpenAI, Anthropic, or compatible API</span>
            </div>
          </label>
        </div>

        {provider === 'local' && (
          <div className="provider-config">
            <div className="form-group">
              <label htmlFor="ollama-url">Ollama URL</label>
              <input
                type="text"
                id="ollama-url"
                value={ollamaUrl}
                onChange={(e) => setOllamaUrl(e.target.value)}
                placeholder="http://localhost:11434"
                disabled={loading || success}
              />
            </div>
            <div className="form-group">
              <label htmlFor="ollama-model">Model Name</label>
              <input
                type="text"
                id="ollama-model"
                value={ollamaModel}
                onChange={(e) => setOllamaModel(e.target.value)}
                placeholder="llama3.2"
                disabled={loading || success}
              />
            </div>
            <p className="info-text">
              Make sure Ollama is installed and running on your device
            </p>
          </div>
        )}

        {provider === 'cloud' && (
          <div className="provider-config">
            <p className="info-text">
              Using free HuggingFace Inference API. No additional configuration
              needed.
            </p>
          </div>
        )}

        {provider === 'custom' && (
          <div className="provider-config">
            <div className="form-group">
              <label htmlFor="api-key">API Key *</label>
              <input
                type="password"
                id="api-key"
                value={customApiKey}
                onChange={(e) => setCustomApiKey(e.target.value)}
                required
                placeholder="Enter your API key"
                disabled={loading || success}
              />
            </div>
            <div className="form-group">
              <label htmlFor="base-url">Base URL</label>
              <input
                type="text"
                id="base-url"
                value={customBaseUrl}
                onChange={(e) => setCustomBaseUrl(e.target.value)}
                placeholder="https://api.openai.com/v1"
                disabled={loading || success}
              />
            </div>
            <div className="form-group">
              <label htmlFor="model">Model Name</label>
              <input
                type="text"
                id="model"
                value={customModel}
                onChange={(e) => setCustomModel(e.target.value)}
                placeholder="gpt-3.5-turbo"
                disabled={loading || success}
              />
            </div>
          </div>
        )}

        {error && <div className="error-message">{error}</div>}
        {success && (
          <div className="success-message">
            LLM configured successfully!
            {testResult && (
              <div className="test-result">{testResult}</div>
            )}
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
            disabled={
              loading ||
              success ||
              (provider === 'custom' && !customApiKey)
            }
          >
            {loading ? 'Configuring...' : success ? 'Success!' : 'Continue'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default LLMConfig
