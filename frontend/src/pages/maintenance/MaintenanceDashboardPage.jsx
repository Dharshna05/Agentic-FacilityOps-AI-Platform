import { useEffect, useState, useCallback, useRef } from 'react'
import { maintenanceService } from '../../services/maintenanceService'
import FleetKpiRow from '../../components/maintenance/FleetKpiRow'
import FleetHealthRadar from '../../components/maintenance/FleetHealthRadar'
import AssetTable from '../../components/maintenance/AssetTable'
import MaintenanceAlertsList from '../../components/maintenance/MaintenanceAlertsList'
import WorkOrdersPanel from '../../components/maintenance/WorkOrdersPanel'
import AgentTraceViewer from '../../components/agent/AgentTraceViewer'
import ModelReliabilityChart from '../../components/charts/ModelReliabilityChart'
import LiveIndicator from '../../components/ui/LiveIndicator'

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
      setWorkOrders(wo.work_orders)
      setLastUpdated(new Date())
    } catch (err) {
      setError(err.message)
    } finally {
      setInvestigating(false)
    }
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <span className="font-mono text-xs text-slate-500 tracking-widest animate-pulse-line">
          SCANNING ASSET FLEET…
        </span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6 text-red-500 dark:text-red-400 text-sm font-mono">
        connection failed: {error} — confirm the FastAPI server is running on :8000
      </div>
    )
  }

  const { fleet, assets } = fleetData
  const openWorkOrderCount = workOrders.filter(w => w.status === 'open').length

  return (
    <div className="min-h-screen animate-fade-in">
      <div className="border-b border-slate-200 dark:border-slate-800/80 px-6 md:px-10 py-6 flex items-end justify-between flex-wrap gap-4">
        <div>
          <div className="mb-2">
            <LiveIndicator lastUpdated={lastUpdated} isRefreshing={refreshing} onRefresh={refreshNow} />
          </div>
          <h1 className="font-display text-3xl md:text-4xl font-semibold text-ink dark:text-slate-100 tracking-tight">
            Predictive Maintenance
          </h1>
          <p className="font-mono text-xs text-slate-500 mt-2">
            {fleetData.building_id} <span className="text-slate-300 dark:text-slate-700">·</span> ML-driven equipment health monitoring
          </p>
        </div>
      </div>

      <div className="p-6 md:p-10 flex flex-col gap-6 max-w-[1400px]">
        <FleetKpiRow fleet={fleet} workOrderCount={openWorkOrderCount} />

        <div className="grid grid-cols-1 lg:grid-cols-[460px_1fr] gap-4 items-start">
          <FleetHealthRadar assets={assets} />
          <AssetTable assets={assets} onSelect={setSelectedAssetId} selectedAssetId={selectedAssetId} />
        </div>

        <ModelReliabilityChart
          title="Health/RUL Model Reliability"
          subtitle="Actual vs. predicted remaining useful life on 100 held-out NASA test engines"
          data={modelScatter}
          unit="days"
        />

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-4 items-start">
          <div className="bg-paper-raised dark:bg-panel border border-slate-200 dark:border-slate-800 rounded-xl p-5 flex flex-col gap-3">
            <h3 className="font-display text-sm font-medium text-ink dark:text-slate-200">Run Deep Investigation</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Give the agent a goal — check fleet health, decide for itself whether any asset's
              evidence is clear enough to open a real work order.
            </p>
            <button
              onClick={runInvestigation}
              disabled={investigating}
              className="mt-1 font-mono text-xs tracking-wide px-4 py-2.5 rounded-lg border border-teal-500/50 dark:border-teal-400/40
                         text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-400/5 hover:bg-teal-100 dark:hover:bg-teal-400/10
                         hover:border-teal-600 dark:hover:border-teal-400/70
                         disabled:opacity-40 disabled:cursor-not-allowed transition-colors self-start"
            >
              {investigating ? 'agent working…' : '▶ investigate fleet health'}
            </button>
          </div>

          <AgentTraceViewer
            investigation={investigation}
            isLoading={investigating}
            title="Maintenance Agent Trace"
            hint="The agent decides itself whether the fleet summary warrants drilling into specific assets."
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <MaintenanceAlertsList alerts={alerts} />
          <WorkOrdersPanel workOrders={workOrders} />
        </div>
      </div>
    </div>
  )
}
