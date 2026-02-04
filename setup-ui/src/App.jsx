import React, { useState, useEffect } from 'react'
import PairingQR from './components/PairingQR'
import Status from './components/Status'
import Logo from './components/Logo'
import SetupWizard from './components/SetupWizard'
import Dashboard from './components/Dashboard'
import { getPairingCode, checkHealth, getSetupStatus } from './services/api'
import './styles/App.css'

function App() {
  const [pairingCode, setPairingCode] = useState(null)
  const [status, setStatus] = useState('checking')
  const [error, setError] = useState(null)
  const [setupComplete, setSetupComplete] = useState(false)
  const [checkingSetup, setCheckingSetup] = useState(true)

  useEffect(() => {
    // Check health and setup status on mount
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

    // Refresh pairing code every 5 minutes if setup is complete
    const interval = setInterval(() => {
      if (status === 'ready' && setupComplete) {
        startPairing()
      }
    }, 5 * 60 * 1000)

    return () => clearInterval(interval)
  }, [status, setupComplete])

  const checkSetupStatus = async () => {
    try {
      const setupStatus = await getSetupStatus()
      setSetupComplete(setupStatus.is_complete)
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
    // Immediately fetch pairing code to show Telegram QR
    await startPairing()
  }

  if (checkingSetup) {
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

  return (
    <div className="app">
      <div className="container">
        {/* <div className="header">
          {/* <Logo /> */}
          {/* <p className="tagline">Home Intelligence Platform</p>
        </div> */} 

        <Status status={status} error={error} />

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
