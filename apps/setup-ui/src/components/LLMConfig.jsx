import React, { useState } from 'react'
import { configureLLM } from '../services/api'
import '../styles/LLMConfig.css'

function LLMConfig({ onComplete, onBack, initialData }) {
  // Load from localStorage if initialData is not provided
  const loadFromStorage = () => {
    try {
      const saved = localStorage.getItem('neuroion_setup_llm')
      if (saved) {
        return JSON.parse(saved)
      }
    } catch (err) {
      console.error('Failed to load LLM config from storage:', err)
    }
    return null
  }

  const savedData = initialData || loadFromStorage()
  const [provider, setProvider] = useState(savedData?.provider || 'local')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)
  const [testResult, setTestResult] = useState(null)

  // Custom API fields
  const [openaiApiKey, setOpenaiApiKey] = useState(savedData?.openaiApiKey || '')
  const [openaiModel, setOpenaiModel] = useState(
    savedData?.openaiModel || 'gpt-4o-mini',
  )
  const [customApiKey, setCustomApiKey] = useState(savedData?.customApiKey || '')
  const [customBaseUrl, setCustomBaseUrl] = useState(
    savedData?.customBaseUrl || 'https://api.openai.com/v1',
  )
  const [customModel, setCustomModel] = useState(
    savedData?.customModel || 'gpt-3.5-turbo',
  )

  // Local Ollama fields - URL automatically detected based on current hostname
  // If accessing via IP, use that IP for Ollama; otherwise use localhost
  const getOllamaUrl = () => {
    const hostname = window.location.hostname
    // If accessing via localhost, use localhost for Ollama
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://localhost:11434'
    }
    // Otherwise, use the same hostname (IP address) for Ollama
    return `http://${hostname}:11434`
  }
  const ollamaUrl = getOllamaUrl()
  const [ollamaModel, setOllamaModel] = useState(
    savedData?.ollamaModel || 'llama3.2:3b',
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
      } else if (provider === 'openai') {
        if (!openaiApiKey) {
          setError('API key is required for OpenAI')
          setLoading(false)
          return
        }
        config = {
          api_key: openaiApiKey,
          base_url: 'https://api.openai.com/v1',
          model: openaiModel,
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
        const llmData = {
          provider,
          config,
          openaiApiKey,
          openaiModel,
          customApiKey,
          customBaseUrl,
          customModel,
          ollamaUrl: ollamaUrl, // Pre-installed URL
          ollamaModel,
        }
        // Save to localStorage
        try {
          localStorage.setItem('neuroion_setup_llm', JSON.stringify(llmData))
        } catch (err) {
          console.error('Failed to save LLM config:', err)
        }
        setTimeout(() => {
          onComplete(llmData)
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
              value="openai"
              checked={provider === 'openai'}
              onChange={(e) => setProvider(e.target.value)}
              disabled={loading || success}
            />
            <div className="radio-content">
              <strong>OpenAI</strong>
              <span>Use your own OpenAI API key</span>
            </div>
          </label>

          <label className="radio-option disabled">
            <input
              type="radio"
              name="provider"
              value="cloud"
              checked={provider === 'cloud'}
              onChange={(e) => setProvider(e.target.value)}
              disabled={true}
            />
            <div className="radio-content">
              <strong>Neuroion Agent (Not available yet)</strong>
              <span>€19 per member</span>
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
              <strong>OpenAI-compatible</strong>
              <span>Use any OpenAI-compatible API endpoint</span>
            </div>
          </label>
        </div>

        {provider === 'local' && (
          <div className="provider-config">
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
              Ollama is pre-installed on your device
            </p>
          </div>
        )}

        {provider === 'openai' && (
          <div className="provider-config">
            <div className="form-group">
              <label htmlFor="openai-key">API Key *</label>
              <input
                type="password"
                id="openai-key"
                value={openaiApiKey}
                onChange={(e) => setOpenaiApiKey(e.target.value)}
                required
                placeholder="Enter your API key"
                disabled={loading || success}
              />
            </div>
            <div className="form-group">
              <label htmlFor="openai-model">Model Name</label>
              <input
                type="text"
                id="openai-model"
                value={openaiModel}
                onChange={(e) => setOpenaiModel(e.target.value)}
                placeholder="gpt-4o-mini"
                disabled={loading || success}
              />
            </div>
          </div>
        )}

        {provider === 'cloud' && (
          <div className="provider-config">
            <p className="info-text">
              Neuroion Agent is not yet available. This feature will be available soon.
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
              (provider === 'openai' && !openaiApiKey) ||
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
