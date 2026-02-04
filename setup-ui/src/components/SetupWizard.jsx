import React, { useState } from 'react'
import WiFiConfig from './WiFiConfig'
import LLMConfig from './LLMConfig'
import HouseholdSetup from './HouseholdSetup'
import '../styles/SetupWizard.css'

function SetupWizard({ onComplete }) {
  const [currentStep, setCurrentStep] = useState(1)
  const [wifiConfig, setWifiConfig] = useState(null)
  const [llmConfig, setLlmConfig] = useState(null)
  const [householdConfig, setHouseholdConfig] = useState(null)

  const steps = [
    { number: 1, name: 'WiFi', component: WiFiConfig },
    { number: 2, name: 'LLM', component: LLMConfig },
    { number: 3, name: 'Household', component: HouseholdSetup },
  ]

  const handleStepComplete = (stepNumber, data) => {
    if (stepNumber === 1) {
      setWifiConfig(data)
    } else if (stepNumber === 2) {
      setLlmConfig(data)
    } else if (stepNumber === 3) {
      setHouseholdConfig(data)
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
                ? llmConfig
                : householdConfig
          }
        />
      </div>
    </div>
  )
}

export default SetupWizard
