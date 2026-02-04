import axios from 'axios'

/**
 * Get API base URL based on current hostname.
 */
function getApiBaseUrl(): string {
  if (typeof window === 'undefined') {
    return 'http://localhost:8000'
  }

  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL
  }

  const hostname = window.location.hostname
  const protocol = window.location.protocol
  const apiPort = process.env.NEXT_PUBLIC_API_PORT || '8000'

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

// Status API
export async function getStatus() {
  const response = await api.get('/api/status')
  return response.data
}

// Members API
export async function getMembers() {
  const response = await api.get('/api/members')
  return response.data.members
}

export async function createMember(data: any) {
  const response = await api.post('/api/members', data)
  return response.data
}

// Join Token API
export async function createJoinToken(expiresInMinutes: number = 10) {
  const response = await api.post('/api/join-token/create', {
    expires_in_minutes: expiresInMinutes,
  })
  return response.data
}

export async function verifyJoinToken(token: string) {
  const response = await api.get('/api/join-token/verify', {
    params: { token },
  })
  return response.data
}

export async function consumeJoinToken(token: string, memberData: any) {
  const response = await api.post('/api/join-token/consume', {
    token,
    member: memberData,
  })
  return response.data
}

// Setup API
export async function getSetupStatus() {
  const response = await api.get('/setup/status')
  return response.data
}

export async function getDeviceConfig() {
  const response = await api.get('/setup/device-config')
  return response.data
}

export default api
