import React, { useState, useEffect, useMemo } from 'react'
import StatusCard from './components/StatusCard'
import ActionButton from './components/ActionButton'
import QRDisplay from './components/QRDisplay'
import SettingsPanel from './components/SettingsPanel'
import BootScreen from './components/BootScreen'
import SetupRequiredScreen from './components/SetupRequiredScreen'
import SetupWizard from './components/SetupWizard'
import ConnectWiFiScreen from './components/ConnectWiFiScreen'
import JoinFlow from './components/JoinFlow'
import { Connectivity, Sparkles, Home, Smartphone, Wrench, RotateCw } from './components/icons'
import { getStatus, getSetupStatus, getDevStatus, factoryReset, getPairingCode, getApiBaseUrl } from './services/api'
import './styles/App.css'

function App() {
  const isJoinPage = useMemo(() => {
    const pathname = window.location.pathname || ''
    const token = new URLSearchParams(window.location.search).get('token')
    return pathname === '/join' && !!token
  }, [])

  const [status, setStatus] = useState(null)
  const [statusLoading, setStatusLoading] = useState(true)
  const [qrData, setQrData] = useState(null)
  const [connectLoading, setConnectLoading] = useState(false)
  const [error, setError] = useState(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [view, setView] = useState('boot')
  const [setupComplete, setSetupComplete] = useState(null)
  const [bootReady, setBootReady] = useState(false)
  const [setupUrl, setSetupUrl] = useState('')
  const [devProgress, setDevProgress] = useState({ progress: 0, stage: 'starting' })
  const [neuroionLaunched, setOpenclawLaunched] = useState(false)

  const isDev = import.meta.env.DEV

  useEffect(() => {
    if (isDev) return
    const timer = setTimeout(() => setBootReady(true), 1800)
    return () => clearTimeout(timer)
  }, [isDev])

  useEffect(() => {
    if (!isDev) return
    let cancelled = false
    const fallback = setTimeout(() => {
      if (!cancelled) setBootReady(true)
    }, 15000)
    const poll = async () => {
      try {
        const data = await getDevStatus()
        if (cancelled) return
        const progress = Number(data?.progress ?? 0)
        const stage = data?.stage ?? 'starting'
        setDevProgress({ progress, stage })
        if (progress >= 100) {
          setBootReady(true)
          clearTimeout(fallback)
        }
      } catch (_) {
        // Ignore errors while dev services boot
      }
    }
    poll()
    const interval = setInterval(poll, 3000)
    return () => {
      cancelled = true
      clearTimeout(fallback)
      clearInterval(interval)
    }
  }, [isDev])

  // After boot: check WiFi and setup; decide view (wifi → setup → dashboard)
  useEffect(() => {
    if (!bootReady) return
    let cancelled = false
    const initialCheck = async () => {
      try {
        const [statusRes, setupRes] = await Promise.all([
          getStatus().catch(() => null),
          getSetupStatus().catch(() => null),
        ])
        if (cancelled) return
        const setupCompleteVal = !!setupRes?.is_complete
        setSetupComplete(setupCompleteVal)
        // Skip WiFi step when hardware already has network (WiFi configured or has IP e.g. ethernet)
        const hasNetwork = !!(
          statusRes?.network?.wifi_configured ||
          (statusRes?.network?.ip && statusRes.network.ip !== '')
        )
        if (!hasNetwork) {
          setView('wifi')
        } else if (!setupCompleteVal) {
          setView('setup')
        } else {
          setView('dashboard')
        }
      } catch (_) {
        if (!cancelled) setView('setup')
      }
    }
    initialCheck()
    return () => { cancelled = true }
  }, [bootReady])

  const handleWifiConnected = () => {
    getSetupStatus()
      .then((data) => {
        const complete = !!data?.is_complete
        setSetupComplete(complete)
        setView(complete ? 'dashboard' : 'setup')
      })
      .catch(() => setView('setup'))
  }

  useEffect(() => {
    if (view !== 'setup') return
    const interval = setInterval(async () => {
      try {
        const data = await getSetupStatus()
        if (data?.is_complete) {
          setSetupComplete(true)
        }
      } catch (err) {
        // Ignore transient errors while polling
      }
    }, 3000)
    return () => clearInterval(interval)
  }, [view])

  useEffect(() => {
    if (view !== 'setup') return
    let cancelled = false
    const resolveSetupUrl = async () => {
      const explicitUrl = import.meta.env.VITE_SETUP_UI_URL
      if (explicitUrl) {
        if (!cancelled) {
          setSetupUrl(explicitUrl)
        }
        return
      }

      let data = null
      try {
        data = await getStatus()
        if (data?.setup_ui_url && !cancelled) {
          setSetupUrl(data.setup_ui_url)
          return
        }
      } catch (err) {
        // Fall through to fallback
      }

      const setupPort = import.meta.env.VITE_SETUP_UI_PORT || '3000'
      const protocol = window.location.protocol || 'http:'
      const currentHost = window.location.hostname
      let resolvedHost = currentHost

      if (!currentHost || currentHost === 'localhost' || currentHost === '127.0.0.1') {
        resolvedHost = data?.network?.hostname || data?.network?.ip || null
        if (!resolvedHost) {
          resolvedHost = import.meta.env.VITE_SETUP_UI_HOST || 'neuroion.core'
        }
      }

      if (!cancelled) {
        setSetupUrl(`${protocol}//${resolvedHost}:${setupPort}`)
      }
    }
    resolveSetupUrl()
    return () => {
      cancelled = true
    }
  }, [view])

  useEffect(() => {
    if (view !== 'dashboard') return
    setStatusLoading(true)
    fetchStatus()
    const interval = setInterval(fetchStatus, 5000)
    return () => clearInterval(interval)
  }, [view])

  useEffect(() => {
    if (view !== 'dashboard' || !status || neuroionLaunched) return
    const autoLaunch = import.meta.env.VITE_NEUROION_AUTOLAUNCH === '1' || import.meta.env.VITE_NEUROION_AUTOLAUNCH === 'true'
    if (!autoLaunch) return
    const url = status?.neuroion_ui_url || 'http://127.0.0.1:3141/neuroion/'
    setOpenclawLaunched(true)
    window.location.href = url
  }, [view, status, neuroionLaunched])

  const fetchStatus = async () => {
    try {
      const data = await getStatus()
      setStatus(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setStatusLoading(false)
    }
  }

  const handleOpenDashboard = () => {
    // Core dashboard (dashboard-nextjs) – use status.dashboard_url from API or fallback to dashboard port (3002 in dev)
    const dashboardPort = 3002
    const url = status?.dashboard_url
      ? `${status.dashboard_url.replace(/\/$/, '')}`
      : `http://${status?.network?.hostname || 'neuroion.local'}:${dashboardPort}`
    setQrData({ url, title: 'Open Dashboard' })
  }

  const handleConnect = async () => {
    setError(null)
    setConnectLoading(true)
    try {
      const householdId = 1
      const deviceId = `connect-${Date.now()}`
      const pairingCode = await getPairingCode(householdId, deviceId, 'ios', 'iPhone')
      const apiPort = import.meta.env.VITE_API_PORT || '8000'
      const rawIp = status?.network?.ip
      const ip = (typeof rawIp === 'string' && rawIp.trim() !== '' && rawIp !== '—') ? rawIp.trim() : null
      const homebaseUrl = ip ? `http://${ip}:${apiPort}` : getApiBaseUrl()
      const vpnBase = 'https://10.66.66.1'
      const params = new URLSearchParams({ base: homebaseUrl, code: pairingCode, vpn: '1', vpn_base: vpnBase })
      const qrValue = `neuroion://pair?${params.toString()}`
      setQrData({ url: qrValue, title: 'Koppelen met app (VPN)' })
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Kon geen koppelcode ophalen')
    } finally {
      setConnectLoading(false)
    }
  }

  const handleSettingsOpen = () => setSettingsOpen(true)
  const handleSettingsClose = () => setSettingsOpen(false)
  const handleFactoryReset = () => {
    factoryReset()
      .then(() => {
        const keys = Object.keys(localStorage).filter((k) =>
          /^neuroion_setup_/i.test(k)
        )
        keys.forEach((k) => localStorage.removeItem(k))
        setSetupComplete(false)
        setView('setup')
        window.location.reload()
      })
      .catch((err) => {
        setError(`Factory reset failed: ${err.message}`)
        setSettingsOpen(false)
      })
  }

  const handleOpenNeuroion = () => {
    const url = status?.neuroion_ui_url || 'http://127.0.0.1:3141/neuroion/'
    window.location.href = url
  }

  const handleRestart = () => {
    if (window.confirm('Are you sure you want to restart Neuroion?')) {
      // This would call a restart API endpoint
      setError('Restart functionality requires API endpoint')
    }
  }

  if (isJoinPage) {
    return (
      <div className="app">
        <JoinFlow />
      </div>
    )
  }

  if (view === 'boot') {
    const progress = isDev ? devProgress.progress : 0
    const stage = isDev ? devProgress.stage : 'starting'
    return <BootScreen progress={progress} stage={stage} />
  }

  if (view === 'wifi') {
    return (
      <div className="app">
        <ConnectWiFiScreen onConnected={handleWifiConnected} />
      </div>
    )
  }

  if (view === 'setup') {
    return (
      <SetupWizard
        onComplete={() => {
          setSetupComplete(true)
        }}
      />
    )
  }

  if (statusLoading) {
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
      {/* <div className="header">
        <h1>Neuroion</h1>
      </div> */}

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
            icon={<Connectivity size={36} />}
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
            icon={<Sparkles size={36} />}
          />
        )}

        {status?.user?.name && (
          <StatusCard
            title="User"
            status="active"
            details={{
              Name: status.user.name,
            }}
            icon={<Home size={36} />}
          />
        )}
      </div>

      {/* {status?.storage && (
          <StatusCard
            title="Storage"
            status="ok"
            details={{
              'Free (GB)': status.storage.free_gb,
              'Total (GB)': status.storage.total_gb,
            }}
            icon={<Sparkles size={36} />}
          />
        )}
        {status?.agent && (
          <StatusCard
            title="Neuroion Agent"
            status={status.agent.status}
            details={{ Name: status.agent.name }}
            icon={<Sparkles size={36} />}
          />
        )} */}
      {status?.degraded_message && (
        <div className="degraded-banner">{status.degraded_message}</div>
      )}

      <div className="actions-grid">
        <ActionButton
          label={connectLoading ? 'Bezig…' : 'Koppelen'}
          icon={<Smartphone size={36} />}
          onClick={handleConnect}
          variant="primary"
          disabled={connectLoading}
        />
        <ActionButton
          label="Open Dashboard"
          icon={<Smartphone size={36} />}
          onClick={handleOpenDashboard}
          variant="secondary"
        />
        <ActionButton
          label="Instellingen"
          icon={<Wrench size={36} />}
          onClick={handleSettingsOpen}
          variant="secondary"
        />
        <ActionButton
          label="Restart"
          icon={<RotateCw size={36} />}
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

      {settingsOpen && (
        <SettingsPanel
          status={status}
          onClose={handleSettingsClose}
          onFactoryReset={handleFactoryReset}
        />
      )}
    </div>
  )
}

export default App
