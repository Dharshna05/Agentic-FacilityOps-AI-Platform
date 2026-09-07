import api from './energyService'

export const securityService = {
  getBuilding: (buildingId = 'BLD-HQ-01') =>
    api.get('/security/building', { params: { building_id: buildingId } }).then(r => r.data),

  getAccessPoints: (buildingId = 'BLD-HQ-01') =>
    api.get('/security/access-points', { params: { building_id: buildingId } }).then(r => r.data),

  getEvents: (limit = 200) =>
    api.get('/security/events', { params: { limit } }).then(r => r.data),

  getAlerts: (buildingId = 'BLD-HQ-01', status = null) =>
    api.get('/security/alerts', { params: { building_id: buildingId, ...(status ? { status } : {}) } }).then(r => r.data),

  getInvestigation: (buildingId = 'BLD-HQ-01') =>
    api.get('/security/investigate', { params: { building_id: buildingId } }).then(r => r.data),

  ingest: () => api.post('/security/ingest').then(r => r.data),

  uploadDataset: (file, replace = true) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/security/ingest/upload', form, { params: { replace } }).then(r => r.data)
  },

  getRecentRecords: (accessPointId = null, limit = 20) =>
    api.get('/security/records/recent', { params: { access_point_id: accessPointId, limit } }).then(r => r.data),

  addRecord: (payload) =>
    api.post('/security/records', payload).then(r => r.data),

  deleteRecord: (id) =>
    api.delete(`/security/records/${id}`).then(r => r.data),

  clearAllRecords: (accessPointId = null) =>
    api.delete('/security/records', { params: { access_point_id: accessPointId } }).then(r => r.data),
}

export default securityService
