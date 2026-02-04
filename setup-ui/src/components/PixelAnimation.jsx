import React, { useEffect, useState } from 'react'
import '../styles/PixelAnimation.css'

function PixelAnimation({ status = 'online' }) {
  const [animationPhase, setAnimationPhase] = useState(0)

  useEffect(() => {
    // Animate through phases to create flowing effect
    const interval = setInterval(() => {
      setAnimationPhase(prev => (prev + 1) % 4)
    }, 800)

    return () => clearInterval(interval)
  }, [])

  const getStatusClass = () => {
    switch (status) {
      case 'online':
        return 'pixel-online'
      case 'no_signal':
        return 'pixel-no-signal'
      case 'error':
        return 'pixel-error'
      default:
        return 'pixel-online'
    }
  }

  return (
    <div className={`pixel-animation ${getStatusClass()}`}>
      <div className="logo-inspired">
        {/* Triangle made of separate segments */}
        {/* Top segment - horizontal */}
        <div className="triangle-segment segment-top" data-phase={animationPhase}></div>
        {/* Left segment - angled side */}
        <div className="triangle-segment segment-left" data-phase={animationPhase}></div>
        {/* Right segment - angled side */}
        <div className="triangle-segment segment-right" data-phase={animationPhase}></div>
        
        {/* Vertical line below triangle center */}
        <div className="vertical-line" data-phase={animationPhase}></div>
        
        {/* Glow effect */}
        <div className="glow-effect"></div>
      </div>
    </div>
  )
}

export default PixelAnimation
