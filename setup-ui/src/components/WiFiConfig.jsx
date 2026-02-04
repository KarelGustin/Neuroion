import React, { useState, useEffect } from 'react'
import { configureWiFi, scanWiFiNetworks, checkInternetConnection } from '../services/api'
import '../styles/WiFiConfig.css'

function WiFiConfig({ onComplete, onBack, initialData }) {
  // Load from localStorage if initialData is not provided
  const loadFromStorage = () => {
    try {
      const saved = localStorage.getItem('neuroion_setup_wifi')
      if (saved) {
        return JSON.parse(saved)
      }
    } catch (err) {
      console.error('Failed to load WiFi config from storage:', err)
    }
    return null
  }

  const savedData = initialData || loadFromStorage()
  const [ssid, setSsid] = useState(savedData?.ssid || '')
  const [password, setPassword] = useState(savedData?.password || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)
  const [networks, setNetworks] = useState([])
  const [scanning, setScanning] = useState(false)
  const [showNetworks, setShowNetworks] = useState(true)
  const [selectedNetwork, setSelectedNetwork] = useState(null)
  const [internetConnected, setInternetConnected] = useState(null)
  const [checkingInternet, setCheckingInternet] = useState(true)
  const [showManualInput, setShowManualInput] = useState(false)

  useEffect(() => {
    // Check internet connection on mount
    const checkInternet = async () => {
      setCheckingInternet(true)
      try {
        const result = await checkInternetConnection()
        setInternetConnected(result.connected)
        // If internet is connected, automatically show WiFi form and minimize off-grid option
        if (result.connected) {
          setShowNetworks(true)
        }
      } catch (err) {
        console.error('Failed to check internet connection:', err)
        setInternetConnected(false)
      } finally {
        setCheckingInternet(false)
      }
    }

    checkInternet()
    // Scan for networks on mount
    handleScan()
  }, [])

  const handleScan = async () => {
    setScanning(true)
    setError(null)
    try {
      const availableNetworks = await scanWiFiNetworks()
      // Sort by signal strength (highest first)
      availableNetworks.sort((a, b) => b.signal_strength - a.signal_strength)
      setNetworks(availableNetworks)
    } catch (err) {
      setError(err.message || 'Failed to scan for networks')
    } finally {
      setScanning(false)
    }
  }

  const handleNetworkSelect = (network) => {
    setSsid(network.ssid)
    setSelectedNetwork(network)
    setShowNetworks(false)
    setShowManualInput(true) // Show form when network is selected
    // Clear password if switching to open network
    if (network.security === 'Open') {
      setPassword('')
    }
  }

  const handleSkipWiFi = () => {
    // Skip WiFi configuration and continue to next step
    const skipData = { skipped: true }
    // Save skip to localStorage
    try {
      localStorage.setItem('neuroion_setup_wifi', JSON.stringify(skipData))
    } catch (err) {
      console.error('Failed to save WiFi skip:', err)
    }
    onComplete(skipData)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(false)

    try {
      const result = await configureWiFi(ssid, password)
      if (result.success) {
        setSuccess(true)
        const wifiData = { ssid, password }
        // Save to localStorage
        try {
          localStorage.setItem('neuroion_setup_wifi', JSON.stringify(wifiData))
        } catch (err) {
          console.error('Failed to save WiFi config:', err)
        }
        setTimeout(() => {
          onComplete(wifiData)
        }, 1000)
      } else {
        setError(result.message || 'Failed to configure WiFi')
      }
    } catch (err) {
      setError(err.message || 'Failed to configure WiFi')
    } finally {
      setLoading(false)
    }
  }

  const getSignalIcon = (strength) => {
    if (strength >= 75) return '▂▄▆█'
    if (strength >= 50) return '▂▄▆▁'
    if (strength >= 25) return '▂▄▁▁'
    return '▂▁▁▁'
  }

  const getSecurityIcon = (security) => {
    if (security === 'WPA2' || security === 'WPA') return '🔒'
    return '🔓'
  }

  return (
    <div className="wifi-config">
      <div className="config-header">
        <h3>WiFi Configuration</h3>
        <p>Connect your Neuroion Homebase to your WiFi network</p>
        {checkingInternet ? (
          <p className="internet-status checking">Checking internet connection...</p>
        ) : internetConnected ? (
          <p className="internet-status connected">
            ✓ Internet connection detected - WiFi mode recommended
          </p>
        ) : (
          <p className="off-grid-note">
            You can continue without WiFi for offline operation
          </p>
        )}
      </div>

      {!internetConnected && (
        <div className="off-grid-section">
          <button
            type="button"
            onClick={handleSkipWiFi}
            className="btn-off-grid"
            disabled={loading || success}
          >
            <span className="off-grid-icon">📡</span>
            <div className="off-grid-content">
              <strong>Continue Off Grid</strong>
              <span>Skip WiFi setup and use offline mode</span>
            </div>
          </button>
        </div>
      )}

      {showNetworks && (
        <div className="networks-section">
          <div className="networks-header">
            <h4>Available Networks</h4>
            <button
              type="button"
              onClick={handleScan}
              disabled={scanning}
              className="btn-scan"
            >
              {scanning ? 'Scanning...' : 'Refresh'}
            </button>
          </div>
          
          {scanning && networks.length === 0 ? (
            <div className="scanning-message">Scanning for networks...</div>
          ) : networks.length === 0 ? (
            <div className="no-networks">No networks found. Try refreshing.</div>
          ) : (
            <div className="networks-list">
              {networks.map((network, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => handleNetworkSelect(network)}
                  className={`network-item ${ssid === network.ssid ? 'selected' : ''}`}
                >
                  <div className="network-info">
                    <div className="network-name">
                      {getSecurityIcon(network.security)} {network.ssid}
                    </div>
                    <div className="network-details">
                      <span className="network-security">{network.security}</span>
                      <span className="network-frequency">{network.frequency}</span>
                    </div>
                  </div>
                  <div className="network-signal">
                    <span className="signal-bars">{getSignalIcon(network.signal_strength)}</span>
                    <span className="signal-strength">{network.signal_strength}%</span>
                  </div>
                </button>
              ))}
            </div>
          )}
          
          <button
            type="button"
            onClick={() => {
              setShowNetworks(false)
              setShowManualInput(true)
            }}
            className="btn-manual"
          >
            Enter network manually
          </button>
        </div>
      )}

      {!showNetworks && !showManualInput && (
        <button
          type="button"
          onClick={() => {
            setShowNetworks(true)
            handleScan()
          }}
          className="btn-show-networks"
        >
          ← Show available networks
        </button>
      )}

      {showManualInput && (
        <form onSubmit={handleSubmit} className="wifi-form">
        {!showNetworks && (
          <button
            type="button"
            onClick={() => {
              setShowNetworks(true)
              setShowManualInput(false)
              setSsid('')
              setPassword('')
              setSelectedNetwork(null)
              handleScan()
            }}
            className="btn-show-networks"
            style={{ marginBottom: '1rem' }}
          >
            ← Show available networks
          </button>
        )}
        
        <div className="form-group">
          <label htmlFor="ssid">Network Name (SSID)</label>
          <input
            type="text"
            id="ssid"
            value={ssid}
            onChange={(e) => setSsid(e.target.value)}
            required
            placeholder="Enter WiFi network name"
            disabled={loading || success}
          />
        </div>

        <div className="form-group">
          <label htmlFor="password">
            Password
            {selectedNetwork && selectedNetwork.security === 'Open' && (
              <span className="optional-label"> (Optional - Open network)</span>
            )}
          </label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required={!selectedNetwork || selectedNetwork.security !== 'Open'}
            placeholder={
              selectedNetwork && selectedNetwork.security === 'Open'
                ? 'No password required'
                : 'Enter WiFi password'
            }
            disabled={loading || success}
          />
        </div>

        {error && <div className="error-message">{error}</div>}
        {success && (
          <div className="success-message">WiFi configured successfully!</div>
        )}

        <div className="form-actions">
          {onBack && (
            <button type="button" onClick={onBack} className="btn-secondary">
              Back
            </button>
          )}
          <button
            type="submit"
            className="btn-primary"
            disabled={
              loading ||
              success ||
              !ssid ||
              (selectedNetwork && selectedNetwork.security !== 'Open' && !password) ||
              (!selectedNetwork && !password)
            }
          >
            {loading ? 'Configuring...' : success ? 'Success!' : 'Connect WiFi'}
          </button>
        </div>
      </form>
      )}
    </div>
  )
}

export default WiFiConfig
