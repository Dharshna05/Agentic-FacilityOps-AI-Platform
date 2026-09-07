import api from './energyService'

export const occupancyService = {
  getBuilding: (buildingId = 'BLD-HQ-01') =>
    api.get('/occupancy/building', { params: { building_id: buildingId } }).then(r => r.data),

  getZones: (buildingId = 'BLD-HQ-01') =>
    api.get('/occupancy/zones', { params: { building_id: buildingId } }).then(r => r.data),

  getZoneDetail: (zoneId) =>
    api.get(`/occupancy/zones/${zoneId}`).then(r => r.data),

  getZoneHistory: (zoneId, limit = 300) =>
    api.get(`/occupancy/zones/${zoneId}/history`, { params: { limit } }).then(r => r.data),

  getAlerts: (buildingId = 'BLD-HQ-01') =>
    api.get('/occupancy/alerts', { params: { building_id: buildingId } }).then(r => r.data),

  getInvestigation: (buildingId = 'BLD-HQ-01') =>
    api.get('/occupancy/investigate', { params: { building_id: buildingId } }).then(r => r.data),

  getCnnLiveInference: () =>
    api.get('/occupancy/cnn/live-inference').then(r => r.data),

  getCnnSummary: () =>
    api.get('/occupancy/cnn/summary').then(r => r.data),
  ingest: () => api.post('/occupancy/ingest').then(r => r.data),

  uploadDataset: (file, replace = true) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/occupancy/ingest/upload', form, { params: { replace } }).then(r => r.data)
  },

  getRecentRecords: (zoneId = null, limit = 20) =>
    api.get('/occupancy/records/recent', { params: { zone_id: zoneId, limit } }).then(r => r.data),

  addRecord: (payload) =>
    api.post('/occupancy/records', payload).then(r => r.data),

  deleteRecord: (id) =>
    api.delete(`/occupancy/records/${id}`).then(r => r.data),

  clearAllRecords: (zoneId = null) =>
    api.delete('/occupancy/records', { params: { zone_id: zoneId } }).then(r => r.data),
}

export default occupancyService
