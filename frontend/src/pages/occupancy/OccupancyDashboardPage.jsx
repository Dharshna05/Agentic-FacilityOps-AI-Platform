import { useEffect, useState, useCallback } from 'react'
import { UsersRound, Database, UploadCloud } from 'lucide-react'
import { occupancyService } from '../../services/occupancyService'
import OccupancyKpiRow from '../../components/occupancy/OccupancyKpiRow'
import ZoneHeatmap from '../../components/occupancy/ZoneHeatmap'
import ZoneTable from '../../components/occupancy/ZoneTable'
import OccupancyAlertsList from '../../components/occupancy/OccupancyAlertsList'
import ZoneDetailPanel from '../../components/occupancy/ZoneDetailPanel'
import CnnModelPanel from '../../components/occupancy/CnnModelPanel'
import AiInsightsPanel from '../../components/occupancy/AiInsightsPanel'
import SectionHeader from '../../components/maintenance/SectionHeader'
import AgentInvestigationPanel from '../../components/agent/AgentInvestigationPanel'
import DashboardHeader from '../../components/ui/DashboardHeader'
import HeroStatCard from '../../components/cards/HeroStatCard'
import DataManagerModal from '../../components/shared/DataManagerModal'
import DatasetUploadPanel from '../../components/shared/DatasetUploadPanel'
import DashboardSkeleton from '../../components/ui/DashboardSkeleton'

const OCCUPANCY_FIELDS = [
  { key: 'zone_id', label: 'Zone ID', type: 'text', required: true, placeholder: 'ZN-01' },
  { key: 'headcount', label: 'Headcount', type: 'number', required: true, step: 1 },
  { key: 'utilization_pct', label: 'Utilization % (optional)', type: 'number', step: 0.1 },
  { key: 'timestamp', label: 'Timestamp', type: 'datetime-local' },
]
const OCCUPANCY_COLUMNS = [
  { key: 'zone_id', label: 'zone' },
  { key: 'headcount', label: 'headcount' },
  { key: 'utilization_pct', label: 'util%' },
]

