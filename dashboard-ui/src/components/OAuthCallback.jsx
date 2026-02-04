import React, { useEffect, useState } from 'react'
import { useSearchParams, useParams, useNavigate } from 'react-router-dom'
import { connectIntegration } from '../services/api'
import '../styles/OAuthCallback.css'

function OAuthCallback() {
  const [searchParams] = useSearchParams()
  const { userId } = useParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState('processing')
  const [error, setError] = useState(null)

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code')
      const state = searchParams.get('state')
      const storedState = sessionStorage.getItem('oauth_state')
      const integrationType = sessionStorage.getItem('oauth_integration')

      if (!code || !state) {
        setError('Missing authorization code or state')
        setStatus('error')
        return
      }

      if (state !== storedState) {
        setError('Invalid state parameter')
        setStatus('error')
        return
      }

      if (!integrationType) {
        setError('Integration type not found')
        setStatus('error')
        return
      }

      try {
        const redirectUri = `${window.location.origin}/user/${userId}/oauth/callback`
        await connectIntegration(userId, integrationType, code, redirectUri)
        
        // Clean up session storage
        sessionStorage.removeItem('oauth_state')
        sessionStorage.removeItem('oauth_integration')
        
        setStatus('success')
        
        // Redirect to dashboard after 2 seconds
        setTimeout(() => {
          navigate(`/user/${userId}?token=${localStorage.getItem('dashboard_token')}`)
        }, 2000)
      } catch (err) {
        console.error('Failed to connect integration:', err)
        setError(err.message || 'Failed to connect integration')
        setStatus('error')
      }
    }

    handleCallback()
  }, [searchParams, userId, navigate])

  return (
    <div className="oauth-callback">
      <div className="oauth-callback-container">
        {status === 'processing' && (
          <>
            <div className="oauth-spinner"></div>
            <h2>Connecting integration...</h2>
            <p>Please wait while we complete the connection.</p>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="oauth-success">✓</div>
            <h2>Integration Connected!</h2>
            <p>Redirecting to your dashboard...</p>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="oauth-error">✕</div>
            <h2>Connection Failed</h2>
            <p>{error || 'An error occurred while connecting the integration.'}</p>
            <button
              className="btn btn-primary"
              onClick={() => navigate(`/user/${userId}?token=${localStorage.getItem('dashboard_token')}`)}
            >
              Return to Dashboard
            </button>
          </>
        )}
      </div>
    </div>
  )
}

export default OAuthCallback
