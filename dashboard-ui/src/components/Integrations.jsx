import React, { useState, useEffect } from 'react'
import { getIntegrations, connectIntegration, disconnectIntegration, getOAuthUrl } from '../services/api'
import '../styles/Integrations.css'

function Integrations({ userId }) {
  const [integrations, setIntegrations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchIntegrations()
  }, [userId])

  const fetchIntegrations = async () => {
    try {
      const data = await getIntegrations(userId)
      setIntegrations(data.integrations || [])
      setError(null)
    } catch (err) {
      console.error('Failed to fetch integrations:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleConnect = async (integrationType) => {
    try {
      // Generate state for OAuth
      const state = Math.random().toString(36).substring(7)
      const redirectUri = `${window.location.origin}/user/${userId}/oauth/callback`
      
      // Get OAuth URL
      const { url } = await getOAuthUrl(integrationType, redirectUri, state)
      
      // Store state in sessionStorage
      sessionStorage.setItem('oauth_state', state)
      sessionStorage.setItem('oauth_integration', integrationType)
      
      // Redirect to OAuth provider
      window.location.href = url
    } catch (err) {
      console.error('Failed to initiate OAuth:', err)
      setError(err.message)
    }
  }

  const handleDisconnect = async (integrationType) => {
    if (!confirm(`Are you sure you want to disconnect ${integrationType}?`)) {
      return
    }

    try {
      await disconnectIntegration(userId, integrationType)
      await fetchIntegrations()
    } catch (err) {
      console.error('Failed to disconnect integration:', err)
      setError(err.message)
    }
  }

  const availableIntegrations = [
    {
      type: 'gmail',
      name: 'Gmail',
      description: 'Connect your Gmail account to allow Neuroion to read, send, and manage emails',
      icon: '📧',
    },
  ]

  if (loading) {
    return (
      <div className="integrations">
        <div className="integrations-loading">
          <p>Loading integrations...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="integrations">
      <div className="integrations-header">
        <h2 className="integrations-title">Integrations</h2>
        <p className="integrations-description">
          Connect external services to extend Neuroion's capabilities
        </p>
      </div>

      {error && (
        <div className="integrations-error">
          <p>Error: {error}</p>
        </div>
      )}

      <div className="integrations-list">
        {availableIntegrations.map((integration) => {
          const connected = integrations.find(i => i.integration_type === integration.type)
          
          return (
            <div key={integration.type} className="integration-card">
              <div className="integration-icon">{integration.icon}</div>
              <div className="integration-content">
                <h3 className="integration-name">{integration.name}</h3>
                <p className="integration-description">{integration.description}</p>
                {connected && (
                  <div className="integration-status">
                    <span className="status-badge status-connected">Connected</span>
                    {connected.permissions && (
                      <span className="permissions-info">
                        Permissions: {Object.keys(connected.permissions).join(', ')}
                      </span>
                    )}
                  </div>
                )}
              </div>
              <div className="integration-actions">
                {connected ? (
                  <button
                    className="btn btn-secondary"
                    onClick={() => handleDisconnect(integration.type)}
                  >
                    Disconnect
                  </button>
                ) : (
                  <button
                    className="btn btn-primary"
                    onClick={() => handleConnect(integration.type)}
                  >
                    Connect
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default Integrations
