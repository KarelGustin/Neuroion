import React from 'react'
import '../styles/NeuroionLogoCard.css'

/**
 * Sixth status tile: Neuroion logo indicator (reused from setup-ui Logo concept).
 */
function NeuroionLogoCard() {
  return (
    <div className="neuroion-logo-card status-card status-good">
      <div className="status-header">
        <span className="status-icon neuroion-logo-icon">
          <svg
            viewBox="0 0 100 120"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <path
              d="M 50 20 L 30 60 L 70 60 Z"
              className="logo-triangle"
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <line
              x1="50"
              y1="75"
              x2="50"
              y2="100"
              className="logo-line"
              stroke="currentColor"
              strokeWidth="3"
              strokeLinecap="round"
            />
          </svg>
        </span>
        <h3>Neuroion</h3>
      </div>
      <div className="status-body">
        <div className="status-indicator">
          <span className="status-dot status-good" />
          <span className="status-text">Ready</span>
        </div>
      </div>
    </div>
  )
}

export default NeuroionLogoCard
