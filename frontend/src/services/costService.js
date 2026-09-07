import api from './energyService'

/** Formats a rupee amount using Indian lakh/crore convention — the amounts
 * in this dataset (real BBMP capital-works tenders can run into crores)
 * would be unreadable as "₹1680000k". */
export function formatINR(amount) {
  if (amount == null || Number.isNaN(amount)) return '₹0'
  const abs = Math.abs(amount)
  if (abs >= 1e7) return `₹${(amount / 1e7).toFixed(2)} Cr`
  if (abs >= 1e5) return `₹${(amount / 1e5).toFixed(2)} L`
  return `₹${amount.toLocaleString('en-IN')}`
}

export const costService = {
  getBuilding: (buildingId = 'BLD-HQ-01') =>
    api.get('/cost/building', { params: { building_id: buildingId } }).then(r => r.data),

  getVendors: (buildingId = 'BLD-HQ-01') =>
    api.get('/cost/vendors', { params: { building_id: buildingId } }).then(r => r.data),

  getBudgets: (buildingId = 'BLD-HQ-01') =>
    api.get('/cost/budgets', { params: { building_id: buildingId } }).then(r => r.data),

  getAlerts: (buildingId = 'BLD-HQ-01') =>
    api.get('/cost/alerts', { params: { building_id: buildingId } }).then(r => r.data),

  getInvestigation: (buildingId = 'BLD-HQ-01') =>
    api.get('/cost/investigate', { params: { building_id: buildingId } }).then(r => r.data),

  ingest: () => api.post('/cost/ingest').then(r => r.data),

  uploadDataset: (file, replace = true) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/cost/ingest/upload', form, { params: { replace } }).then(r => r.data)
  },

  getRecentRecords: (category = null, limit = 20) =>
    api.get('/cost/records/recent', { params: { category: category || undefined, limit } }).then(r => r.data),

  addRecord: (payload) =>
    api.post('/cost/records', payload).then(r => r.data),

  deleteRecord: (id) =>
    api.delete(`/cost/records/${id}`).then(r => r.data),

  clearAllRecords: (category = null) =>
    api.delete('/cost/records', { params: { category: category || undefined } }).then(r => r.data),
}

export const facilityService = {
  getHealth: (buildingId = 'BLD-HQ-01') =>
    api.get('/facility/health', { params: { building_id: buildingId } }).then(r => r.data),

  getAlerts: (buildingId = 'BLD-HQ-01') =>
    api.get('/facility/alerts', { params: { building_id: buildingId } }).then(r => r.data),

  getKpis: (buildingId = 'BLD-HQ-01') =>
    api.get('/facility/kpis', { params: { building_id: buildingId } }).then(r => r.data),

  getInvestigation: (buildingId = 'BLD-HQ-01') =>
    api.get('/facility/investigate', { params: { building_id: buildingId } }).then(r => r.data),

  search: (query, buildingId = 'BLD-HQ-01') =>
    api.get('/facility/search', { params: { q: query, building_id: buildingId } }).then(r => r.data),
}
