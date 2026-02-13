import React, { useState, useEffect } from 'react'
import { scanWifiNetworks, configureWifi, applyWifi, getStatus } from '../services/api'
import TouchKeyboard from './TouchKeyboard'
import '../styles/SetupWizard.css'
import '../styles/ConnectWiFiScreen.css'

function ConnectWiFiScreen({ onConnected }) {
  const [networks, setNetworks] = useState([])
  const [selectedSsid, setSelectedSsid] = useState('')
  const [wifiPassword, setWifiPassword] = useState('')
  const [wifiConnecting, setWifiConnecting] = useState(false)
  const [error, setError] = useState(null)
  const [focusedInput, setFocusedInput] = useState(null)

  useEffect(() => {
    let cancelled = false
    scanWifiNetworks()
      .then((list) => {
        if (!cancelled) setNetworks(Array.isArray(list) ? list : [])
      })
      .catch(() => {
        if (!cancelled) setNetworks([])
      })
    return () => { cancelled = true }
  }, [])

  const handleConnect = async () => {
    if (!selectedSsid) return
    setError(null)
    setWifiConnecting(true)
    try {
      await configureWifi(selectedSsid, (wifiPassword || '').trim())
      const result = await applyWifi()
      if (!result?.success) {
        setError(result?.message || 'Verbinding mislukt.')
        setWifiConnecting(false)
        return
      }
      // Poll until WiFi is reported connected (apply can take a few seconds)
      const deadline = Date.now() + 30000
      while (Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 2000))
        try {
          const status = await getStatus()
          if (status?.network?.wifi_configured) {
            onConnected?.()
            return
          }
        } catch (_) {}
      }
      onConnected?.()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'WiFi verbinden mislukt.')
    } finally {
      setWifiConnecting(false)
    }
  }

  return (
    <div className="connect-wifi-screen">
      <div className="connect-wifi-inner">
        <h2 className="setup-wizard-title">Verbind met WiFi</h2>
        <p className="setup-wizard-hint">Kies je netwerk zodat Neuroion verbinding heeft.</p>
        {error && <p className="setup-wizard-error">{error}</p>}
        <ul className="setup-wizard-network-list">
          {networks.map((n) => (
            <li key={n.ssid ?? n}>
              <button
                type="button"
                className={`setup-wizard-network-btn ${selectedSsid === (n.ssid ?? n) ? 'setup-wizard-network-btn--selected' : ''}`}
                onClick={() => setSelectedSsid(n.ssid ?? n)}
              >
                {n.ssid ?? n} {n.signal_strength != null ? `(${n.signal_strength}%)` : ''}
              </button>
            </li>
          ))}
        </ul>
        {networks.length === 0 && !error && (
          <p className="connect-wifi-scanning">Netwerken scannen…</p>
        )}
        {selectedSsid && (
          <label className="setup-wizard-label">
            Wachtwoord (optioneel voor open netwerk)
            <input
              type="password"
              className="setup-wizard-input"
              value={wifiPassword}
              onChange={(e) => setWifiPassword(e.target.value)}
              onFocus={() => setFocusedInput('wifiPassword')}
              readOnly={focusedInput === 'wifiPassword'}
              placeholder="Wachtwoord"
              autoComplete="current-password"
            />
          </label>
        )}
        <div className="setup-wizard-actions">
          {selectedSsid ? (
            <button
              type="button"
              className="setup-wizard-btn setup-wizard-btn--primary"
              onClick={handleConnect}
              disabled={wifiConnecting}
            >
              {wifiConnecting ? 'Verbinden…' : 'Verbinden'}
            </button>
          ) : (
            <button type="button" className="setup-wizard-btn setup-wizard-btn--primary" disabled>
              Kies een netwerk
            </button>
          )}
        </div>
      </div>
      {focusedInput && (
        <TouchKeyboard
          visible={!!focusedInput}
          value={focusedInput === 'wifiPassword' ? wifiPassword : ''}
          onChange={focusedInput === 'wifiPassword' ? setWifiPassword : () => {}}
          onClose={() => setFocusedInput(null)}
        />
      )}
    </div>
  )
}

export default ConnectWiFiScreen
