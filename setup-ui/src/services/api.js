import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export async function checkHealth() {
  const response = await api.get('/health')
  return response.data
}

export async function getPairingCode(householdId, deviceId, deviceType, name) {
  const response = await api.post('/pair/start', {
    household_id: householdId,
    device_id: deviceId,
    device_type: deviceType,
    name: name,
  })
  return response.data.pairing_code
}

// Setup API functions
export async function getSetupStatus() {
  const response = await api.get('/setup/status')
  return response.data
}

export async function configureWiFi(ssid, password) {
  const response = await api.post('/setup/wifi', {
    ssid,
    password,
  })
  return response.data
}

export async function configureLLM(provider, config) {
  const response = await api.post('/setup/llm', {
    provider,
    config,
  })
  return response.data
}

export async function setupHousehold(householdName, ownerName) {
  const response = await api.post('/setup/household', {
    household_name: householdName,
    owner_name: ownerName,
  })
  return response.data
}

export async function checkSetupComplete() {
  const response = await api.get('/setup/complete')
  return response.data
}

export default api