export default function OccupancyDashboardPage() {
  const [data, setData] = useState(null)
  const [selectedZoneId, setSelectedZoneId] = useState(null)
  const [investigation, setInvestigation] = useState(null)
  const [investigating, setInvestigating] = useState(false)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [error, setError] = useState(null)
  const [managerFor, setManagerFor] = useState(null)
  const [uploadOpen, setUploadOpen] = useState(false)

  const load = useCallback(async () => {
    const result = await occupancyService.getBuilding()
    setData(result)
    setLastUpdated(new Date())
  }, [])

  const refreshNow = useCallback(async () => {
    setRefreshing(true)
    try { await load() } catch (err) { setError(err.message) } finally { setRefreshing(false) }
  }, [load])

  useEffect(() => {
    let cancelled = false
    async function init() {
      try {
        setLoading(true)
        await load()
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    init()
    return () => { cancelled = true }
  }, [load])

  const runInvestigation = useCallback(async () => {
    setInvestigating(true)
    setInvestigation(null)
    try {
      const result = await occupancyService.getInvestigation()
      setInvestigation(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setInvestigating(false)
    }
  }, [])

  if (loading) {
    return (
      <DashboardSkeleton message="SCANNING BUILDING ZONES…" kpiCount={4} />
    )
  }

  if (error) {
    return <div className="p-6 text-red-500 dark:text-red-400 text-sm font-mono">connection failed: {error}</div>
  }

  return (
    <div className="dashboard-page">
      <div className="pointer-events-none absolute -top-32 -left-20 w-[420px] h-[420px] rounded-full bg-violet-500/10 dark:bg-violet-500/[0.08] blur-[110px]" />
      <div className="pointer-events-none absolute top-40 -right-32 w-[380px] h-[380px] rounded-full bg-teal-400/10 dark:bg-teal-400/[0.07] blur-[110px]" />

      <DashboardHeader Icon={UsersRound} agentLabel="OCCUPANCY AGENT" title="Occupancy" emphasis="Intelligence" description="ML-driven space utilization monitoring" buildingId={data.building_id} lastUpdated={lastUpdated} isRefreshing={refreshing} onRefresh={refreshNow} accent="violet" />

      <div className="dashboard-content">
        <section className="flex flex-col gap-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <SectionHeader title="Building Overview" subtitle="Live headcount and utilization across every monitored zone" />
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => setUploadOpen(true)}
                className="flex items-center gap-1.5 font-mono text-[10px] text-violet-600 dark:text-violet-400 border border-violet-500/30 dark:border-violet-400/30 bg-violet-500/5 dark:bg-violet-400/5 rounded-full px-3 py-1.5 hover:bg-violet-500/10 transition-colors"
              >
                <UploadCloud size={12} /> UPLOAD DATASET
              </button>
              <button
                onClick={() => setManagerFor({})}
                className="flex items-center gap-1.5 font-mono text-[10px] text-violet-600 dark:text-violet-400 border border-violet-500/30 dark:border-violet-400/30 bg-violet-500/5 dark:bg-violet-400/5 rounded-full px-3 py-1.5 hover:bg-violet-500/10 transition-colors"
              >
                <Database size={12} /> MANAGE DATASET
              </button>
            </div>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-4">
              <HeroStatCard
                label="Total Headcount"
                value={data.building.total_headcount}
                unit={`/ ${data.building.total_capacity ?? '—'} capacity`}
                icon={UsersRound}
              />
            </div>
            <div className="lg:col-span-8">
              <OccupancyKpiRow building={data.building} confidence={data.model_confidence} hideHero />
            </div>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
            <ZoneHeatmap heatmap={data.heatmap} zones={data.zones} onSelect={setSelectedZoneId} />
            <ZoneTable zones={data.zones} onSelect={setSelectedZoneId} selectedZoneId={selectedZoneId} />
          </div>

          <AiInsightsPanel insights={data.ai_insights} bestZone={data.best_available_zone} />
        </section>

        <section className="flex flex-col gap-4">
          <SectionHeader title="Model Comparison" subtitle="A second, genuinely-trained model evaluated honestly against the primary classifier" />
          <CnnModelPanel cnn={data.cnn_model_confidence} baseline={data.model_confidence} />
        </section>

        <AgentInvestigationPanel investigation={investigation} isLoading={investigating} onRun={runInvestigation} buildingId={data.building_id} title="Ask the Occupancy Agent" prompt="It maps utilization across the building, investigates the spaces that matter, and hands off restricted-zone risk to Security when needed." traceTitle="Occupancy Agent Trace" hint="Watch the agent decide whether a zone requires a Security handoff." buttonLabel="INVESTIGATE OCCUPANCY" accent="violet" />

        <section className="flex flex-col gap-4">
          <SectionHeader title="Alerts" subtitle="Overcrowding, low-utilization space signals, and restricted-zone security handoffs" />
          <OccupancyAlertsList alerts={data.top_alerts} />
        </section>
      </div>

      <ZoneDetailPanel zoneId={selectedZoneId} onClose={() => setSelectedZoneId(null)} />

      <DataManagerModal
        open={!!managerFor}
        onClose={() => setManagerFor(null)}
        title="Manage Occupancy Dataset"
        subtitle={managerFor?.zone_id ? `Filtered to ${managerFor.name}` : 'All zones'}
        fields={OCCUPANCY_FIELDS}
        columns={OCCUPANCY_COLUMNS}
        fetchRecords={limit => occupancyService.getRecentRecords(managerFor?.zone_id || null, limit)}
        addRecord={payload => occupancyService.addRecord(payload)}
        deleteRecord={id => occupancyService.deleteRecord(id)}
        clearAllRecords={zoneId => occupancyService.clearAllRecords(zoneId)}
        onChanged={refreshNow}
        lockedField={managerFor?.zone_id ? { key: 'zone_id', value: managerFor.zone_id, label: managerFor.name } : null}
      />

      <DatasetUploadPanel
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        title="Upload Occupancy Dataset"
        subtitle="CSV/Excel with zone_id, headcount, timestamp"
        uploadFn={file => occupancyService.uploadDataset(file)}
        onUploaded={refreshNow}
        accentClass="violet"
      />
    </div>
  )
}
