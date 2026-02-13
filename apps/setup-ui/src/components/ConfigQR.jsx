import React, { useState, useEffect } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import '../styles/ConfigQR.css'

/**
 * Fullscreen QR code for the setup/config page URL.
 * Shown on kiosk when setup is not complete so users can scan and open the wizard on their phone.
 */
function ConfigQR() {
  const [configUrl, setConfigUrl] = useState('')
  const [qrSize, setQrSize] = useState(280)

  useEffect(() => {
    const origin = window.location.origin
    const pathname = window.location.pathname || '/'
    const url = `${origin}${pathname}`
    setConfigUrl(url)
  }, [])

  useEffect(() => {
    const updateSize = () => {
      const w = window.innerWidth
      const h = window.innerHeight
      const size = Math.min(320, w - 48, h - 120)
      setQrSize(Math.max(160, size))
    }
    updateSize()
    window.addEventListener('resize', updateSize)
    return () => window.removeEventListener('resize', updateSize)
  }, [])

  if (!configUrl) {
    return (
      <div className="config-qr">
        <p className="config-qr-loading">Loading...</p>
      </div>
    )
  }

  return (
    <div className="config-qr">
      <div className="config-qr-inner">
        <h2 className="config-qr-title">Neuroion Setup</h2>
        <p className="config-qr-instruction">Scan om te configureren</p>
        <div className="config-qr-code">
          <QRCodeSVG
            value={configUrl}
            size={qrSize}
            level="H"
            includeMargin={true}
          />
        </div>
        <p className="config-qr-url">{configUrl}</p>
      </div>
    </div>
  )
}

export default ConfigQR
