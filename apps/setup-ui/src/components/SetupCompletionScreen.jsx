import React, { useEffect, useState } from 'react'
import '../styles/SetupCompletionScreen.css'

function SetupCompletionScreen({ onDone }) {
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    let cancelled = false
    const start = Date.now()
    const durationMs = 12000
    const tick = () => {
      if (cancelled) return
      const elapsed = Date.now() - start
      const next = Math.min(100, Math.round((elapsed / durationMs) * 100))
      setProgress(next)
      if (next >= 100) {
        setTimeout(() => onDone?.(), 500)
        return
      }
      requestAnimationFrame(tick)
    }
    tick()
    return () => {
      cancelled = true
    }
  }, [onDone])

  return (
    <div className="setup-completion-screen">
      <div className="completion-card">
        <div className="completion-logo">Neuroion</div>
        <p className="completion-text">We schakelen over naar je Wi‑Fi…</p>
        <div className="completion-bar">
          <div className="completion-bar-fill" style={{ width: `${progress}%` }} />
        </div>
        <div className="completion-percent">{progress}%</div>
      </div>
    </div>
  )
}

export default SetupCompletionScreen
