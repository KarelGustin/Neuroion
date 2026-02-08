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

// Add token to requests if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('dashboard_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export async function getDashboardLink(userId) {
  const response = await api.get(`/dashboard/user/${userId}/link`)
  return response.data
}

export async function getIntegrations(userId) {
  const response = await api.get(`/integrations/user/${userId}`)
  return response.data
}

export async function connectIntegration(userId, integrationType, code, redirectUri) {
  const response = await api.post(`/integrations/connect`, {
    user_id: userId,
    integration_type: integrationType,
    code,
    redirect_uri: redirectUri,
  })
  return response.data
}

export async function disconnectIntegration(userId, integrationType) {
  const response = await api.delete(`/integrations/user/${userId}/${integrationType}`)
  return response.data
}

export async function getOAuthUrl(integrationType, redirectUri, state) {
  const response = await api.get(`/integrations/oauth/authorize`, {
    params: {
      integration_type: integrationType,
      redirect_uri: redirectUri,
      state,
    },
  })
  return response.data
}

export async function verifyLoginCode(code) {
  const response = await api.post('/dashboard/login-code/verify', {
    code,
  })
  return response.data
}

export async function getUserPreferences(userId) {
  const response = await api.get(`/preferences/user/${userId}`)
  return response.data
}

export async function setUserPreference(userId, key, value, category = null) {
  const response = await api.post(`/preferences/user/${userId}`, {
    key,
    value,
    category,
  })
  return response.data
}

export async function deleteUserPreference(userId, key) {
  const response = await api.delete(`/preferences/user/${userId}/${key}`)
  return response.data
}

export async function getHouseholdPreferences() {
  const response = await api.get('/preferences/household')
  return response.data
}

export async function getContextList(limit = 50) {
  const response = await api.get('/context', { params: { limit } })
  return response.data
}

export async function deleteContext(snapshotId) {
  const response = await api.delete(`/context/${snapshotId}`)
  return response.data
}

export async function addContext(summary) {
  const response = await api.post('/context', { summary })
  return response.data
}

export default api
