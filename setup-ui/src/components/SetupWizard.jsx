import React, { useState, useEffect } from 'react'
import WiFiConfig from './WiFiConfig'
import LLMConfig from './LLMConfig'
import HouseholdSetup from './HouseholdSetup'
import '../styles/SetupWizard.css'

const STORAGE_KEYS = {
  wifi: 'neuroion_setup_wifi',
  llm: 'neuroion_setup_llm',
  household: 'neuroion_setup_household',
}

function SetupWizard({ onComplete }) {
  const [currentStep, setCurrentStep] = useState(1)
  const [wifiConfig, setWifiConfig] = useState(null)
  const [llmConfig, setLlmConfig] = useState(null)
  const [householdConfig, setHouseholdConfig] = useState(null)

  // Load saved data from localStorage on mount
  useEffect(() => {
    try {
      const savedWifi = localStorage.getItem(STORAGE_KEYS.wifi)
      const savedLlm = localStorage.getItem(STORAGE_KEYS.llm)
      const savedHousehold = localStorage.getItem(STORAGE_KEYS.household)

      if (savedWifi) {
        const wifiData = JSON.parse(savedWifi)
        setWifiConfig(wifiData)
        // If WiFi is saved, move to step 2
        if (!savedLlm) {
          setCurrentStep(2)
        }
      }

      if (savedLlm) {
        const llmData = JSON.parse(savedLlm)
        setLlmConfig(llmData)
        // If LLM is saved, move to step 3
        if (!savedHousehold) {
          setCurrentStep(3)
        }
      }

      if (savedHousehold) {
        const householdData = JSON.parse(savedHousehold)
        setHouseholdConfig(householdData)
      }
    } catch (err) {
      console.error('Failed to load saved setup data:', err)
    }
  }, [])

  const steps = [
    { number: 1, name: 'WiFi', component: WiFiConfig },
    { number: 2, name: 'LLM', component: LLMConfig },
    { number: 3, name: 'Household', component: HouseholdSetup },
  ]

  const handleStepComplete = (stepNumber, data) => {
    if (stepNumber === 1) {
      setWifiConfig(data)
      // Save to localStorage
      try {
        localStorage.setItem(STORAGE_KEYS.wifi, JSON.stringify(data))
      } catch (err) {
        console.error('Failed to save WiFi config:', err)
      }
    } else if (stepNumber === 2) {
      setLlmConfig(data)
      // Save to localStorage
      try {
        localStorage.setItem(STORAGE_KEYS.llm, JSON.stringify(data))
      } catch (err) {
        console.error('Failed to save LLM config:', err)
      }
    } else if (stepNumber === 3) {
      setHouseholdConfig(data)
      // Save to localStorage
      try {
        localStorage.setItem(STORAGE_KEYS.household, JSON.stringify(data))
      } catch (err) {
        console.error('Failed to save household config:', err)
      }
      // Clear all localStorage after successful completion
      try {
        localStorage.removeItem(STORAGE_KEYS.wifi)
        localStorage.removeItem(STORAGE_KEYS.llm)
        localStorage.removeItem(STORAGE_KEYS.household)
      } catch (err) {
        console.error('Failed to clear localStorage:', err)
      }
      if (onComplete) {
        onComplete()
      }
      return
    }

    // Move to next step (works for both WiFi configured and skipped)
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
                ? llmConfig
                : householdConfig
          }
        />
      </div>
    </div>
  )
}

export default SetupWizard
