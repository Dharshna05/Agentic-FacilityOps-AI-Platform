import { useEffect, useState, useCallback } from 'react'
import { LayoutDashboard, Zap, Wrench, Users, ShieldCheck, IndianRupee } from 'lucide-react'
import { Link } from 'react-router-dom'
import { facilityService, formatINR } from '../../services/costService'
import FacilityHealthGauge from '../../components/executive/FacilityHealthGauge'
import UnifiedAlertFeed from '../../components/executive/UnifiedAlertFeed'
import KpiCard from '../../components/cards/KpiCard'
import SectionHeader from '../../components/maintenance/SectionHeader'
import DashboardHeader from '../../components/ui/DashboardHeader'
import AgentInvestigationPanel from '../../components/agent/AgentInvestigationPanel'
import DashboardSkeleton from '../../components/ui/DashboardSkeleton'

export default function ExecutiveDashboardPage() {
  const [health, setHealth] = useState(null)
  const [alertsData, setAlertsData] = useState(null)
  const [kpis, setKpis] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [error, setError] = useState(null)
  const [investigation, setInvestigation] = useState(null)
  const [investigating, setInvestigating] = useState(false)

  const load = useCallback(async () => {
    const [h, a, k] = await Promise.all([
      facilityService.getHealth(),
      facilityService.getAlerts(),
      facilityService.getKpis(),
    ])
    setHealth(h)
    setAlertsData(a)
    setKpis(k)
    setLastUpdated(new Date())
  }, [])

  const refreshNow = useCallback(async () => {
    setRefreshing(true)
    try { await load() } catch (err) { setError(err.message) } finally { setRefreshing(false) }
  }, [load])

  const runInvestigation = useCallback(async () => {
    setInvestigating(true)
    setInvestigation(null)
    try {
      const result = await facilityService.getInvestigation(health?.building_id)
      setInvestigation(result)
    } finally {
      setInvestigating(false)
    }
  }, [health])

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

  if (loading) {
    return (
      <DashboardSkeleton message="AGGREGATING AGENTS…" kpiCount={3} />
    )
  }

  if (error) {
    return <div className="p-6 text-red-500 dark:text-red-400 text-sm font-mono">connection failed: {error}</div>
  }

  return (
    <div className="dashboard-page">
      <div className="pointer-events-none absolute -top-32 -left-20 w-[420px] h-[420px] rounded-full bg-violet-500/10 dark:bg-violet-500/[0.08] blur-[110px]" />
      <div className="pointer-events-none absolute top-40 -right-32 w-[380px] h-[380px] rounded-full bg-amber-400/10 dark:bg-amber-400/[0.07] blur-[110px]" />

      <DashboardHeader Icon={LayoutDashboard} agentLabel="FACILITY INTELLIGENCE ENGINE" title="Executive" emphasis="Overview" description="cross-agent facility health & KPIs" buildingId={health.building_id} lastUpdated={lastUpdated} isRefreshing={refreshing} onRefresh={refreshNow} accent="violet" />

      <div className="dashboard-content">
        <section className="flex flex-col gap-4">
          <SectionHeader title="Facility Snapshot" subtitle="One headline KPI per agent — click through to any domain dashboard for the full picture" />
          <div className="grid grid-cols-2 xl:grid-cols-5 gap-4">
            <Link to="/energy"><KpiCard label="Energy" value={`${(kpis.energy_total_kwh / 1000).toFixed(1)}`} unit="MWh tracked" accent="blue" icon={Zap} /></Link>
            <Link to="/maintenance"><KpiCard label="Fleet Health" value={kpis.maintenance_avg_health_score} unit={`${kpis.maintenance_open_critical} critical`} accent="teal" icon={Wrench} /></Link>
            <Link to="/occupancy"><KpiCard label="Occupancy" value={`${kpis.occupancy_avg_utilization_pct}%`} unit="avg utilization" accent="violet" icon={Users} /></Link>
            <Link to="/security"><KpiCard label="Security" value={kpis.security_flagged_last_24h} unit="flagged (24h)" accent="alert" icon={ShieldCheck} /></Link>
            <Link to="/cost"><KpiCard label="Cost" value={formatINR(kpis.cost_total_spend_inr)} unit={`${kpis.cost_categories_over_budget} over budget`} accent="amber" icon={IndianRupee} /></Link>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 items-start">
            <FacilityHealthGauge health={health} />
            <UnifiedAlertFeed alerts={alertsData.alerts} totalOpen={alertsData.total_open} />
          </div>
        </section>

        <section className="flex flex-col gap-4 mt-6">
          <SectionHeader title="Cross-Domain Investigation" subtitle="One agent, every domain's tools at once — looks for correlations a single-domain agent can't see" />
          <AgentInvestigationPanel
            investigation={investigation}
            isLoading={investigating}
            onRun={runInvestigation}
            buildingId={health.building_id}
            title="Ask the Facility Intelligence Agent"
            prompt="Unlike each domain agent, this one holds Energy, Maintenance, Occupancy, Security, and Cost tools simultaneously — it looks specifically for connections across domains (an energy anomaly and a failing asset, a restricted-zone occupant and a flagged security event) before reporting anything."
            traceTitle="Facility Intelligence Agent Trace"
            hint="Pulls a baseline from every domain, then only chases a specific thread if two domains' evidence actually lines up."
            buttonLabel="INVESTIGATE ACROSS ALL DOMAINS"
            accent="violet"
          />
        </section>
      </div>
    </div>
  )
}
