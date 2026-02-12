import React, { useCallback } from 'react'
import '../styles/TouchKeyboard.css'

const ROWS = [
  ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
  ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
  ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],
  ['z', 'x', 'c', 'v', 'b', 'n', 'm', '⌫'],
]

function TouchKeyboard({ value = '', onChange, onClose, visible }) {
  const handleKey = useCallback(
    (key) => {
      if (key === '⌫') {
        onChange(value.slice(0, -1))
      } else {
        onChange(value + key)
      }
    },
    [value, onChange]
  )

  if (!visible) return null

  return (
    <>
      <div
        className="touch-keyboard-backdrop"
        onClick={onClose}
        onTouchEnd={(e) => {
          e.preventDefault()
          onClose?.()
        }}
        aria-hidden="true"
      />
      <div className="touch-keyboard" role="group" aria-label="On-screen keyboard">
        <div className="touch-keyboard-grid">
          {ROWS.map((row, rowIndex) => (
            <div key={rowIndex} className="touch-keyboard-row">
              {row.map((key) => (
                <button
                  key={key}
                  type="button"
                  className={`touch-keyboard-key ${key === '⌫' ? 'touch-keyboard-key--backspace' : ''}`}
                  onClick={() => handleKey(key)}
                  onTouchEnd={(e) => {
                    e.preventDefault()
                    handleKey(key)
                  }}
                >
                  {key}
                </button>
              ))}
            </div>
          ))}
        </div>
        <div className="touch-keyboard-row touch-keyboard-row--bottom">
          <button
            type="button"
            className="touch-keyboard-key touch-keyboard-key--space"
            onClick={() => handleKey(' ')}
            onTouchEnd={(e) => {
              e.preventDefault()
              handleKey(' ')
            }}
          >
            spatie
          </button>
          <button
            type="button"
            className="touch-keyboard-key touch-keyboard-key--close"
            onClick={onClose}
            onTouchEnd={(e) => {
              e.preventDefault()
              onClose?.()
            }}
          >
            Sluiten
          </button>
        </div>
      </div>
    </>
  )
}

export default TouchKeyboard
