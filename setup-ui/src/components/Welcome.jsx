import React from 'react'
import '../styles/Welcome.css'

/**
 * Step 0: Welcome — "Connect to Neuroion Core Wi-Fi" + fallback URL + CTA Start.
 * One tap to continue to WiFi step.
 */
function Welcome({ onComplete, onBack }) {
  const setupUrl = typeof window !== 'undefined'
    ? `${window.location.origin}${window.location.pathname || '/'}`
    : 'http://192.168.4.1/setup'

  return (
    <div className="welcome-step">
      <div className="welcome-content">
        <h3 className="welcome-title">Connect to Neuroion Core Wi‑Fi</h3>
        <p className="welcome-text">
          Connect your phone or tablet to the <strong>Neuroion-Setup</strong> Wi‑Fi network.
          Then open the setup page to configure your Neuroion Core.
        </p>
        <p className="welcome-fallback">
          If the setup page doesn’t open automatically, go to:
        </p>
        <p className="welcome-url">{setupUrl}</p>
        <button
          type="button"
          className="welcome-cta"
          onClick={() => onComplete && onComplete({ started: true })}
        >
          Start
        </button>
      </div>
    </div>
  )
}

export default Welcome
