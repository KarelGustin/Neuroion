import React from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { getApiBaseUrl } from '../services/api'
import '../styles/DashboardLinkScreen.css'

const DASHBOARD_PORT = 3001

/**
 * Builds the URL that the iOS app scans to connect in one step (base URL + pairing code).
 */
function buildAppPairingQRValue(apiBase, pairingCode) {
  return `neuroion://pair?base=${encodeURIComponent(apiBase)}&code=${encodeURIComponent(pairingCode)}`
}

function DashboardLinkScreen({ pairingCode = null }) {
  const dashboardUrl =
    typeof window !== 'undefined'
      ? `${window.location.protocol}//${window.location.hostname}:${DASHBOARD_PORT}`
      : `http://localhost:${DASHBOARD_PORT}`

  const apiBase = typeof window !== 'undefined' ? getApiBaseUrl() : ''
  const appPairingQRValue = pairingCode && apiBase ? buildAppPairingQRValue(apiBase, pairingCode) : null

  return (
    <div className="app">
      <div className="container">
        <div className="dashboard-link-card">
          <h2 className="dashboard-link-title">Setup voltooid</h2>
          <p className="dashboard-link-text">
            Open het dashboard op het touchscreen of op een ander apparaat op je netwerk.
          </p>
          <a
            href={dashboardUrl}
            className="dashboard-link-button"
            target="_blank"
            rel="noopener noreferrer"
          >
            Open dashboard
          </a>
          <p className="dashboard-link-url">{dashboardUrl}</p>
        </div>

        {appPairingQRValue && (
          <div className="dashboard-link-card dashboard-link-app-qr">
            <h3 className="dashboard-link-app-qr-title">iPhone koppelen</h3>
            <p className="dashboard-link-app-qr-text">
              Open de Neuroion-app op je iPhone en scan deze QR-code om te koppelen.
            </p>
            <div className="dashboard-link-app-qr-code">
              <QRCodeSVG value={appPairingQRValue} size={200} level="H" includeMargin />
            </div>
            <p className="dashboard-link-app-qr-code-label">Code: {pairingCode}</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default DashboardLinkScreen
