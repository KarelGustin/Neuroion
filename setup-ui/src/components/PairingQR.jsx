import React from 'react'
import { QRCodeSVG } from 'qrcode.react'
import '../styles/PairingQR.css'

function PairingQR({ code, botUsername }) {
  // Create Telegram deep link URL
  // Format: https://t.me/botname?start=PAIRING_CODE
  const telegramUrl = botUsername 
    ? `https://t.me/${botUsername}?start=${code}`
    : `neuroion://pair?code=${code}`

  return (
    <div className="pairing-qr">
      <div className="qr-container">
        <QRCodeSVG
          value={telegramUrl}
          size={400}
          level="H"
          includeMargin={true}
        />
      </div>
      <div className="code-display">
        <p className="code-label">Pairing Code</p>
        <p className="code-value">{code}</p>
      </div>
      <p className="code-instructions">
        {botUsername 
          ? `Scan QR code with Telegram to pair, or use /start ${code} in @${botUsername}`
          : "Enter this code in your app or scan the QR code"}
      </p>
    </div>
  )
}

export default PairingQR
