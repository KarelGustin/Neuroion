import React, { useState, useEffect } from 'react'
import StatusCard from './components/StatusCard'
import ActionButton from './components/ActionButton'
import QRDisplay from './components/QRDisplay'
import { Connectivity, Sparkles, Home, Smartphone, UserPlus, Wrench, RotateCw } from './components/icons'
import { getStatus, createJoinToken } from './services/api'
import './styles/App.css'

function App() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [qrData, setQrData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchStatus = async () => {
    try {
      const data = await getStatus()
      setStatus(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleOpenDashboard = () => {
    const url = `http://${status?.network?.hostname || 'neuroion.local'}/dashboard`
    setQrData({ url, title: 'Open Dashboard' })
  }

  const handleAddMember = async () => {
    try {
      const tokenData = await createJoinToken()
      const url = tokenData.join_url || `http://${status?.network?.hostname || 'neuroion.local'}/join?token=${tokenData.token}`
      setQrData({ url, title: 'Add Member - Scan to Join' })
    } catch (err) {
      setError(`Failed to create join token: ${err.message}`)
    }
  }

  const handleTroubleshoot = () => {
    const url = `http://${status?.network?.hostname || 'neuroion.local'}/dashboard`
    setQrData({ url, title: 'Troubleshoot - Open Dashboard' })
  }

  const handleRestart = () => {
    if (window.confirm('Are you sure you want to restart Neuroion?')) {
      // This would call a restart API endpoint
      setError('Restart functionality requires API endpoint')
    }
  }

  if (loading) {
    return (
      <div className="app">
        <div className="loading">
          <div className="loading-spinner" aria-hidden="true" />
          <span className="loading-label">Loading…</span>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      <div className="header">
        <h1>Neuroion</h1>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="status-grid">
        {status?.network && (
          <StatusCard
            title="Connectivity"
            status={status.network.wifi_configured ? 'connected' : 'disconnected'}
            details={{
              SSID: status.network.ssid,
              IP: status.network.ip,
              Hostname: status.network.hostname,
            }}
            icon={<Connectivity size={24} />}
          />
        )}

        {status?.model && (
          <StatusCard
            title="LLM"
            status={status.model.status}
            details={{
              Preset: status.model.preset,
              Model: status.model.name,
              Health: status.model.health,
            }}
            icon={<Sparkles size={24} />}
          />
        )}

        {status?.household && (
          <StatusCard
            title="Household"
            status="active"
            details={{
              Name: status.household.name,
              Members: status.household.member_count,
            }}
            icon={<Home size={24} />}
          />
        )}
        {status?.storage && (
          <StatusCard
            title="Storage"
            status="ok"
            details={{
              'Free (GB)': status.storage.free_gb,
              'Total (GB)': status.storage.total_gb,
            }}
            icon={<Sparkles size={24} />}
          />
        )}
        {status?.agent && (
          <StatusCard
            title="Neuroion Agent"
            status={status.agent.status}
            details={{ Name: status.agent.name }}
            icon={<Sparkles size={24} />}
          />
        )}
      </div>
      {status?.degraded_message && (
        <div className="degraded-banner">{status.degraded_message}</div>
      )}

      <div className="actions-grid">
        <ActionButton
          label="Open Dashboard"
          icon={<Smartphone size={24} />}
          onClick={handleOpenDashboard}
          variant="primary"
        />
        <ActionButton
          label="Add Member"
          icon={<UserPlus size={24} />}
          onClick={handleAddMember}
          variant="primary"
        />
        <ActionButton
          label="Troubleshoot"
          icon={<Wrench size={24} />}
          onClick={handleTroubleshoot}
          variant="secondary"
        />
        <ActionButton
          label="Restart"
          icon={<RotateCw size={24} />}
          onClick={handleRestart}
          variant="danger"
          requiresLongPress={true}
        />
      </div>

      {qrData && (
        <QRDisplay
          url={qrData.url}
          title={qrData.title}
          onClose={() => setQrData(null)}
        />
      )}
    </div>
  )
}

export default App
