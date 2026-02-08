import React from 'react'
import '../styles/Welcome.css'

/**
 * Step 0: Welcome — brief intro + fallback URL + CTA Start.
 * One tap to continue.
 */
function Welcome({ onComplete, onBack }) {
  const setupUrl = typeof window !== 'undefined'
    ? `${window.location.origin}${window.location.pathname || '/'}`
    : 'http://192.168.4.1/setup'

  return (
    <div className="welcome-step">
      <div className="welcome-content">
        <h3 className="welcome-title">Welcome to Neuroion Core</h3>
        <p className="welcome-text">
          In a few steps we will set up your system identity, local AI, and how you want to talk to Neuroion.
          You will connect to your home Wi-Fi near the end of the setup.
        </p>
        <p className="welcome-fallback">
          If the setup page doesn't open automatically, go to:
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
