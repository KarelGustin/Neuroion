import React, { useState, useEffect } from 'react'
import Welcome from './Welcome'
import WiFiConfig from './WiFiConfig'
import DeviceTimezone from './DeviceTimezone'
import HouseholdSetup from './HouseholdSetup'
import OwnerProfile from './OwnerProfile'
import PrivacySettings from './PrivacySettings'
import ModelPreset from './ModelPreset'
import ValidateStep from './ValidateStep'
import FinishStep from './FinishStep'
import '../styles/SetupWizard.css'

const STORAGE_KEYS = {
  welcome: 'neuroion_setup_welcome',
  wifi: 'neuroion_setup_wifi',
  device: 'neuroion_setup_device',
  household: 'neuroion_setup_household',
  owner: 'neuroion_setup_owner',
  privacy: 'neuroion_setup_privacy',
  model: 'neuroion_setup_model',
}

const STEPS = [
  { number: 1, name: 'Welcome', component: Welcome },
  { number: 2, name: 'WiFi', component: WiFiConfig },
  { number: 3, name: 'Device', component: DeviceTimezone },
  { number: 4, name: 'Household', component: HouseholdSetup },
  { number: 5, name: 'Owner', component: OwnerProfile },
  { number: 6, name: 'Model', component: ModelPreset },
  { number: 7, name: 'Privacy', component: PrivacySettings },
  { number: 8, name: 'Validate', component: ValidateStep },
  { number: 9, name: 'Finish', component: FinishStep },
]

function SetupWizard({ onComplete }) {
  const [currentStep, setCurrentStep] = useState(1)
  const [welcomeConfig, setWelcomeConfig] = useState(null)
  const [wifiConfig, setWifiConfig] = useState(null)
  const [deviceConfig, setDeviceConfig] = useState(null)
  const [householdConfig, setHouseholdConfig] = useState(null)
  const [ownerConfig, setOwnerConfig] = useState(null)
  const [privacyConfig, setPrivacyConfig] = useState(null)
  const [modelConfig, setModelConfig] = useState(null)

  useEffect(() => {
    try {
      let step = 1
      const savedWelcome = localStorage.getItem(STORAGE_KEYS.welcome)
      if (savedWelcome) {
        setWelcomeConfig(JSON.parse(savedWelcome))
        step = 2
      }
      const savedWifi = localStorage.getItem(STORAGE_KEYS.wifi)
      if (savedWifi && !savedWifi.includes('"skipped"')) {
        setWifiConfig(JSON.parse(savedWifi))
        step = 3
      }
      const savedDevice = localStorage.getItem(STORAGE_KEYS.device)
      if (savedDevice) {
        setDeviceConfig(JSON.parse(savedDevice))
        step = 4
      }
      const savedHousehold = localStorage.getItem(STORAGE_KEYS.household)
      if (savedHousehold) {
        setHouseholdConfig(JSON.parse(savedHousehold))
        step = 5
      }
      const savedOwner = localStorage.getItem(STORAGE_KEYS.owner)
      if (savedOwner) {
        setOwnerConfig(JSON.parse(savedOwner))
        step = 6
      }
      const savedPrivacy = localStorage.getItem(STORAGE_KEYS.privacy)
      if (savedPrivacy) {
        setPrivacyConfig(JSON.parse(savedPrivacy))
        step = 7
      }
      const savedModel = localStorage.getItem(STORAGE_KEYS.model)
      if (savedModel) {
        setModelConfig(JSON.parse(savedModel))
        step = 8
      }
      setCurrentStep(step)
    } catch (err) {
      console.error('Failed to load saved setup data:', err)
    }
  }, [])

  const getInitialDataForStep = (stepNumber) => {
    switch (stepNumber) {
      case 1: return welcomeConfig
      case 2: return wifiConfig
      case 3: return deviceConfig
      case 4: return householdConfig
      case 5: return ownerConfig
      case 6: return modelConfig
      case 7: return privacyConfig
      default: return null
    }
  }

  const handleStepComplete = (stepNumber, data) => {
    if (stepNumber === 1) {
      setWelcomeConfig(data)
      try { localStorage.setItem(STORAGE_KEYS.welcome, JSON.stringify(data)) } catch (_) {}
    } else if (stepNumber === 2) {
      setWifiConfig(data)
      try { localStorage.setItem(STORAGE_KEYS.wifi, JSON.stringify(data)) } catch (_) {}
    } else if (stepNumber === 3) {
      setDeviceConfig(data)
      try { localStorage.setItem(STORAGE_KEYS.device, JSON.stringify(data)) } catch (_) {}
    } else if (stepNumber === 4) {
      setHouseholdConfig(data)
      try { localStorage.setItem(STORAGE_KEYS.household, JSON.stringify(data)) } catch (_) {}
    } else if (stepNumber === 5) {
      setOwnerConfig(data)
      try { localStorage.setItem(STORAGE_KEYS.owner, JSON.stringify(data)) } catch (_) {}
    } else if (stepNumber === 6) {
      setModelConfig(data)
      try { localStorage.setItem(STORAGE_KEYS.model, JSON.stringify(data)) } catch (_) {}
    } else if (stepNumber === 7) {
      setPrivacyConfig(data)
      try { localStorage.setItem(STORAGE_KEYS.privacy, JSON.stringify(data)) } catch (_) {}
    } else if (stepNumber === 8) {
      // Validate step - just advance
    } else if (stepNumber === 9) {
      try {
        Object.values(STORAGE_KEYS).forEach((key) => localStorage.removeItem(key))
      } catch (_) {}
      if (onComplete) onComplete()
      return
    }

    if (currentStep < STEPS.length) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handleBack = () => {
    if (currentStep > 1) setCurrentStep(currentStep - 1)
  }

  const CurrentStepComponent = STEPS[currentStep - 1]?.component

  return (
    <div className="setup-wizard">
      <div className="wizard-header">
        <h2>Neuroion Setup</h2>
        <div className="step-indicator">
          {STEPS.map((step, index) => (
            <div key={step.number} className="step-item">
              <div
                className={`step-circle ${currentStep > step.number ? 'completed' : ''} ${currentStep === step.number ? 'active' : ''}`}
              >
                {currentStep > step.number ? '✓' : step.number}
              </div>
              <span className="step-name">{step.name}</span>
              {index < STEPS.length - 1 && (
                <div className={`step-line ${currentStep > step.number ? 'completed' : ''}`} />
              )}
            </div>
          ))}
        </div>
      </div>
      <div className="wizard-content">
        {CurrentStepComponent && (
          <CurrentStepComponent
            onComplete={(data) => handleStepComplete(currentStep, data)}
            onBack={currentStep > 1 ? handleBack : null}
            initialData={getInitialDataForStep(currentStep)}
          />
        )}
      </div>
    </div>
  )
}

export default SetupWizard
