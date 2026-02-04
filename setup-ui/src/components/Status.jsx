import React from 'react'
import '../styles/Status.css'

function Status({ status, error }) {
  const getStatusClass = () => {
    switch (status) {
      case 'ready':
        return 'status-ready'
      case 'error':
        return 'status-error'
      case 'checking':
        return 'status-checking'
      default:
        return 'status-unknown'
    }
  }

  const getStatusText = () => {
    switch (status) {
      case 'ready':
        return 'System Ready'
      case 'error':
        return `Error: ${error || 'Unknown error'}`
      case 'checking':
        return 'Checking system status...'
      default:
        return 'Unknown status'
    }
  }

  return (
    <div className={`status ${getStatusClass()}`}>
      <div className="status-indicator"></div>
      <span className="status-text">{getStatusText()}</span>
    </div>
  )
}

export default Status
