import React, { useState, useEffect } from 'react'
import DeviceHouseholdStep from './DeviceHouseholdStep'
import ModelPreset from './ModelPreset'
import NeuroionGatewayStep from './NeuroionGatewayStep'
import NeuroionWorkspaceStep from './NeuroionWorkspaceStep'
import NeuroionTelegramStep from './NeuroionTelegramStep'
import WiFiConfig from './WiFiConfig'
import ValidateStep from './ValidateStep'
import FinishStep from './FinishStep'
import '../styles/SetupWizard.css'

const STORAGE_KEYS = {
  core: 'neuroion_setup_core',
  model: 'neuroion_setup_model',
  gateway: 'neuroion_setup_neuroion_gateway',
  workspace: 'neuroion_setup_neuroion_workspace',
  channels: 'neuroion_setup_neuroion_channels',
  wifi: 'neuroion_setup_wifi',
}

const STEPS = [
  { number: 1, name: 'Device & Household', component: DeviceHouseholdStep },
  { number: 2, name: 'Auth & Model', component: ModelPreset },
  { number: 3, name: 'Gateway', component: NeuroionGatewayStep },
  { number: 4, name: 'Workspace', component: NeuroionWorkspaceStep },
  { number: 5, name: 'Telegram', component: NeuroionTelegramStep },
  { number: 6, name: 'Network', component: WiFiConfig },
  { number: 7, name: 'Activate', component: ValidateStep },
  { number: 8, name: 'Finish', component: FinishStep },
]

function SetupWizard({ onComplete }) {
  const [currentStep, setCurrentStep] = useState(1)
  const [coreConfig, setCoreConfig] = useState(null)
  const [wifiConfig, setWifiConfig] = useState(null)
  const [modelConfig, setModelConfig] = useState(null)
  const [gatewayConfig, setGatewayConfig] = useState(null)
  const [workspaceConfig, setWorkspaceConfig] = useState(null)
  const [channelsConfig, setChannelsConfig] = useState(null)

  useEffect(() => {
    try {
      let step = 1
      const savedCore = localStorage.getItem(STORAGE_KEYS.core)
      if (savedCore) {
        setCoreConfig(JSON.parse(savedCore))
        step = 2
      }
      const savedModel = localStorage.getItem(STORAGE_KEYS.model)
      if (savedModel) {
        setModelConfig(JSON.parse(savedModel))
        step = 3
      }
      const savedGateway = localStorage.getItem(STORAGE_KEYS.gateway)
      if (savedGateway) {
        setGatewayConfig(JSON.parse(savedGateway))
        step = 4
      }
      const savedWorkspace = localStorage.getItem(STORAGE_KEYS.workspace)
      if (savedWorkspace) {
        setWorkspaceConfig(JSON.parse(savedWorkspace))
        step = 5
      }
      const savedChannels = localStorage.getItem(STORAGE_KEYS.channels)
      if (savedChannels) {
        setChannelsConfig(JSON.parse(savedChannels))
        step = 6
      }
      const savedWifi = localStorage.getItem(STORAGE_KEYS.wifi)
      if (savedWifi) {
        setWifiConfig(JSON.parse(savedWifi))
        step = 7
      }
      setCurrentStep(step)
    } catch (err) {
      console.error('Failed to load saved setup data:', err)
    }
  }, [])

  const getInitialDataForStep = (stepNumber) => {
    const base = {
      1: coreConfig,
      2: modelConfig,
      3: gatewayConfig,
      4: workspaceConfig,
      5: { ...channelsConfig, ownerName: coreConfig?.ownerName, householdId: coreConfig?.householdId },
      6: wifiConfig,
    }
    return base[stepNumber] ?? null
  }

  const handleStepComplete = (stepNumber, data) => {
    if (stepNumber === 1) {
      setCoreConfig(data)
      try { localStorage.setItem(STORAGE_KEYS.core, JSON.stringify(data)) } catch (_) {}
    } else if (stepNumber === 2) {
      setModelConfig(data)
      try { localStorage.setItem(STORAGE_KEYS.model, JSON.stringify(data)) } catch (_) {}
    } else if (stepNumber === 3) {
      setGatewayConfig(data)
      try { localStorage.setItem(STORAGE_KEYS.gateway, JSON.stringify(data)) } catch (_) {}
    } else if (stepNumber === 4) {
      setWorkspaceConfig(data)
      try { localStorage.setItem(STORAGE_KEYS.workspace, JSON.stringify(data)) } catch (_) {}
    } else if (stepNumber === 5) {
      setChannelsConfig(data)
      try { localStorage.setItem(STORAGE_KEYS.channels, JSON.stringify(data)) } catch (_) {}
    } else if (stepNumber === 6) {
      setWifiConfig(data)
      try { localStorage.setItem(STORAGE_KEYS.wifi, JSON.stringify(data)) } catch (_) {}
    } else if (stepNumber === 7) {
      // Validate step - just advance
    } else if (stepNumber === 8) {
      try {
        Object.keys(localStorage).forEach((key) => {
          if (key.startsWith('neuroion_setup_')) {
            localStorage.removeItem(key)
          }
        })
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
        <h2>Neuroion Onboarding</h2>
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
