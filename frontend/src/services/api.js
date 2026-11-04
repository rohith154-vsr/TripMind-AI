import axios from 'axios'

/**
 * Resolves the backend API base URL:
 * - In local development: defaults to '/api' (proxied via Vite dev server)
 * - In production (Vercel): uses import.meta.env.VITE_API_BASE_URL (e.g. Render backend URL)
 * Automatically normalizes trailing slashes and ensures '/api' suffix.
 */
export const getApiBaseUrl = () => {
  const envUrl = (import.meta.env.VITE_API_BASE_URL || '').trim()
  if (!envUrl) {
    return '/api'
  }
  const cleanUrl = envUrl.replace(/\/+$/, '')
  return cleanUrl.endsWith('/api') ? cleanUrl : `${cleanUrl}/api`
}

const api = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
)

// Response interceptor
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'An error occurred'
    return Promise.reject(new Error(message))
  }
)

export const tripApi = {
  generate: (preferences) => api.post('/trips/generate', { preferences }),
  list: () => api.get('/trips'),
  get: (tripId) => api.get(`/trips/${tripId}`),
  delete: (tripId) => api.delete(`/trips/${tripId}`),
}

export const agentApi = {
  getStatus: (tripId) => api.get(`/agents/status/${tripId}`),
  streamUrl: (tripId) => `${getApiBaseUrl()}/agents/stream/${tripId}`,
}

export const healthApi = {
  check: () => api.get('/health'),
}

export default api
