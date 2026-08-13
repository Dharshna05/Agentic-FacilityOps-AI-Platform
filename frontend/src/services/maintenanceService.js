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
}

export default maintenanceService
