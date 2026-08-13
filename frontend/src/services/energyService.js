import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

const api = axios.create({ baseURL: API_BASE_URL })

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

  getBriefing: (buildingId = 'BLD-HQ-01') =>
    api.get('/energy/briefing', { params: { building_id: buildingId } }).then(r => r.data),

  getInvestigation: (buildingId = 'BLD-HQ-01') =>
    api.get('/energy/investigate', { params: { building_id: buildingId } }).then(r => r.data),

  ingest: () => api.post('/energy/ingest').then(r => r.data),
}

export default api
