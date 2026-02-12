import axios from 'axios'

/**
 * Automatically detect API base URL based on current hostname.
 * Set VITE_API_PORT in .env to match API_PORT when using a custom port (default: 8000).
 */
function getApiBaseUrl() {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }

  const hostname = window.location.hostname
  const protocol = window.location.protocol
  const apiPort = import.meta.env.VITE_API_PORT || '8000'

  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return `http://localhost:${apiPort}`
  }

  return `${protocol}//${hostname}:${apiPort}`
}

const API_BASE_URL = getApiBaseUrl()

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
})

export async function getStatus() {
  const response = await api.get('/api/status')
  return response.data
}

export async function getSetupStatus() {
  const response = await api.get('/setup/status')
  return response.data
}

export async function getDevStatus() {
  const response = await api.get('/setup/dev-status')
  return response.data
}

/** Create join token (requires owner auth). Prefer createDashboardJoinToken for kiosk. */
export async function createJoinToken() {
  const response = await api.post('/api/join-token/create', {
    expires_in_minutes: 10,
  })
  return response.data
}

/** Create join token from kiosk (no auth). Returns join_url for add-member QR. */
export async function createDashboardJoinToken() {
  const response = await api.post('/dashboard/join-token', {
    expires_in_minutes: 10,
  })
  return response.data
}

/** Verify join token (for add-member flow). */
export async function verifyJoinToken(token) {
  const response = await api.get('/api/join-token/verify', { params: { token } })
  return response.data
}

/** Consume join token and create member. */
export async function consumeJoinToken(token, memberData) {
  const response = await api.post('/api/join-token/consume', {
    token,
    member: memberData,
  })
  return response.data
}

/** Get pairing code for Telegram (after join). Pass memberId to link Telegram to the newly created member. */
export async function getPairingCode(householdId, deviceId, deviceType, name, memberId = null) {
  const body = {
    household_id: householdId,
    device_id: deviceId,
    device_type: deviceType,
    name: name,
  }
  if (memberId != null) body.member_id = memberId
  const response = await api.post('/pair/start', body)
  return response.data.pairing_code
}

/**
 * Factory reset. Caller should clear localStorage and reload after success.
 * Uses a longer timeout (60s) because wiping the DB can take a while.
 */
export async function factoryReset() {
  const response = await api.post('/setup/factory-reset', null, { timeout: 60000 })
  return response.data
}

// Setup wizard API (4 steps)
export async function setupHousehold(householdName, ownerName) {
  const response = await api.post('/setup/household', {
    household_name: householdName,
    owner_name: ownerName,
  })
  return response.data
}

export async function setupDevice(deviceName, timezone = 'Europe/Amsterdam') {
  const response = await api.post('/setup/device', {
    device_name: deviceName,
    timezone,
  })
  return response.data
}

export async function setupAgentName(name) {
  const response = await api.post('/setup/agent-name', { name: name || 'ion' })
  return response.data
}

export async function scanWifiNetworks() {
  const response = await api.get('/setup/wifi/scan')
  return response.data?.networks ?? []
}

export async function configureWifi(ssid, password) {
  const response = await api.post('/setup/wifi', { ssid, password })
  return response.data
}

export async function applyWifi() {
  const response = await api.post('/setup/wifi/apply')
  return response.data
}

export async function markSetupComplete() {
  const response = await api.post('/setup/complete')
  return response.data
}

/** Get household members (for dashboard). */
export async function getDashboardMembers() {
  const response = await api.get('/dashboard/members')
  return response.data?.members ?? []
}

/** Add member and get Telegram pairing QR (member_id, pairing_code, qr_value). */
export async function addMember(name) {
  const response = await api.post('/dashboard/add-member', { name: (name || '').trim() })
  return response.data
}

export default api
