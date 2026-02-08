import React from 'react'
import '../styles/BootScreen.css'

function BootScreen({ progress = 0, stage = 'starting' }) {
  return (
    <div className="boot-screen">
      <div className="boot-logo" aria-label="Neuroion">
        <svg
          viewBox="0 0 100 120"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path
            d="M 50 20 L 30 60 L 70 60 Z"
            className="boot-logo-triangle"
            fill="none"
            stroke="currentColor"
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <line
            x1="50"
            y1="75"
            x2="50"
            y2="105"
            className="boot-logo-line"
            stroke="currentColor"
            strokeWidth="4"
            strokeLinecap="round"
          />
        </svg>
      </div>
      <div className="boot-loader" aria-live="polite">
        <div className="boot-stage">{stage.replace(/-/g, ' ')}</div>
        <div className="boot-bar">
          <div className="boot-bar-fill" style={{ width: `${Math.min(100, Math.max(0, progress))}%` }} />
        </div>
        <div className="boot-percent">{Math.min(100, Math.max(0, progress))}%</div>
      </div>
    </div>
  )
}

export default BootScreen
