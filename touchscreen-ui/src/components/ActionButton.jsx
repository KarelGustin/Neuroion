import React, { useState, useRef } from 'react'
import '../styles/ActionButton.css'

const DEBOUNCE_MS = 300

function ActionButton({ label, icon, onClick, variant = 'primary', requiresLongPress = false, disabled = false }) {
  const [showConfirm, setShowConfirm] = useState(false)
  const longPressTimerRef = useRef(null)
  const lastInvokeRef = useRef(0)

  const invokeOnce = () => {
    if (disabled) return
    const now = Date.now()
    if (now - lastInvokeRef.current < DEBOUNCE_MS) return
    lastInvokeRef.current = now
    onClick()
  }

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
      invokeOnce()
    }
  }

  const handleClick = () => {
    if (disabled) return
    if (!requiresLongPress) {
      invokeOnce()
    }
  }

  return (
    <button
      type="button"
      className={`action-button ${variant} ${showConfirm ? 'confirm' : ''}`}
      disabled={disabled}
      onTouchStart={handlePressStart}
      onTouchEnd={handlePressEnd}
      onMouseDown={handlePressStart}
      onMouseUp={handlePressEnd}
      onClick={handleClick}
    >
      {icon && <span className="action-icon">{icon}</span>}
      <span className="action-label">{label}</span>
      {showConfirm && <span className="confirm-text">Release to confirm</span>}
    </button>
  )
}

export default ActionButton
