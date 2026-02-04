import React, { useState, useEffect } from 'react'
import { Routes, Route, useSearchParams, useParams, useNavigate } from 'react-router-dom'
import Integrations from './components/Integrations'
import OAuthCallback from './components/OAuthCallback'
import './styles/App.css'

function DashboardPage() {
  const [searchParams] = useSearchParams()
  const { userId } = useParams()
  const [authenticated, setAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

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

  if (error || !authenticated) {
    return (
      <div className="app">
        <div className="app-error">
          <h1>Authentication Required</h1>
          <p>{error || 'Please provide a valid dashboard token'}</p>
          <p className="error-hint">
            Ask Neuroion for your personal dashboard link to access this page.
          </p>
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

        <main className="app-main">
          <Integrations userId={parseInt(userId)} />
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
