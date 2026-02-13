import React, { useState } from 'react'
import '../styles/SettingsPanel.css'

function SettingsPanel({ status, onClose, onFactoryReset }) {
  const [confirmReset, setConfirmReset] = useState(false)
  const [resetting, setResetting] = useState(false)

  const handleFactoryResetClick = () => {
    if (!confirmReset) {
      setConfirmReset(true)
      return
    }
    setResetting(true)
    onFactoryReset?.()
  }

  const handleCancelReset = () => {
    setConfirmReset(false)
  }

  return (
    <div className="settings-overlay" role="dialog" aria-modal="true" aria-labelledby="settings-title">
      <div className="settings-panel">
        <div className="settings-header">
          <h2 id="settings-title">Instellingen</h2>
        </div>
        <div className="settings-body">
          <section className="settings-section">
            <h3>Apparaat</h3>
            <dl className="settings-dl">
              {status?.network?.hostname && (
                <>
                  <dt>Naam</dt>
                  <dd>{status.network.hostname}</dd>
                </>
              )}
              {status?.network?.ip && (
                <>
                  <dt>IP</dt>
                  <dd>{status.network.ip}</dd>
                </>
              )}
              {status?.network?.ssid != null && (
                <>
                  <dt>Wi‑Fi</dt>
                  <dd>{status.network.ssid || 'Niet verbonden'}</dd>
                </>
              )}
            </dl>
          </section>
          <section className="settings-section settings-section-danger">
            <h3>Fabrieksinstellingen</h3>
            <p className="settings-warning">
              Alle gegevens worden gewist. Setup moet opnieuw worden doorlopen.
            </p>
            {!confirmReset ? (
              <button
                type="button"
                className="settings-btn settings-btn-danger"
                onClick={handleFactoryResetClick}
                disabled={resetting}
              >
                Terug naar fabrieksinstellingen
              </button>
            ) : (
              <div className="settings-confirm">
                <p className="settings-confirm-text">Weet je het zeker?</p>
                <div className="settings-confirm-actions">
                  <button
                    type="button"
                    className="settings-btn settings-btn-secondary"
                    onClick={handleCancelReset}
                    disabled={resetting}
                  >
                    Annuleren
                  </button>
                  <button
                    type="button"
                    className="settings-btn settings-btn-danger"
                    onClick={handleFactoryResetClick}
                    disabled={resetting}
                  >
                    {resetting ? 'Bezig…' : 'Ja, resetten'}
                  </button>
                </div>
              </div>
            )}
          </section>
        </div>
        <div className="settings-footer">
          <button
            type="button"
            className="settings-btn settings-btn-close"
            onClick={onClose}
          >
            Sluiten
          </button>
        </div>
      </div>
    </div>
  )
}

export default SettingsPanel
