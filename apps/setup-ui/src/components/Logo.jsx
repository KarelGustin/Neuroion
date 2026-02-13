import React from 'react'
import '../styles/variables.css'
import '../styles/Logo.css'

function Logo() {
  return (
    <div className="logo-container">
      <svg 
        className="logo-svg" 
        viewBox="0 0 100 120" 
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Triangle (upward pointing) */}
        <path
          d="M 50 20 L 30 60 L 70 60 Z"
          className="logo-triangle"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        
        {/* Vertical line */}
        <line
          x1="50"
          y1="75"
          x2="50"
          y2="100"
          className="logo-line"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
        />
      </svg>
      <span className="logo-text">Neuroion</span>
    </div>
  )
}

export default Logo
