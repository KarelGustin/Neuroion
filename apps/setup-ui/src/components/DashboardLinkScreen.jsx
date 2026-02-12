import React from 'react'
import '../styles/DashboardLinkScreen.css'

const DASHBOARD_PORT = 3001

function DashboardLinkScreen() {
  const dashboardUrl =
    typeof window !== 'undefined'
      ? `${window.location.protocol}//${window.location.hostname}:${DASHBOARD_PORT}`
      : `http://localhost:${DASHBOARD_PORT}`

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
      </div>
    </div>
  )
}

export default DashboardLinkScreen
