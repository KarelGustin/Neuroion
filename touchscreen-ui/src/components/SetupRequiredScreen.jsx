import React, { useEffect, useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import '../styles/SetupRequiredScreen.css'

function SetupRequiredScreen({ setupUrl }) {
  const [qrSize, setQrSize] = useState(280)

  useEffect(() => {
    const updateSize = () => {
      const w = window.innerWidth
      const h = window.innerHeight
      const size = Math.min(320, w - 64, h - 200)
      setQrSize(Math.max(160, size))
    }
    updateSize()
    window.addEventListener('resize', updateSize)
    return () => window.removeEventListener('resize', updateSize)
  }, [])

  if (!setupUrl) {
    return (
      <div className="setup-required">
        <p className="setup-required-loading">Loading…</p>
      </div>
    )
  }

  return (
    <div className="setup-required">
      <div className="setup-required-inner">
        <div className="setup-required-logo" aria-label="Neuroion">
          <svg
            viewBox="0 0 100 120"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <path
              d="M 50 20 L 30 60 L 70 60 Z"
              className="setup-logo-triangle"
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
              className="setup-logo-line"
              stroke="currentColor"
              strokeWidth="4"
              strokeLinecap="round"
            />
          </svg>
        </div>
        <h2 className="setup-required-title">Neuroion setup</h2>
        <p className="setup-required-instruction">Scan om te configureren</p>
        <div className="setup-required-code">
          <QRCodeSVG value={setupUrl} size={qrSize} level="H" includeMargin />
        </div>
        <p className="setup-required-url">{setupUrl}</p>
      </div>
    </div>
  )
}

export default SetupRequiredScreen
