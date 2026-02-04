import React from 'react'
import '../styles/StatusCard.css'

function StatusCard({ title, status, details, icon }) {
  const getStatusClass = () => {
    if (status === 'connected' || status === 'running' || status === 'ok') {
      return 'status-good'
    } else if (status === 'error' || status === 'failed') {
      return 'status-error'
    }
    return 'status-warning'
  }

  return (
    <div className={`status-card ${getStatusClass()}`}>
      <div className="status-header">
        {icon && <span className="status-icon">{icon}</span>}
        <h3>{title}</h3>
      </div>
      <div className="status-body">
        <div className="status-indicator">
          <span className={`status-dot ${getStatusClass()}`}></span>
          <span className="status-text">{status}</span>
        </div>
        {details && (
          <div className="status-details">
            {Object.entries(details).map(([key, value]) => (
              <div key={key} className="detail-item">
                <span className="detail-key">{key}:</span>
                <span className="detail-value">{value}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default StatusCard
