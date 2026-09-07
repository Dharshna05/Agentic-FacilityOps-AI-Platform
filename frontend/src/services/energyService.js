import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

const api = axios.create({ baseURL: API_BASE_URL })

// Attach the stored JWT (if any) to every request this shared instance
// makes — read fresh from localStorage per-request rather than captured
// once at module-load time, since login/logout happen after this module
// is first imported. Only the /records POST/DELETE endpoints actually
// enforce this server-side (see backend/app/core/security.py), so most
// requests will 200 either way — this just makes sure the token is THERE
// when a protected one needs it, without importing AuthContext here (this
// file has no React context to hook into, and doesn't need one).
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('facilityops-token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// A 401 here means the token is missing/expired/invalid for a route that
// actually required it — clear it and bounce to /login rather than
// leaving the user looking at a silently-failed action.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !error.config?.url?.includes('/auth/')) {
      localStorage.removeItem('facilityops-token')
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export const energyService = {
  getDashboard: (buildingId = 'BLD-HQ-01', limit = null) =>
    api.get('/energy/dashboard', { params: { building_id: buildingId, ...(limit ? { limit } : {}) } }).then(r => r.data),

  getAnalytics: (buildingId = 'BLD-HQ-01') =>
    api.get('/energy/analytics', { params: { building_id: buildingId } }).then(r => r.data),

  getRecommendations: (buildingId = 'BLD-HQ-01') =>
    api.get('/energy/recommendations', { params: { building_id: buildingId } }).then(r => r.data),

  getReadings: (buildingId = 'BLD-HQ-01', limit = 200) =>
    api.get('/energy/readings', { params: { building_id: buildingId, limit } }).then(r => r.data),

  getForecast: (buildingId = 'BLD-HQ-01', horizon = '1h') =>
    api.get('/energy/forecast', { params: { building_id: buildingId, horizon } }).then(r => r.data),

  getForecastScatter: (horizon = '1h') =>
    api.get('/energy/forecast/scatter', { params: { horizon } }).then(r => r.data),

  getForecastModelComparison: (horizon = '1h') =>
    api.get('/energy/forecast/model-comparison', { params: { horizon } }).then(r => r.data),

  getBriefing: (buildingId = 'BLD-HQ-01') =>
    api.get('/energy/briefing', { params: { building_id: buildingId } }).then(r => r.data),

  getInvestigation: (buildingId = 'BLD-HQ-01') =>
    api.get('/energy/investigate', { params: { building_id: buildingId } }).then(r => r.data),

  ingest: () => api.post('/energy/ingest').then(r => r.data),

  uploadDataset: (file, replace = true) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/energy/ingest/upload', form, { params: { replace } }).then(r => r.data)
  },

  getRecentRecords: (limit = 20) =>
    api.get('/energy/records/recent', { params: { limit } }).then(r => r.data),

  addRecord: (payload) =>
    api.post('/energy/records', payload).then(r => r.data),

  deleteRecord: (id) =>
    api.delete(`/energy/records/${id}`).then(r => r.data),

  clearAllRecords: () =>
    api.delete('/energy/records').then(r => r.data),
}

export default api
