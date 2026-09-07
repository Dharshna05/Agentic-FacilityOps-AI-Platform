import { useEffect, useState, useCallback, useRef } from 'react'
import { maintenanceService } from '../../services/maintenanceService'
import FleetKpiRow from '../../components/maintenance/FleetKpiRow'
import FleetHealthRadar from '../../components/maintenance/FleetHealthRadar'
import AssetTable from '../../components/maintenance/AssetTable'
import AssetDetailPanel from '../../components/maintenance/AssetDetailPanel'
import CriticalAssetsSpotlight from '../../components/maintenance/CriticalAssetsSpotlight'
import MaintenanceAlertsList from '../../components/maintenance/MaintenanceAlertsList'
import WorkOrdersPanel from '../../components/maintenance/WorkOrdersPanel'
import SectionHeader from '../../components/maintenance/SectionHeader'
import AgentInvestigationPanel from '../../components/agent/AgentInvestigationPanel'
import ModelReliabilityChart from '../../components/charts/ModelReliabilityChart'
import DashboardHeader from '../../components/ui/DashboardHeader'
import Toast from '../../components/ui/Toast'
import DataManagerModal from '../../components/shared/DataManagerModal'
import DatasetUploadPanel from '../../components/shared/DatasetUploadPanel'
import { Wrench, Database, UploadCloud } from 'lucide-react'
import DashboardSkeleton from '../../components/ui/DashboardSkeleton'

const MAINTENANCE_FIELDS = [
  { key: 'asset_id', label: 'Asset ID', type: 'text', required: true, placeholder: 'AST-01' },
  { key: 'vibration_index', label: 'Vibration index', type: 'number', step: 0.01 },
  { key: 'pressure_kpa', label: 'Pressure (kPa)', type: 'number', step: 0.1 },
  { key: 'flow_rate', label: 'Flow rate', type: 'number', step: 0.1 },
  { key: 'efficiency_ratio', label: 'Efficiency ratio', type: 'number', step: 0.01 },
  { key: 'timestamp', label: 'Timestamp', type: 'datetime-local' },
]
const MAINTENANCE_COLUMNS = [
  { key: 'asset_id', label: 'asset' },
  { key: 'cycle', label: 'cycle' },
  { key: 'vibration_index', label: 'vib' },
]

// The fleet's underlying sensor data doesn't change second-to-second in this
// demo dataset, but the dashboard should still behave like a live monitoring
// screen rather than a one-time snapshot — so it quietly re-polls the API on
// an interval and reflects whatever the backend has right now (e.g. a new
// work order opened by another teammate's session, or by the agent).
const POLL_INTERVAL_MS = 30_000

