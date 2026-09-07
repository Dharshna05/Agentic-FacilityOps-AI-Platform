import { useEffect, useState, useCallback } from 'react'
import { Activity, Database, UploadCloud } from 'lucide-react'
import { securityService } from '../../services/securityService'
import SecurityKpiRow from '../../components/security/SecurityKpiRow'
import FlaggedEventsList from '../../components/security/FlaggedEventsList'
import SecurityAlertsList from '../../components/security/SecurityAlertsList'
import RiskHeatmap from '../../components/security/RiskHeatmap'
import AccessPointRiskGrid from '../../components/security/AccessPointRiskGrid'
import SecurityModelComparison from '../../components/security/SecurityModelComparison'
import SectionHeader from '../../components/maintenance/SectionHeader'
import AgentInvestigationPanel from '../../components/agent/AgentInvestigationPanel'
import DashboardHeader from '../../components/ui/DashboardHeader'
import HeroStatCard from '../../components/cards/HeroStatCard'
import DataManagerModal from '../../components/shared/DataManagerModal'
import DatasetUploadPanel from '../../components/shared/DatasetUploadPanel'
import DashboardSkeleton from '../../components/ui/DashboardSkeleton'
import DataDriftBanner from '../../components/ui/DataDriftBanner'

const SECURITY_FIELDS = [
  { key: 'access_point_id', label: 'Access point ID', type: 'text', required: true, placeholder: 'AP-01' },
  { key: 'employee_id', label: 'Employee ID', type: 'text', required: true, placeholder: 'EMP-0123' },
  { key: 'timestamp', label: 'Timestamp', type: 'datetime-local' },
  { key: 'access_granted', label: 'Access granted', type: 'checkbox', defaultValue: true },
]
const SECURITY_COLUMNS = [
  { key: 'access_point_id', label: 'door' },
  { key: 'employee_id', label: 'employee' },
  { key: 'access_granted', label: 'granted', format: v => (v ? 'yes' : 'NO') },
]

