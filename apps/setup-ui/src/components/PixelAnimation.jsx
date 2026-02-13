import React, { useState } from 'react'
import '../styles/PixelAnimation.css'
// Import the existing logo from assets
import logoImage from '../assets/ChatGPT Image Feb 2, 2026, 11_56_17 AM.png'

function PixelAnimation({ status = 'online' }) {
  const [logoError, setLogoError] = useState(false)

  const getStatusClass = () => {
    switch (status) {
      case 'online':
        return 'pixel-online'
      case 'no_signal':
        return 'pixel-no-signal'
      case 'error':
        return 'pixel-error'
      default:
        return 'pixel-online'
    }
  }

  // Fallback: show a placeholder if logo fails to load
  if (logoError) {
    return (
      <div className={`pixel-animation ${getStatusClass()}`}>
        <div className="logo-container">
          <div className="logo-placeholder">
            <div className="logo-placeholder-text">Logo</div>
            <div className="logo-placeholder-hint">Logo image failed to load</div>
          </div>
          <div className="glow-effect"></div>
        </div>
      </div>
    )
  }

  return (
    <div className={`pixel-animation ${getStatusClass()}`}>
      <div className="logo-container">
        <img 
          src={logoImage} 
          alt="Neuroion Logo" 
          className="logo-image"
          onError={() => setLogoError(true)}
        />
        <div className="glow-effect"></div>
      </div>
    </div>
  )
}

export default PixelAnimation
