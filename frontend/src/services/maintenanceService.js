import api from './energyService'

export const maintenanceService = {
  getFleet: (buildingId = 'BLD-HQ-01') =>
    api.get('/maintenance/fleet', { params: { building_id: buildingId } }).then(r => r.data),

  getAssets: (buildingId = 'BLD-HQ-01') =>
    api.get('/maintenance/assets', { params: { building_id: buildingId } }).then(r => r.data),

  getAssetDetail: (assetId) =>
    api.get(`/maintenance/assets/${assetId}`).then(r => r.data),

  getAssetHistory: (assetId, limit = 200) =>
    api.get(`/maintenance/assets/${assetId}/history`, { params: { limit } }).then(r => r.data),

  getAlerts: (buildingId = 'BLD-HQ-01') =>
    api.get('/maintenance/alerts', { params: { building_id: buildingId } }).then(r => r.data),

  getWorkOrders: (buildingId = 'BLD-HQ-01', status = null) =>
    api.get('/maintenance/work-orders', { params: { building_id: buildingId, ...(status ? { status } : {}) } }).then(r => r.data),

  getInvestigation: (buildingId = 'BLD-HQ-01') =>
    api.get('/maintenance/investigate', { params: { building_id: buildingId } }).then(r => r.data),

  getModelScatter: () =>
    api.get('/maintenance/model/scatter').then(r => r.data),

  ingest: () => api.post('/maintenance/ingest').then(r => r.data),

  uploadDataset: (file, replace = true) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/maintenance/ingest/upload', form, { params: { replace } }).then(r => r.data)
  },

  getRecentRecords: (assetId = null, limit = 20) =>
    api.get('/maintenance/records/recent', { params: { asset_id: assetId, limit } }).then(r => r.data),

  addRecord: (payload) =>
    api.post('/maintenance/records', payload).then(r => r.data),

  deleteRecord: (id) =>
    api.delete(`/maintenance/records/${id}`).then(r => r.data),

  clearAllRecords: (assetId = null) =>
    api.delete('/maintenance/records', { params: { asset_id: assetId } }).then(r => r.data),
}

export default maintenanceService
