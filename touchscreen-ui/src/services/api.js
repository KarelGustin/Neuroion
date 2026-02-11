import axios from 'axios'

/**
 * Automatically detect API base URL based on current hostname.
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
 * Factory reset. After success, clear setup-related localStorage and reload.
 */
export async function factoryReset() {
  const response = await api.post('/setup/factory-reset')
  const keys = Object.keys(localStorage).filter((k) =>
    /^neuroion_setup_/i.test(k)
  )
  keys.forEach((k) => localStorage.removeItem(k))
  window.location.reload()
  return response.data
}

export default api