export default function SecurityDashboardPage() {
  const [data, setData] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [investigation, setInvestigation] = useState(null)
  const [investigating, setInvestigating] = useState(false)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [error, setError] = useState(null)
  const [managerFor, setManagerFor] = useState(null) // null = closed; {} = open unfiltered; {access_point_id,name} = filtered
  const [uploadOpen, setUploadOpen] = useState(false)

  const load = useCallback(async () => {
    const [building, alertsData] = await Promise.all([
      securityService.getBuilding(),
      securityService.getAlerts(),
    ])
    setData(building)
    setAlerts(alertsData.alerts)
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
      const result = await securityService.getInvestigation()
      setInvestigation(result)
      const alertsData = await securityService.getAlerts()
      setAlerts(alertsData.alerts)
    } catch (err) {
      setError(err.message)
    } finally {
      setInvestigating(false)
    }
  }, [])

  if (loading) {
    return (
      <DashboardSkeleton message="SCANNING ACCESS LOGS…" kpiCount={4} />
    )
  }

  if (error) {
    return <div className="p-6 text-red-500 dark:text-red-400 text-sm font-mono">connection failed: {error}</div>
  }

  return (
    <div className="dashboard-page">
      <div className="pointer-events-none absolute -top-32 -left-20 w-[420px] h-[420px] rounded-full bg-rose-500/10 dark:bg-rose-500/[0.08] blur-[110px]" />
      <div className="pointer-events-none absolute top-40 -right-32 w-[380px] h-[380px] rounded-full bg-teal-400/10 dark:bg-teal-400/[0.07] blur-[110px]" />

      <DashboardHeader Icon={Activity} agentLabel="SECURITY AGENT" title="Security" emphasis="Intelligence" description="anomaly-driven access monitoring" buildingId={data.building_id} lastUpdated={lastUpdated} isRefreshing={refreshing} onRefresh={refreshNow} accent="rose" />

      <div className="dashboard-content">
        <section className="flex flex-col gap-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <SectionHeader title="Building Overview" subtitle="Access activity and anomaly detection across every monitored entry point" />
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => setUploadOpen(true)}
                className="flex items-center gap-1.5 font-mono text-[10px] text-rose-600 dark:text-rose-400 border border-rose-500/30 dark:border-rose-400/30 bg-rose-500/5 dark:bg-rose-400/5 rounded-full px-3 py-1.5 hover:bg-rose-500/10 transition-colors"
              >
                <UploadCloud size={12} /> UPLOAD DATASET
              </button>
              <button
                onClick={() => setManagerFor({})}
                className="flex items-center gap-1.5 font-mono text-[10px] text-rose-600 dark:text-rose-400 border border-rose-500/30 dark:border-rose-400/30 bg-rose-500/5 dark:bg-rose-400/5 rounded-full px-3 py-1.5 hover:bg-rose-500/10 transition-colors"
              >
                <Database size={12} /> MANAGE DATASET
              </button>
            </div>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-4">
              <HeroStatCard
                label="Events (24h)"
                value={data.building.events_last_24h}
                unit="access events"
                icon={Activity}
              />
            </div>
            <div className="lg:col-span-8">
              <SecurityKpiRow building={data.building} confidence={data.model_confidence} hideHero />
            </div>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
            <RiskHeatmap
              heatmap={data.heatmap}
              accessPoints={data.access_points}
              onSelect={apId => setManagerFor({ access_point_id: apId, name: data.access_points.find(a => a.access_point_id === apId)?.name || apId })}
            />
            <AccessPointRiskGrid
              activity={data.access_point_activity}
              onSelect={apId => setManagerFor({ access_point_id: apId, name: data.access_point_activity.find(a => a.access_point_id === apId)?.name || apId })}
            />
          </div>
          <FlaggedEventsList events={data.flagged_events} />
          <SecurityModelComparison primary={data.model_confidence} comparison={data.comparison_model_confidence} supervisedReference={data.supervised_reference_confidence} />
          <DataDriftBanner drift={data.data_drift} subject="the currently loaded access-log data" />
        </section>

        <AgentInvestigationPanel investigation={investigation} isLoading={investigating} onRun={runInvestigation} buildingId={data.building_id} title="Ask the Security Agent" prompt="It weighs each anomaly against access-point risk, traces the context, and opens only the alerts that deserve escalation." traceTitle="Security Agent Trace" hint="A real-time activity trace of evidence, risk assessment, and escalations." buttonLabel="INVESTIGATE ACCESS ACTIVITY" accent="rose" />

        <section className="flex flex-col gap-4">
          <SectionHeader title="Alerts" subtitle="Anomaly-driven alerts, plus restricted-zone handoffs from the Occupancy Agent" />
          <SecurityAlertsList alerts={alerts} />
        </section>
      </div>

      <DataManagerModal
        open={!!managerFor}
        onClose={() => setManagerFor(null)}
        title="Manage Security Dataset"
        subtitle={managerFor?.access_point_id ? `Filtered to ${managerFor.name}` : 'All access points'}
        fields={SECURITY_FIELDS}
        columns={SECURITY_COLUMNS}
        fetchRecords={limit => securityService.getRecentRecords(managerFor?.access_point_id || null, limit)}
        addRecord={payload => securityService.addRecord(payload)}
        deleteRecord={id => securityService.deleteRecord(id)}
        clearAllRecords={apId => securityService.clearAllRecords(apId)}
        onChanged={refreshNow}
        lockedField={managerFor?.access_point_id ? { key: 'access_point_id', value: managerFor.access_point_id, label: managerFor.name } : null}
      />

      <DatasetUploadPanel
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        title="Upload Security Dataset"
        subtitle="CSV/Excel with access_point_id, employee_id, timestamp, access_granted"
        uploadFn={file => securityService.uploadDataset(file)}
        onUploaded={refreshNow}
        accentClass="rose"
      />
    </div>
  )
}
