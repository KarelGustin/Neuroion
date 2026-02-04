import React, { useState, useEffect } from 'react'
import PixelAnimation from './PixelAnimation'
import { getDashboardStats, getHouseholdMembers, generateLoginCode } from '../services/api'
import '../styles/Dashboard.css'

function Dashboard() {
  const [stats, setStats] = useState({
    member_count: 0,
    daily_requests: 0,
    wifi_status: 'online',
    wifi_status_color: 'green',
    wifi_message: 'Connected',
  })
  const [members, setMembers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [loginCode, setLoginCode] = useState(null)
  const [countdown, setCountdown] = useState(60)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await getDashboardStats()
        console.log('Dashboard stats received:', data) // Debug log
        setStats(data)
        setError(null)
      } catch (err) {
        console.error('Failed to fetch dashboard stats:', err)
        setError(err.message)
      } finally {
        setLoading(false)
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

    // Initial fetch
    fetchStats()
    fetchMembers()

    // Poll every 5 seconds
    const interval = setInterval(() => {
      fetchStats()
      fetchMembers()
    }, 5000)

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

  if (loading) {
    return (
      <div className="dashboard">
        <div className="dashboard-loading">
          <p>Loading dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1 className="dashboard-title">Neuroion</h1>
        <p className="dashboard-subtitle">Home Intelligence Platform</p>
      </div>

      <div className="dashboard-content">
        <div className="dashboard-status">
          <PixelAnimation status={stats.wifi_status} />
          <div className="status-info">
            <p className="status-label">Connection Status</p>
            <p className={`status-value status-${stats.wifi_status_color}`}>
              {stats.wifi_message}
            </p>
          </div>
        </div>

        <div className="dashboard-stats">
          <div className="stat-card">
            <div className="stat-content">
              <p className="stat-label">Household Members</p>
              <p className="stat-value">{stats.member_count}</p>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-content">
              <p className="stat-label">Requests Today</p>
              <p className="stat-value">{stats.daily_requests}</p>
            </div>
          </div>
        </div>

        {members.length > 0 && (
          <div className="dashboard-members">
            <h2 className="members-title">Household Members</h2>
            <p className="members-hint">Click a name to get login code</p>
            <div className="members-list">
              {members.map((member) => (
                <button
                  key={member.id}
                  className="member-item"
                  onClick={() => handleMemberClick(member.id)}
                >
                  <span className="member-name">{member.name}</span>
                  <span className="member-role">{member.role}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {loginCode && (
        <div className="login-code-modal">
          <div className="login-code-content">
            <h3>Login Code</h3>
            <div className="login-code-display">
              <span className="login-code-value">{loginCode}</span>
              <button className="copy-button" onClick={copyToClipboard}>
                Copy
              </button>
            </div>
            <p className="login-code-timer">Expires in {countdown} seconds</p>
            <button className="close-button" onClick={() => setLoginCode(null)}>
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
