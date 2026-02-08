import React, { useState, useEffect } from 'react'
import { Routes, Route, useSearchParams, useParams, useNavigate } from 'react-router-dom'
import Integrations from './components/Integrations'
import Preferences from './components/Preferences'
import Context from './components/Context'
import OAuthCallback from './components/OAuthCallback'
import { verifyLoginCode } from './services/api'
import './styles/App.css'

function DashboardPage() {
  const [searchParams] = useSearchParams()
  const { userId } = useParams()
  const navigate = useNavigate()
  const [authenticated, setAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [loginCode, setLoginCode] = useState('')
  const [verifying, setVerifying] = useState(false)
  const [activeTab, setActiveTab] = useState('integrations') // 'integrations' | 'preferences' | 'context'

  useEffect(() => {
    // Check for token in URL or localStorage
    const token = searchParams.get('token') || localStorage.getItem('dashboard_token')
    
    if (token) {
      localStorage.setItem('dashboard_token', token)
      setAuthenticated(true)
    } else {
      setError('No authentication token provided')
    }
    
    setLoading(false)
  }, [searchParams])

  if (loading) {
    return (
      <div className="app">
        <div className="app-loading">
          <p>Loading...</p>
        </div>
      </div>
    )
  }

  const handleLoginCodeSubmit = async (e) => {
    e.preventDefault()
    if (!loginCode || loginCode.length !== 4) {
      setError('Please enter a valid 4-digit login code')
      return
    }

    setVerifying(true)
    setError(null)

    try {
      const result = await verifyLoginCode(loginCode)
      localStorage.setItem('dashboard_token', result.token)
      setAuthenticated(true)
      // Redirect to update URL with token
      navigate(`/user/${result.user_id}?token=${result.token}`, { replace: true })
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid or expired login code')
      setLoginCode('')
    } finally {
      setVerifying(false)
    }
  }

  if (error || !authenticated) {
    return (
      <div className="app">
        <div className="app-error">
          <h1>Authentication Required</h1>
          <p>{error || 'Please provide a valid dashboard token or login code'}</p>
          <p className="error-hint">
            Ask Neuroion for your personal dashboard link, or enter a login code below.
          </p>
          <form onSubmit={handleLoginCodeSubmit} className="login-code-form">
            <input
              type="text"
              className="login-code-input"
              placeholder="Enter 4-digit code"
              value={loginCode}
              onChange={(e) => {
                const value = e.target.value.replace(/\D/g, '').slice(0, 4)
                setLoginCode(value)
                setError(null)
              }}
              maxLength={4}
              disabled={verifying}
              autoFocus
            />
            <button
              type="submit"
              className="login-code-submit"
              disabled={verifying || loginCode.length !== 4}
            >
              {verifying ? 'Verifying...' : 'Login'}
            </button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      <div className="app-container">
        <header className="app-header">
          <h1 className="app-title">Neuroion Dashboard</h1>
          <p className="app-subtitle">Manage your integrations and settings</p>
        </header>

        <div className="app-tabs">
          <button
            className={`app-tab ${activeTab === 'integrations' ? 'active' : ''}`}
            onClick={() => setActiveTab('integrations')}
          >
            Integrations
          </button>
          <button
            className={`app-tab ${activeTab === 'preferences' ? 'active' : ''}`}
            onClick={() => setActiveTab('preferences')}
          >
            Preferences
          </button>
          <button
            className={`app-tab ${activeTab === 'context' ? 'active' : ''}`}
            onClick={() => setActiveTab('context')}
          >
            Context
          </button>
        </div>

        <main className="app-main">
          {activeTab === 'integrations' && <Integrations userId={parseInt(userId)} />}
          {activeTab === 'preferences' && <Preferences userId={parseInt(userId)} />}
          {activeTab === 'context' && <Context userId={parseInt(userId)} />}
        </main>
      </div>
    </div>
  )
}

function App() {
  return (
    <Routes>
      <Route path="/user/:userId" element={<DashboardPage />} />
      <Route path="/user/:userId/oauth/callback" element={<OAuthCallback />} />
    </Routes>
  )
}

export default App
