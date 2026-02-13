import React, { useState, useEffect } from 'react'
import {
  getStatus,
  setupHousehold,
  setupDevice,
  setupAgentName,
  scanWifiNetworks,
  configureWifi,
  applyWifi,
  markSetupComplete,
} from '../services/api'
import TouchKeyboard from './TouchKeyboard'
import '../styles/SetupWizard.css'

function SetupWizard({ onComplete }) {
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [deviceName, setDeviceName] = useState('Neuroion Core')
  const [householdName, setHouseholdName] = useState('')
  const [agentName, setAgentName] = useState('ion')
  const [wifiStatus, setWifiStatus] = useState(null)
  const [networks, setNetworks] = useState([])
  const [selectedSsid, setSelectedSsid] = useState('')
  const [wifiPassword, setWifiPassword] = useState('')
  const [wifiConnecting, setWifiConnecting] = useState(false)
  const [completing, setCompleting] = useState(false)
  const [showLogoAnimation, setShowLogoAnimation] = useState(false)
  const [focusedInput, setFocusedInput] = useState(null)

  useEffect(() => {
    if (step !== 3) return
    let cancelled = false
    getStatus()
      .then((data) => {
        if (!cancelled) setWifiStatus(data?.network)
      })
      .catch(() => {
        if (!cancelled) setWifiStatus({ wifi_configured: false })
      })
    return () => { cancelled = true }
  }, [step])

  useEffect(() => {
    if (step !== 3 || (wifiStatus && wifiStatus.wifi_configured)) return
    let cancelled = false
    scanWifiNetworks()
      .then((list) => {
        if (!cancelled) setNetworks(Array.isArray(list) ? list : [])
      })
      .catch(() => {
        if (!cancelled) setNetworks([])
      })
    return () => { cancelled = true }
  }, [step, wifiStatus])

  const handleStep1Next = async () => {
    const h = (householdName || '').trim()
    const d = (deviceName || 'Neuroion Core').trim()
    if (!h) {
      setError('Vul een householdnaam in.')
      return
    }
    setError(null)
    setLoading(true)
    try {
      await setupHousehold(h, h)
      await setupDevice(d || 'Neuroion Core', 'Europe/Amsterdam')
      setStep(2)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Opslaan mislukt.')
    } finally {
      setLoading(false)
    }
  }

  const handleStep2Next = async () => {
    const name = (agentName || 'ion').trim() || 'ion'
    setError(null)
    setLoading(true)
    try {
      await setupAgentName(name)
      setStep(3)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Opslaan mislukt.')
    } finally {
      setLoading(false)
    }
  }

  const handleStep3Connect = async () => {
    if (selectedSsid && !wifiPassword.trim()) {
      setError('Voer wachtwoord in (of laat leeg voor open netwerk).')
      return
    }
    setError(null)
    setWifiConnecting(true)
    try {
      await configureWifi(selectedSsid, wifiPassword.trim())
      const result = await applyWifi()
      if (result?.success) {
        setWifiStatus({ wifi_configured: true, ssid: selectedSsid })
      } else {
        setError(result?.message || 'Verbinding mislukt.')
      }
    } catch (err) {
      setError(err.response?.data?.message || err.response?.data?.detail || err.message || 'WiFi mislukt.')
    } finally {
      setWifiConnecting(false)
    }
  }

  const handleStep3Next = () => {
    setError(null)
    setStep(4)
  }

  const handleStep4Start = async () => {
    setError(null)
    setCompleting(true)
    try {
      await markSetupComplete()
      setShowLogoAnimation(true)
      setTimeout(() => {
        onComplete?.()
      }, 5000)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Afronden mislukt.')
      setCompleting(false)
    }
  }

  if (showLogoAnimation) {
    return (
      <div className="setup-wizard setup-wizard--logo">
        <div className="setup-wizard-logo" aria-label="Neuroion">
          <svg viewBox="0 0 100 120" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path
              d="M 50 20 L 30 60 L 70 60 Z"
              fill="none"
              stroke="currentColor"
              strokeWidth="4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <line x1="50" y1="75" x2="50" y2="105" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
          </svg>
        </div>
        <p className="setup-wizard-logo-text">Start je Neuroion Core One</p>
      </div>
    )
  }

  return (
    <div className="setup-wizard">
      <div className="setup-wizard-progress">
        Stap {step} van 4
      </div>
      {error && (
        <div className="setup-wizard-error" role="alert">
          {error}
        </div>
      )}

      {step === 1 && (
        <div className="setup-wizard-step">
          <h2 className="setup-wizard-title">Device &amp; Household</h2>
          <label className="setup-wizard-label">
            Householdnaam
            <input
              type="text"
              className="setup-wizard-input"
              value={householdName}
              onChange={(e) => setHouseholdName(e.target.value)}
              onFocus={() => setFocusedInput('householdName')}
              readOnly={focusedInput === 'householdName'}
              placeholder="Bijv. Thuis"
              autoComplete="organization"
            />
          </label>
          <label className="setup-wizard-label">
            Device naam
            <input
              type="text"
              className="setup-wizard-input"
              value={deviceName}
              onChange={(e) => setDeviceName(e.target.value)}
              onFocus={() => setFocusedInput('deviceName')}
              readOnly={focusedInput === 'deviceName'}
              placeholder="Neuroion Core"
              autoComplete="name"
            />
          </label>
          <div className="setup-wizard-actions">
            <button type="button" className="setup-wizard-btn setup-wizard-btn--primary" onClick={handleStep1Next} disabled={loading}>
              {loading ? 'Bezig…' : 'Volgende'}
            </button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="setup-wizard-step">
          <h2 className="setup-wizard-title">Neuroion Agent naam</h2>
          <label className="setup-wizard-label">
            Naam van je assistent
            <input
              type="text"
              className="setup-wizard-input"
              value={agentName}
              onChange={(e) => setAgentName(e.target.value)}
              onFocus={() => setFocusedInput('agentName')}
              readOnly={focusedInput === 'agentName'}
              placeholder="ion"
              autoComplete="off"
            />
          </label>
          <div className="setup-wizard-actions">
            <button type="button" className="setup-wizard-btn setup-wizard-btn--secondary" onClick={() => setStep(1)}>
              Terug
            </button>
            <button type="button" className="setup-wizard-btn setup-wizard-btn--primary" onClick={handleStep2Next} disabled={loading}>
              {loading ? 'Bezig…' : 'Volgende'}
            </button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="setup-wizard-step">
          <h2 className="setup-wizard-title">WiFi</h2>
          {wifiStatus?.wifi_configured ? (
            <>
              <p className="setup-wizard-wifi-ok">WiFi verbonden: {wifiStatus.ssid || 'Actief'}</p>
              <div className="setup-wizard-actions">
                <button type="button" className="setup-wizard-btn setup-wizard-btn--secondary" onClick={() => setStep(2)}>
                  Terug
                </button>
                <button type="button" className="setup-wizard-btn setup-wizard-btn--primary" onClick={handleStep3Next}>
                  Volgende
                </button>
              </div>
            </>
          ) : (
            <>
              <p className="setup-wizard-hint">Kies een netwerk</p>
              <ul className="setup-wizard-network-list">
                {networks.map((n) => (
                  <li key={n.ssid || n}>
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
                <button type="button" className="setup-wizard-btn setup-wizard-btn--secondary" onClick={() => setStep(2)}>
                  Terug
                </button>
                {selectedSsid ? (
                  <button
                    type="button"
                    className="setup-wizard-btn setup-wizard-btn--primary"
                    onClick={handleStep3Connect}
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
            </>
          )}
        </div>
      )}

      {step === 4 && (
        <div className="setup-wizard-step">
          <h2 className="setup-wizard-title">Start je Neuroion Core One</h2>
          <p className="setup-wizard-hint">Alles is ingesteld. Klik om te starten.</p>
          <div className="setup-wizard-actions">
            <button type="button" className="setup-wizard-btn setup-wizard-btn--secondary" onClick={() => setStep(3)}>
              Terug
            </button>
            <button
              type="button"
              className="setup-wizard-btn setup-wizard-btn--primary setup-wizard-btn--large"
              onClick={handleStep4Start}
              disabled={completing}
            >
              {completing ? 'Bezig…' : 'Start'}
            </button>
          </div>
        </div>
      )}

      {focusedInput && (
        <TouchKeyboard
          visible={!!focusedInput}
          value={
            focusedInput === 'householdName'
              ? householdName
              : focusedInput === 'deviceName'
                ? deviceName
                : focusedInput === 'agentName'
                  ? agentName
                  : focusedInput === 'wifiPassword'
                    ? wifiPassword
                    : ''
          }
          onChange={
            focusedInput === 'householdName'
              ? setHouseholdName
              : focusedInput === 'deviceName'
                ? setDeviceName
                : focusedInput === 'agentName'
                  ? setAgentName
                  : focusedInput === 'wifiPassword'
                    ? setWifiPassword
                    : () => {}
          }
          onClose={() => setFocusedInput(null)}
        />
      )}
    </div>
  )
}

export default SetupWizard
