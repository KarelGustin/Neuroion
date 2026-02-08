import axios from 'axios'

/**
 * Automatically detect API base URL based on current hostname.
 * - If accessed via localhost, use localhost for API
 * - If accessed via IP address, use that IP for API
 * - Falls back to environment variable or localhost
 */
function getApiBaseUrl() {
  // Use environment variable if explicitly set
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }

  // Get current hostname and protocol
  const hostname = window.location.hostname
  const protocol = window.location.protocol
  const apiPort = import.meta.env.VITE_API_PORT || '8000'

  // If accessing via localhost or 127.0.0.1, use localhost for API
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return `http://localhost:${apiPort}`
  }

  // Otherwise, use the same hostname (IP address) for API
  // This works when accessing from mobile devices on the same network
  return `${protocol}//${hostname}:${apiPort}`
}

const API_BASE_URL = getApiBaseUrl()

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

export async function scanWiFiNetworks() {
  const response = await api.get('/setup/wifi/scan')
  return response.data.networks
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

export async function setupOwner(name, language, timezone, style_prefs = null, preferences = null) {
  const response = await api.post('/setup/owner', {
    name,
    language,
    timezone,
    style_prefs: style_prefs || null,
    preferences: preferences || null,
  })
  return response.data
}

/** Save initial context for the owner (for Neuroion Agent ion). Used in profile wizard step. */
export async function saveOwnerContext(summary) {
  const response = await api.post('/setup/owner-context', { summary: summary || '' })
  return response.data
}

export async function setupModelChoice(choice, options = {}) {
  const body = { choice, ...options }
  const response = await api.post('/setup/model', body)
  return response.data
}

export async function checkSetupComplete() {
  const response = await api.get('/setup/complete')
  return response.data
}

export async function markSetupComplete() {
  const response = await api.post('/setup/complete')
  return response.data
}

export async function setupDevice(deviceName, timezone) {
  const response = await api.post('/setup/device', {
    device_name: deviceName,
    timezone: timezone || 'Europe/Amsterdam',
  })
  return response.data
}

export async function validateSetup() {
  const response = await api.post('/setup/validate')
  return response.data
}

export async function applyWifi() {
  const response = await api.post('/setup/wifi/apply')
  return response.data
}

export async function checkInternetConnection() {
  const response = await api.get('/setup/internet/check')
  return response.data
}

// Dashboard API functions
export async function getDashboardStats() {
  const response = await api.get('/dashboard/stats')
  return response.data
}

export async function getHouseholdMembers() {
  const response = await api.get('/dashboard/members')
  return response.data.members
}

export async function generateLoginCode(userId) {
  const response = await api.post('/dashboard/login-code/generate', {
    user_id: userId,
  })
  return response.data
}

export async function verifyLoginCode(code) {
  const response = await api.post('/dashboard/login-code/verify', {
    code,
  })
  return response.data
}

export async function createDashboardJoinToken(expiresInMinutes = 10) {
  const response = await api.post('/dashboard/join-token', {
    expires_in_minutes: expiresInMinutes,
  })
  return response.data
}

export async function deleteMemberFromDashboard(memberId, confirmationCode) {
  const response = await api.post('/dashboard/member-delete', {
    member_id: memberId,
    confirmation_code: confirmationCode,
  })
  return response.data
}

export default api
