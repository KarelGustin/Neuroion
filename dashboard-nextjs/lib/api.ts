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

let authToken: string | null = null

export function setAuthToken(token: string | null) {
  authToken = token
}

export function getAuthToken(): string | null {
  return authToken
}

api.interceptors.request.use((config) => {
  let token = authToken
  if (!token && typeof window !== 'undefined') {
    token = localStorage.getItem('neuroion_token')
    if (token) authToken = token
  }
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
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

// Personal page (passcode unlock)
export async function getByPage(pageName: string) {
  const response = await api.get(`/dashboard/by-page/${encodeURIComponent(pageName)}`)
  return response.data
}

export async function unlockWithPasscode(pageName: string, passcode: string) {
  const response = await api.post('/dashboard/unlock', {
    page_name: pageName,
    passcode,
  })
  return response.data
}

export async function setPasscode(setupToken: string, passcode: string) {
  const response = await api.post('/dashboard/set-passcode', {
    setup_token: setupToken,
    passcode,
  })
  return response.data
}

// Chat (requires auth)
export async function sendChatMessage(message: string, conversationHistory?: { role: string; content: string }[]) {
  const response = await api.post('/chat', {
    message,
    conversation_history: conversationHistory,
  })
  return response.data
}

// User stats for personal dashboard (requires auth)
export async function getUserStats() {
  const response = await api.get('/dashboard/user/stats')
  return response.data
}

export default api
