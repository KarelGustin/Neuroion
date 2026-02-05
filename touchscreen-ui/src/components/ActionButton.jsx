import React, { useState, useRef } from 'react'
import '../styles/ActionButton.css'

function ActionButton({ label, icon, onClick, variant = 'primary', requiresLongPress = false }) {
  const [showConfirm, setShowConfirm] = useState(false)
  const longPressTimerRef = useRef(null)

  const handlePressStart = () => {
    if (requiresLongPress) {
      longPressTimerRef.current = setTimeout(() => {
        setShowConfirm(true)
        longPressTimerRef.current = null
      }, 2000)
    }
  }

  const handlePressEnd = () => {
    if (requiresLongPress) {
      if (longPressTimerRef.current) {
        clearTimeout(longPressTimerRef.current)
        longPressTimerRef.current = null
      }
      if (showConfirm) {
        onClick()
        setShowConfirm(false)
      }
    } else {
      onClick()
    }
  }

  return (
    <button
      type="button"
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