export default function MaintenanceDashboardPage() {
  const [fleetData, setFleetData] = useState(null)
  const [modelScatter, setModelScatter] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [workOrders, setWorkOrders] = useState([])
  const [selectedAssetId, setSelectedAssetId] = useState(null)
  const [investigation, setInvestigation] = useState(null)
  const [investigating, setInvestigating] = useState(false)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)
  const [managerFor, setManagerFor] = useState(null)
  const [uploadOpen, setUploadOpen] = useState(false)
  const pollRef = useRef(null)

  const loadAll = useCallback(async () => {
    const [fleet, alertsData, workOrdersData, scatterData] = await Promise.all([
      maintenanceService.getFleet(),
      maintenanceService.getAlerts(),
      maintenanceService.getWorkOrders(),
      maintenanceService.getModelScatter().catch(() => null),
    ])
    setFleetData(fleet)
    setAlerts(alertsData.alerts)
    setWorkOrders(workOrdersData.work_orders)
    setModelScatter(scatterData)
    setLastUpdated(new Date())
  }, [])

  // Manual refresh — used by the button in LiveIndicator.
  const refreshNow = useCallback(async () => {
    setRefreshing(true)
    try {
      await loadAll()
    } catch (err) {
      setError(err.message)
      setToast({ message: `refresh failed: ${err.message}`, variant: 'warning' })
    } finally {
      setRefreshing(false)
    }
  }, [loadAll])

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        setLoading(true)
        await loadAll()
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [loadAll])

  // Silent background polling — no full-page spinner, just a brief
  // "syncing…" flash in the LiveIndicator while it happens.
  useEffect(() => {
    pollRef.current = setInterval(() => {
      setRefreshing(true)
      loadAll().catch(() => {}).finally(() => setRefreshing(false))
    }, POLL_INTERVAL_MS)
    return () => clearInterval(pollRef.current)
  }, [loadAll])

  const runInvestigation = useCallback(async () => {
    setInvestigating(true)
    setInvestigation(null)
    try {
      const result = await maintenanceService.getInvestigation()
      setInvestigation(result)
      // A real work order may have just been created by the investigation —
      // refresh so the Work Orders panel reflects it immediately.
      const wo = await maintenanceService.getWorkOrders()
      const createdOne = wo.work_orders.length > workOrders.length
      setWorkOrders(wo.work_orders)
      setLastUpdated(new Date())
      if (createdOne) {
        setToast({ message: 'agent opened a new work order from this investigation', variant: 'success' })
      }
    } catch (err) {
      setError(err.message)
      setToast({ message: `investigation failed: ${err.message}`, variant: 'warning' })
    } finally {
      setInvestigating(false)
    }
  }, [workOrders])

  // Escape key closes the detail drawer, same as clicking the backdrop.
  useEffect(() => {
    if (!selectedAssetId) return
    const onKey = (e) => { if (e.key === 'Escape') setSelectedAssetId(null) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selectedAssetId])

  if (loading) {
    return (
      <DashboardSkeleton message="SCANNING ASSET FLEET…" kpiCount={4} />
    )
  }

  if (error) {
    return (
      <div className="p-6 text-red-500 dark:text-red-400 text-sm font-mono">
        connection failed: {error} — confirm the FastAPI server is running on :8000
      </div>
    )
  }

  const { fleet, assets, risk_ranking } = fleetData
  const openWorkOrderCount = workOrders.filter(w => w.status === 'open').length
  const modelConfidence = fleetData.model_confidence

  return (
    <div className="dashboard-page">
      <DashboardHeader Icon={Wrench} agentLabel="MAINTENANCE AGENT" title="Predictive" emphasis="Maintenance" description="ML-driven equipment health monitoring" buildingId={fleetData.building_id} lastUpdated={lastUpdated} isRefreshing={refreshing} onRefresh={refreshNow} accent="teal" />

      <div className="dashboard-content">

        {/* ── Fleet overview: KPIs + spotlight + radar + searchable asset table ── */}
        <section className="flex flex-col gap-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <SectionHeader
              title="Fleet Overview"
              subtitle="Live status across every monitored asset — click any point, row, or card to inspect its ML prediction"
            />
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => setUploadOpen(true)}
                className="flex items-center gap-1.5 font-mono text-[10px] text-teal-600 dark:text-teal-400 border border-teal-500/30 dark:border-teal-400/30 bg-teal-500/5 dark:bg-teal-400/5 rounded-full px-3 py-1.5 hover:bg-teal-500/10 transition-colors"
              >
                <UploadCloud size={12} /> UPLOAD DATASET
              </button>
              <button
                onClick={() => setManagerFor({})}
                className="flex items-center gap-1.5 font-mono text-[10px] text-teal-600 dark:text-teal-400 border border-teal-500/30 dark:border-teal-400/30 bg-teal-500/5 dark:bg-teal-400/5 rounded-full px-3 py-1.5 hover:bg-teal-500/10 transition-colors"
              >
                <Database size={12} /> MANAGE DATASET
              </button>
            </div>
          </div>
          <FleetKpiRow fleet={fleet} workOrderCount={openWorkOrderCount} confidence={modelConfidence} />

          <CriticalAssetsSpotlight riskRanking={risk_ranking} onSelect={setSelectedAssetId} selectedAssetId={selectedAssetId} />

          <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-4 items-start">
            <FleetHealthRadar assets={assets} selectedAssetId={selectedAssetId} onSelect={setSelectedAssetId} />
            <AssetTable assets={assets} onSelect={setSelectedAssetId} selectedAssetId={selectedAssetId} />
          </div>
        </section>

        {/* ── Model performance ── */}
        <section className="flex flex-col gap-4">
          <SectionHeader
            title="Model Performance"
            subtitle="How trustworthy are these predictions? Evaluated on 100 held-out NASA test engines the model never trained on"
            badge={modelConfidence?.model_used?.replace(/_/g, ' ')}
          />
          <ModelReliabilityChart
            title="Health/RUL Model Reliability"
            subtitle="Actual vs. predicted remaining useful life, with 80% prediction interval per asset"
            data={modelScatter}
            unit="days"
          />
        </section>

        <AgentInvestigationPanel investigation={investigation} isLoading={investigating} onRun={runInvestigation} buildingId={fleetData.building_id} title="Ask the Maintenance Agent" prompt="It reads fleet health, tests the evidence around the riskiest assets, and can create a real work order when action is justified." traceTitle="Maintenance Agent Trace" hint="Watch the model-led investigation unfold and see when the agent escalates." buttonLabel="INVESTIGATE FLEET HEALTH" />

        {/* ── Alerts & work orders ── */}
        <section className="flex flex-col gap-4">
          <SectionHeader
            title="Alerts & Work Orders"
            subtitle="Rule-based and ML-driven alerts, plus every work order — including cross-agent handoffs from Energy. Click any card to inspect the asset."
          />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <MaintenanceAlertsList alerts={alerts} onSelect={setSelectedAssetId} />
            <WorkOrdersPanel workOrders={workOrders} onSelect={setSelectedAssetId} />
          </div>
        </section>
      </div>

      <AssetDetailPanel assetId={selectedAssetId} onClose={() => setSelectedAssetId(null)} />

      <DataManagerModal
        open={!!managerFor}
        onClose={() => setManagerFor(null)}
        title="Manage Maintenance Dataset"
        subtitle={managerFor?.asset_id ? `Filtered to ${managerFor.name}` : 'All assets'}
        fields={MAINTENANCE_FIELDS}
        columns={MAINTENANCE_COLUMNS}
        fetchRecords={limit => maintenanceService.getRecentRecords(managerFor?.asset_id || null, limit)}
        addRecord={payload => maintenanceService.addRecord(payload)}
        deleteRecord={id => maintenanceService.deleteRecord(id)}
        clearAllRecords={assetId => maintenanceService.clearAllRecords(assetId)}
        onChanged={refreshNow}
        lockedField={managerFor?.asset_id ? { key: 'asset_id', value: managerFor.asset_id, label: managerFor.name } : null}
      />

      <DatasetUploadPanel
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        title="Upload Maintenance Dataset"
        subtitle="CSV/Excel with asset_id, vibration_index, and other sensor readings"
        uploadFn={file => maintenanceService.uploadDataset(file)}
        onUploaded={refreshNow}
        accentClass="teal"
      />

      <Toast message={toast?.message} variant={toast?.variant} onDismiss={() => setToast(null)} />
    </div>
  )
}
