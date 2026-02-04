import React, { useState, useEffect } from 'react'
import PixelAnimation from './PixelAnimation'
import { getDashboardStats } from '../services/api'
import '../styles/Dashboard.css'

function Dashboard() {
  const [stats, setStats] = useState({
    member_count: 0,
    daily_requests: 0,
    wifi_status: 'online',
    wifi_status_color: 'green',
    wifi_message: 'Connected',
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await getDashboardStats()
        setStats(data)
        setError(null)
      } catch (err) {
        console.error('Failed to fetch dashboard stats:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    // Initial fetch
    fetchStats()

    // Poll every 5 seconds
    const interval = setInterval(fetchStats, 5000)

    return () => clearInterval(interval)
  }, [])

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
            <div className="stat-icon">👥</div>
            <div className="stat-content">
              <p className="stat-label">Household Members</p>
              <p className="stat-value">{stats.member_count}</p>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">💬</div>
            <div className="stat-content">
              <p className="stat-label">Requests Today</p>
              <p className="stat-value">{stats.daily_requests}</p>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="dashboard-error">
          <p>Error: {error}</p>
        </div>
      )}
    </div>
  )
}

export default Dashboard
