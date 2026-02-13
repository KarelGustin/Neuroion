import React, { useState, useEffect } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import PixelAnimation from './PixelAnimation'
import ConfigQR from './ConfigQR'
import {
  getDashboardStats,
  getHouseholdMembers,
  getSetupStatus,
  generateLoginCode,
  createDashboardJoinToken,
  deleteMemberFromDashboard,
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

  const [addMemberModal, setAddMemberModal] = useState({ show: false, joinUrl: null, addCountdown: 600 })
  const [deleteMemberModal, setDeleteMemberModal] = useState({ show: false, member: null, error: null })

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

  const openAddMemberModal = async () => {
    try {
      const data = await createDashboardJoinToken(10)
      setAddMemberModal({
        show: true,
        joinUrl: data.join_url,
        addCountdown: 10 * 60,
      })
    } catch (err) {
      console.error('Failed to create join token:', err)
      const detail = err.response?.data?.detail
      const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((d) => d.msg || JSON.stringify(d)).join('. ') : err.message || 'Failed to create add-member link'
      setError(message)
    }
  }

  useEffect(() => {
    if (!addMemberModal.show || addMemberModal.addCountdown <= 0) return
    const t = setInterval(() => {
      setAddMemberModal((prev) =>
        prev.show && prev.addCountdown > 0
          ? { ...prev, addCountdown: prev.addCountdown - 1 }
          : prev
      )
    }, 60000)
    return () => clearInterval(t)
  }, [addMemberModal.show, addMemberModal.addCountdown])

  const openDeleteMemberModal = (member) => (e) => {
    e.stopPropagation()
    setDeleteMemberModal({ show: true, member, error: null })
  }

  const confirmDeleteMember = async () => {
    if (!deleteMemberModal.member) return
    try {
      await deleteMemberFromDashboard(deleteMemberModal.member.id)
      setDeleteMemberModal({ show: false, member: null, error: null })
      const membersList = await getHouseholdMembers()
      setMembers(membersList)
    } catch (err) {
      const detail = err.response?.data?.detail
      const message = Array.isArray(detail)
        ? detail.map((d) => d.msg || JSON.stringify(d)).join('. ')
        : typeof detail === 'string'
          ? detail
          : 'Verwijderen mislukt.'
      setDeleteMemberModal((prev) => ({ ...prev, error: message }))
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
            <p className="dashboard-kiosk-label">Members</p>
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
      <div className="dashboard-members" aria-label="Leden">
        <div className="members-header-row">
          <h2 className="members-title">Members</h2>
          {setupComplete ? (
            <button type="button" className="add-member-btn" onClick={openAddMemberModal}>
              + Add member
            </button>
          ) : (
            <span className="members-setup-hint">Complete setup first</span>
          )}
        </div>
        {members.length > 0 ? (
          <>
            <p className="members-hint">Klik op een naam voor login code</p>
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
                  <button
                    type="button"
                    className="member-remove-btn"
                    onClick={openDeleteMemberModal(member)}
                    title="Remove member"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          </>
        ) : (
          <p className="members-hint">Nog geen members. Klik op + Add member en scan de QR om iemand toe te voegen.</p>
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

      {addMemberModal.show && addMemberModal.joinUrl && (
        <div className="login-code-modal add-member-modal">
          <div className="login-code-content add-member-content">
            <h3>Add member to Neuroion</h3>
            <p className="add-member-hint">Scan de QR of open de link op je telefoon om iemand toe te voegen aan je Neuroion Core.</p>
            <div className="add-member-qr">
              <QRCodeSVG value={addMemberModal.joinUrl} size={220} level="H" includeMargin />
            </div>
            <p className="login-code-timer">Geldig nog {Math.floor(addMemberModal.addCountdown / 60)} min</p>
            <button
              type="button"
              className="close-button"
              onClick={() => setAddMemberModal({ show: false, joinUrl: null, addCountdown: 0 })}
            >
              Sluiten
            </button>
          </div>
        </div>
      )}

      {deleteMemberModal.show && deleteMemberModal.member && (
        <div className="login-code-modal">
          <div className="login-code-content">
            <h3>Member verwijderen</h3>
            <p className="delete-member-warning">
              Weet je het zeker? Alle data van <strong>{deleteMemberModal.member.name}</strong> wordt permanent
              verwijderd.
            </p>
            {deleteMemberModal.error && (
              <p className="delete-member-error">{deleteMemberModal.error}</p>
            )}
            <div className="delete-member-actions">
              <button
                type="button"
                className="close-button"
                onClick={() => setDeleteMemberModal({ show: false, member: null, error: null })}
              >
                Annuleren
              </button>
              <button type="button" className="copy-button" onClick={confirmDeleteMember}>
                Verwijderen
              </button>
            </div>
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
