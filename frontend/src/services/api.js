import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
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
  streamUrl: (tripId) => `/api/agents/stream/${tripId}`,
}

export const healthApi = {
  check: () => api.get('/health'),
}

export default api
