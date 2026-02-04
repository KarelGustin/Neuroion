import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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

export default api
