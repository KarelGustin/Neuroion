import React from 'react'
import { QRCodeSVG } from 'qrcode.react'
import '../styles/QRDisplay.css'

function QRDisplay({ url, title, onClose, openOnDeviceLabel }) {
  return (
    <div className="qr-overlay" onClick={onClose}>
      <div className="qr-container" onClick={(e) => e.stopPropagation()}>
        <h3>{title}</h3>
        <div className="qr-code">
          <QRCodeSVG value={url} size={300} level="H" includeMargin={true} />
        </div>
        <p className="qr-url">{url}</p>
        {openOnDeviceLabel && (
          <button
            type="button"
            className="qr-open-on-device"
            onClick={() => { window.location.href = url }}
          >
            {openOnDeviceLabel}
          </button>
        )}
        <button className="qr-close" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  )
}

export default QRDisplay
