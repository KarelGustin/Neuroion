import React, { useState } from 'react'
import '../styles/ActionButton.css'

function ActionButton({ label, icon, onClick, variant = 'primary', requiresLongPress = false }) {
  const [pressStart, setPressStart] = useState(null)
  const [showConfirm, setShowConfirm] = useState(false)

  const handlePressStart = () => {
    if (requiresLongPress) {
      setPressStart(Date.now())
      setTimeout(() => {
        if (pressStart && Date.now() - pressStart >= 2000) {
          setShowConfirm(true)
        }
      }, 2000)
    }
  }

  const handlePressEnd = () => {
    if (requiresLongPress) {
      if (showConfirm) {
        onClick()
        setShowConfirm(false)
      }
      setPressStart(null)
    } else {
      onClick()
    }
  }

  return (
    <button
      className={`action-button ${variant} ${showConfirm ? 'confirm' : ''}`}
      onTouchStart={handlePressStart}
      onTouchEnd={handlePressEnd}
      onMouseDown={handlePressStart}
      onMouseUp={handlePressEnd}
    >
      {icon && <span className="action-icon">{icon}</span>}
      <span className="action-label">{label}</span>
      {showConfirm && <span className="confirm-text">Release to confirm</span>}
    </button>
  )
}

export default ActionButton
