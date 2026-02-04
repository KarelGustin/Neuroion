import React, { useState, useEffect } from 'react'
import WiFiConfig from './WiFiConfig'
import HouseholdSetup from './HouseholdSetup'
import OwnerProfile from './OwnerProfile'
import PrivacySettings from './PrivacySettings'
import ModelPreset from './ModelPreset'
import '../styles/SetupWizard.css'

const STORAGE_KEYS = {
  wifi: 'neuroion_setup_wifi',
  household: 'neuroion_setup_household',
  owner: 'neuroion_setup_owner',
  privacy: 'neuroion_setup_privacy',
  model: 'neuroion_setup_model',
}

function SetupWizard({ onComplete }) {
  const [currentStep, setCurrentStep] = useState(1)
  const [wifiConfig, setWifiConfig] = useState(null)
  const [householdConfig, setHouseholdConfig] = useState(null)
  const [ownerConfig, setOwnerConfig] = useState(null)
  const [privacyConfig, setPrivacyConfig] = useState(null)
  const [modelConfig, setModelConfig] = useState(null)

  // Load saved data from localStorage on mount
  useEffect(() => {
    try {
      const savedWifi = localStorage.getItem(STORAGE_KEYS.wifi)
      const savedHousehold = localStorage.getItem(STORAGE_KEYS.household)
      const savedOwner = localStorage.getItem(STORAGE_KEYS.owner)
      const savedPrivacy = localStorage.getItem(STORAGE_KEYS.privacy)
      const savedModel = localStorage.getItem(STORAGE_KEYS.model)

      // Determine current step based on saved data
      let step = 1
      if (savedWifi && !savedWifi.includes('"skipped"')) {
        setWifiConfig(JSON.parse(savedWifi))
        step = 2
      }
      if (savedHousehold) {
        setHouseholdConfig(JSON.parse(savedHousehold))
        step = 3
      }
      if (savedOwner) {
        setOwnerConfig(JSON.parse(savedOwner))
        step = 4
      }
      if (savedPrivacy) {
        setPrivacyConfig(JSON.parse(savedPrivacy))
        step = 5
      }
      if (savedModel) {
        setModelConfig(JSON.parse(savedModel))
        step = 6
      }
      setCurrentStep(step)
    } catch (err) {
      console.error('Failed to load saved setup data:', err)
    }
  }, [])

  const steps = [
    { number: 1, name: 'WiFi', component: WiFiConfig },
    { number: 2, name: 'Household', component: HouseholdSetup },
    { number: 3, name: 'Owner', component: OwnerProfile },
    { number: 4, name: 'Privacy', component: PrivacySettings },
    { number: 5, name: 'Model', component: ModelPreset },
  ]

  const handleStepComplete = (stepNumber, data) => {
    if (stepNumber === 1) {
      // WiFi step
      setWifiConfig(data)
      try {
        localStorage.setItem(STORAGE_KEYS.wifi, JSON.stringify(data))
      } catch (err) {
        console.error('Failed to save WiFi config:', err)
      }
    } else if (stepNumber === 2) {
      // Household step
      setHouseholdConfig(data)
      try {
        localStorage.setItem(STORAGE_KEYS.household, JSON.stringify(data))
      } catch (err) {
        console.error('Failed to save household config:', err)
      }
    } else if (stepNumber === 3) {
      // Owner step
      setOwnerConfig(data)
      try {
        localStorage.setItem(STORAGE_KEYS.owner, JSON.stringify(data))
      } catch (err) {
        console.error('Failed to save owner config:', err)
      }
    } else if (stepNumber === 4) {
      // Privacy step
      setPrivacyConfig(data)
      try {
        localStorage.setItem(STORAGE_KEYS.privacy, JSON.stringify(data))
      } catch (err) {
        console.error('Failed to save privacy config:', err)
      }
    } else if (stepNumber === 5) {
      // Model preset step (final step)
      setModelConfig(data)
      try {
        localStorage.setItem(STORAGE_KEYS.model, JSON.stringify(data))
      } catch (err) {
        console.error('Failed to save model config:', err)
      }
      // Clear all localStorage after successful completion
      try {
        Object.values(STORAGE_KEYS).forEach((key) => {
          localStorage.removeItem(key)
        })
      } catch (err) {
        console.error('Failed to clear localStorage:', err)
      }
      if (onComplete) {
        onComplete()
      }
      return
    }

    // Move to next step
    if (currentStep < steps.length) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const CurrentStepComponent = steps[currentStep - 1].component

  return (
    <div className="setup-wizard">
      <div className="wizard-header">
        <h2>Neuroion Setup</h2>
        <div className="step-indicator">
          {steps.map((step, index) => (
            <div key={step.number} className="step-item">
              <div
                className={`step-circle ${currentStep > step.number ? 'completed' : ''} ${currentStep === step.number ? 'active' : ''}`}
              >
                {currentStep > step.number ? '✓' : step.number}
              </div>
              <span className="step-name">{step.name}</span>
              {index < steps.length - 1 && (
                <div
                  className={`step-line ${currentStep > step.number ? 'completed' : ''}`}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="wizard-content">
        <CurrentStepComponent
          onComplete={(data) => handleStepComplete(currentStep, data)}
          onBack={currentStep > 1 ? handleBack : null}
          initialData={
            currentStep === 1
              ? wifiConfig
              : currentStep === 2
                ? householdConfig
                : currentStep === 3
                  ? ownerConfig
                  : currentStep === 4
                    ? privacyConfig
                    : modelConfig
          }
        />
      </div>
    </div>
  )
}

export default SetupWizard
