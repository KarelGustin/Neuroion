import React, { useState, useEffect, useMemo } from 'react'
import PairingQR from './components/PairingQR'
import Status from './components/Status'
import Logo from './components/Logo'
import SetupWizard from './components/SetupWizard'
import SetupCompletionScreen from './components/SetupCompletionScreen'
import Dashboard from './components/Dashboard'
import ConfigQR from './components/ConfigQR'
import { getPairingCode, checkHealth, getSetupStatus } from './services/api'
import './styles/App.css'

function App() {
  const isKiosk = useMemo(() => {
    const params = new URLSearchParams(window.location.search)
    return params.get('kiosk') === '1' || params.get('mode') === 'kiosk'
  }, [])

  const [pairingCode, setPairingCode] = useState(null)
  const [status, setStatus] = useState('checking')
  const [error, setError] = useState(null)
  const [setupComplete, setSetupComplete] = useState(false)
  const [checkingSetup, setCheckingSetup] = useState(true)
  const [showCompletion, setShowCompletion] = useState(false)

  useEffect(() => {
    checkHealth()
      .then(() => {
        setStatus('ready')
        return checkSetupStatus()
      })
      .catch((err) => {
        setStatus('error')
        setError(err.message)
        setCheckingSetup(false)
      })

    const interval = setInterval(() => {
      if (status === 'ready' && setupComplete) {
        startPairing()
      }
    }, 5 * 60 * 1000)

    return () => clearInterval(interval)
  }, [status, setupComplete])

  // In kiosk mode, poll setup status so we switch from ConfigQR to Dashboard when config is done on another device
  useEffect(() => {
    if (!isKiosk || status !== 'ready') return
    const poll = setInterval(() => {
      getSetupStatus()
        .then((s) => setSetupComplete(s.is_complete))
        .catch(() => {})
    }, 3000)
    return () => clearInterval(poll)
  }, [isKiosk, status])

  const checkSetupStatus = async () => {
    try {
      const setupStatus = await getSetupStatus()
      setSetupComplete(setupStatus.is_complete)
      if (!setupStatus.is_complete && setupStatus.reset_at) {
        try {
          const storedReset = localStorage.getItem('neuroion_setup_reset_at')
          if (storedReset !== setupStatus.reset_at) {
            Object.keys(localStorage).forEach((key) => {
              if (key.startsWith('neuroion_setup_')) {
                localStorage.removeItem(key)
              }
            })
            localStorage.setItem('neuroion_setup_reset_at', setupStatus.reset_at)
          }
        } catch (_) {}
      }
      if (setupStatus.is_complete) {
        await startPairing()
      }
    } catch (err) {
      console.error('Failed to check setup status:', err)
      // Assume not complete if check fails
      setSetupComplete(false)
    } finally {
      setCheckingSetup(false)
    }
  }

  const startPairing = async () => {
    try {
      // Get first household ID (should be 1 after setup)
      const code = await getPairingCode(1, 'setup-ui', 'web', 'Setup UI')
      setPairingCode(code)
      setError(null)
    } catch (err) {
      setError(err.message)
      setStatus('error')
    }
  }

  const handleSetupComplete = async () => {
    setSetupComplete(true)
    setShowCompletion(true)
    // Immediately fetch pairing code to show Telegram QR
    await startPairing()
  }

  if (checkingSetup && !isKiosk) {
    return (
      <div className="app">
        <div className="container">
          <div className="header">
            <Logo />
            <p className="tagline">Home Intelligence Platform</p>
          </div>
          <Status status="checking" />
        </div>
      </div>
    )
  }

  if (isKiosk && !setupComplete) {
    return (
      <div className="app config-qr-app">
        <ConfigQR />
      </div>
    )
  }

  if (isKiosk && setupComplete) {
    return (
      <div className="app app-kiosk">
        <div className="container">
          <Dashboard isKiosk />
        </div>
      </div>
    )
  }

  if (showCompletion) {
    return (
      <div className="app">
        <div className="container">
          <SetupCompletionScreen onDone={() => setShowCompletion(false)} />
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      <div className="container app-grid">
        {!setupComplete && <Status status={status} error={error} />}
        {!setupComplete ? (
          <SetupWizard onComplete={handleSetupComplete} />
        ) : (
          <Dashboard />
        )}
      </div>
    </div>
  )
}

export default App
