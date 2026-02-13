import React, { useState, useEffect } from 'react'
import PixelAnimation from './PixelAnimation'
import ConfigQR from './ConfigQR'
import {
  getDashboardStats,
  getHouseholdMembers,
  getSetupStatus,
  generateLoginCode,
} from '../services/api'
import '../styles/Dashboard.css'

function Dashboard({ isKiosk = false }) {
  const [stats, setStats] = useState({
    member_count: 0,
    daily_requests: 0,
    wifi_status: 'online',
    wifi_status_color: 'green',
    wifi_message: 'Connected',
    days_since_boot: 0,
  })
  const [members, setMembers] = useState([])
  const [setupComplete, setSetupComplete] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [loginCode, setLoginCode] = useState(null)
  const [countdown, setCountdown] = useState(60)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await getDashboardStats()
        setStats(data)
        setError(null)
      } catch (err) {
        console.error('Failed to fetch dashboard stats:', err)
        setError(err.message)
      }
    }

    const fetchMembers = async () => {
      try {
        const membersList = await getHouseholdMembers()
        setMembers(membersList)
      } catch (err) {
        console.error('Failed to fetch members:', err)
      }
    }

    const fetchSetupComplete = async () => {
      try {
        const s = await getSetupStatus()
        setSetupComplete(s.is_complete)
      } catch (_) {
        setSetupComplete(false)
      }
    }

    const loadAll = async () => {
      await Promise.all([fetchStats(), fetchMembers(), fetchSetupComplete()])
    }

    loadAll().finally(() => setLoading(false))

    const interval = setInterval(() => {
      fetchStats()
      fetchMembers()
      fetchSetupComplete()
    }, 60000)

    return () => clearInterval(interval)
  }, [])

  // Countdown timer for login code
  useEffect(() => {
    if (loginCode && countdown > 0) {
      const timer = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            setLoginCode(null)
            return 60
          }
          return prev - 1
        })
      }, 1000)
      return () => clearInterval(timer)
    } else if (loginCode && countdown === 0) {
      setLoginCode(null)
      setCountdown(60)
    }
  }, [loginCode, countdown])

  const handleMemberClick = async (userId) => {
    try {
      const result = await generateLoginCode(userId)
      setLoginCode(result.code)
      setCountdown(60)
    } catch (err) {
      console.error('Failed to generate login code:', err)
      alert('Failed to generate login code. Please try again.')
    }
  }

  const copyToClipboard = () => {
    if (loginCode) {
      navigator.clipboard.writeText(loginCode)
      alert('Login code copied to clipboard!')
    }
  }

  if (loading && !isKiosk) {
    return (
      <div className="dashboard dashboard-loading">
        <p>Loading dashboard...</p>
      </div>
    )
  }

  if (!loading && !setupComplete) {
    return (
      <div className="app">
        <ConfigQR />
      </div>
    )
  }

  /* Kiosk mode: grid van 4 tiles – Members, WiFi, Requests, Dagen sinds geboot */
  if (isKiosk) {
    return (
      <div className="dashboard dashboard--kiosk">
        <div className="dashboard-kiosk-grid">
          <div className="dashboard-kiosk-tile kiosk-tile-members">
            <p className="dashboard-kiosk-label">User</p>
            <p className="dashboard-kiosk-value">{stats.member_count}</p>
          </div>
          <div className="dashboard-kiosk-tile kiosk-tile-wifi">
            <p className="dashboard-kiosk-label">WiFi-verbinding</p>
            <div className="dashboard-kiosk-wifi">
              <PixelAnimation status={stats.wifi_status} />
              <p className={`dashboard-kiosk-value status-${stats.wifi_status_color}`}>{stats.wifi_message}</p>
            </div>
          </div>
          <div className="dashboard-kiosk-tile kiosk-tile-requests">
            <p className="dashboard-kiosk-label">Neuroion Requests</p>
            <p className="dashboard-kiosk-value">{stats.daily_requests}</p>
          </div>
          <div className="dashboard-kiosk-tile kiosk-tile-days">
            <p className="dashboard-kiosk-label">Dagen sinds geboot</p>
            <p className="dashboard-kiosk-value">{stats.days_since_boot ?? 0}</p>
          </div>
        </div>
        {error && (
          <div className="dashboard-error">
            <p>{error}</p>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="dashboard dashboard--fullscreen">
      <div className="dashboard-status" aria-label="Connection">
        <PixelAnimation status={stats.wifi_status} />
        <div className="status-info">
          <p className="status-label">Connection</p>
          <p className={`status-value status-${stats.wifi_status_color}`}>
            {stats.wifi_message}
          </p>
        </div>
      </div>
      <div className="dashboard-stat" aria-label="Neuroion Requests">
        <p className="stat-label">Neuroion Requests</p>
        <p className="stat-value">{stats.daily_requests}</p>
      </div>
      <div className="dashboard-members" aria-label="User">
        <div className="members-header-row">
          <h2 className="members-title">User</h2>
        </div>
        {members.length > 0 ? (
          <>
            <p className="members-hint">Klik op je naam voor login code</p>
            <div className="members-list">
              {members.map((member) => (
                <div key={member.id} className="member-row">
                  <button
                    type="button"
                    className="member-item"
                    onClick={() => handleMemberClick(member.id)}
                  >
                    <span className="member-name">{member.name}</span>
                    <span className="member-role">{member.role}</span>
                  </button>
                </div>
              ))}
            </div>
          </>
        ) : (
          <p className="members-hint">Nog geen user. Voltooi eerst de setup.</p>
        )}
      </div>

      {loginCode && (
        <div className="login-code-modal">
          <div className="login-code-content">
            <h3>Login Code</h3>
            <div className="login-code-display">
              <span className="login-code-value">{loginCode}</span>
              <button type="button" className="copy-button" onClick={copyToClipboard}>
                Copy
              </button>
            </div>
            <p className="login-code-timer">Expires in {countdown} seconds</p>
            <button type="button" className="close-button" onClick={() => setLoginCode(null)}>
              Close
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="dashboard-error">
          <p>Error: {error}</p>
        </div>
      )}
    </div>
  )
}

export default Dashboard
