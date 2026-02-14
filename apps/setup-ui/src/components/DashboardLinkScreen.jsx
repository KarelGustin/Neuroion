import React from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { getApiBaseUrl } from '../services/api'
import '../styles/DashboardLinkScreen.css'

const DASHBOARD_PORT = 3001

/** VPN base URL when using WireGuard (fixed IP on unit). */
const VPN_BASE_URL = 'https://10.66.66.1'

/**
 * Builds the URL that the iOS app scans to connect in one step (base URL + pairing code).
 * @param {boolean} [vpn=false] - If true, use VPN base URL and add vpn=1 so app requests WireGuard config.
 */
function buildAppPairingQRValue(apiBase, pairingCode, vpn = false) {
  const base = vpn ? VPN_BASE_URL : apiBase
  const params = new URLSearchParams({ base, code: pairingCode })
  if (vpn) params.set('vpn', '1')
  return `neuroion://pair?${params.toString()}`
}

function DashboardLinkScreen({ pairingCode = null }) {
  const dashboardUrl =
    typeof window !== 'undefined'
      ? `${window.location.protocol}//${window.location.hostname}:${DASHBOARD_PORT}`
      : `http://localhost:${DASHBOARD_PORT}`

  const apiBase = typeof window !== 'undefined' ? getApiBaseUrl() : ''
  const appPairingQRValue = pairingCode && apiBase ? buildAppPairingQRValue(apiBase, pairingCode) : null
  const appPairingQRValueVpn = pairingCode ? buildAppPairingQRValue(apiBase, pairingCode, true) : null
  const inviteQRValue = inviteCode && apiBase ? buildAppPairingQRValue(apiBase, inviteCode) : null

  const handleInviteMember = async () => {
    setInviteError(null)
    setInviteLoading(true)
    try {
      const code = await getPairingCode(
        HOUSEHOLD_ID,
        `invite-${Date.now()}`,
        'ios',
        'Nieuwe member'
      )
      setInviteCode(code)
    } catch (err) {
      setInviteError(err.response?.data?.detail || err.message || 'Kon geen code ophalen')
    } finally {
      setInviteLoading(false)
    }
  }

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
        {appPairingQRValueVpn && (
          <div className="dashboard-link-card dashboard-link-app-qr">
            <h3 className="dashboard-link-app-qr-title">iPhone koppelen (via VPN)</h3>
            <p className="dashboard-link-app-qr-text">
              Scan om te koppelen met VPN: daarna bereik je Neuroion overal via 10.66.66.1.
            </p>
            <div className="dashboard-link-app-qr-code">
              <QRCodeSVG value={appPairingQRValueVpn} size={200} level="H" includeMargin />
            </div>
            <p className="dashboard-link-app-qr-code-label">Code: {pairingCode}</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default DashboardLinkScreen
