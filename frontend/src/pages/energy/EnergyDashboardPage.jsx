import { useEffect, useState, useCallback, useRef } from 'react'
import { energyService } from '../../services/energyService'
import KpiCard from '../../components/cards/KpiCard'
import ConsumptionChart from '../../components/charts/ConsumptionChart'
import BreakdownChart from '../../components/charts/BreakdownChart'
import RecommendationsList from '../../components/cards/RecommendationsList'
import ForecastCard from '../../components/cards/ForecastCard'
import ModelReliabilityChart from '../../components/charts/ModelReliabilityChart'
import BriefingCard from '../../components/cards/BriefingCard'
import AgentTraceViewer from '../../components/agent/AgentTraceViewer'
import LiveIndicator from '../../components/ui/LiveIndicator'

const DEFAULT_RANGE = 672 // 7 days at 15-min resolution
const POLL_INTERVAL_MS = 30_000

export default function EnergyDashboardPage() {
  const [dashboard, setDashboard] = useState(null)
  const [readings, setReadings] = useState([])
  const [readingsLimit, setReadingsLimit] = useState(DEFAULT_RANGE)
  const [briefing, setBriefing] = useState(null)
  const [forecastScatter, setForecastScatter] = useState(null)
  const [investigation, setInvestigation] = useState(null)
  const [investigating, setInvestigating] = useState(false)
  const [loading, setLoading] = useState(true)
  const [rangeLoading, setRangeLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [error, setError] = useState(null)
  const pollRef = useRef(null)

  const fetchAll = useCallback(async (limit) => {
    const [dash, readingsData, briefingData, scatterData] = await Promise.all([
      energyService.getDashboard('BLD-HQ-01', limit),
      energyService.getReadings('BLD-HQ-01', limit),
      energyService.getBriefing().catch(() => null),
      energyService.getForecastScatter('1h').catch(() => null),
    ])
    setDashboard(dash)
    setReadings(readingsData.readings)
    setBriefing(briefingData)
    setForecastScatter(scatterData)
    setLastUpdated(new Date())
  }, [])

  const refreshNow = useCallback(async () => {
    setRefreshing(true)
    try {
      await fetchAll(readingsLimit)
    } catch (err) {
      setError(err.message)
    } finally {
      setRefreshing(false)
    }
  }, [fetchAll, readingsLimit])

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        setLoading(true)
        await fetchAll(DEFAULT_RANGE)
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [fetchAll])

  // Silent background polling on the current range, same idea as the
  // Maintenance dashboard — keeps "LIVE" honest rather than decorative.
  useEffect(() => {
    pollRef.current = setInterval(() => {
      setRefreshing(true)
      fetchAll(readingsLimit).catch(() => {}).finally(() => setRefreshing(false))
    }, POLL_INTERVAL_MS)
    return () => clearInterval(pollRef.current)
  }, [fetchAll, readingsLimit])

  // Range change now refetches BOTH the chart data AND the KPI/analytics
  // summary for that same window — previously only the chart updated while
  // Total/Avg/Peak/Anomalies stayed pinned to the full-dataset numbers.
  const handleRangeChange = useCallback(async (limit) => {
    setReadingsLimit(limit)
    setRangeLoading(true)
    try {
      const [readingsData, dash] = await Promise.all([
        energyService.getReadings('BLD-HQ-01', limit),
        energyService.getDashboard('BLD-HQ-01', limit),
      ])
      setReadings(readingsData.readings)
      setDashboard(dash)
      setLastUpdated(new Date())
    } catch (err) {
      setError(err.message)
    } finally {
      setRangeLoading(false)
    }
  }, [])

  const runInvestigation = useCallback(async () => {
    setInvestigating(true)
    setInvestigation(null)
    try {
      const result = await energyService.getInvestigation()
      setInvestigation(result)
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
          INITIALIZING FACILITY LINK…
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

  const { consumption, breakdown, trend_pct_vs_prev_period, anomaly_count, top_recommendations } = dashboard

  return (
    <div className="min-h-screen animate-fade-in">
      <div className="border-b border-slate-200 dark:border-slate-800/80 px-6 md:px-10 py-6 flex items-end justify-between flex-wrap gap-4">
        <div>
          <div className="mb-2">
            <LiveIndicator lastUpdated={lastUpdated} isRefreshing={refreshing} onRefresh={refreshNow} />
          </div>
          <h1 className="font-display text-3xl md:text-4xl font-semibold text-ink dark:text-slate-100 tracking-tight">
            Energy Monitoring
          </h1>
          <p className="font-mono text-xs text-slate-500 mt-2">
            {dashboard.building_id} <span className="text-slate-300 dark:text-slate-700">·</span> {consumption.period}
          </p>
        </div>
      </div>

      <div className="p-6 md:p-10 flex flex-col gap-6 max-w-[1400px]">
        <div className={`grid grid-cols-2 md:grid-cols-4 gap-4 transition-opacity ${rangeLoading ? 'opacity-50' : ''}`}>
          <KpiCard label="Total Consumption" value={consumption.total_kwh.toLocaleString()} unit="kWh" accent="blue" />
          <KpiCard label="Avg Hourly Load" value={consumption.avg_hourly_kwh} unit="kWh"
                   trend={trend_pct_vs_prev_period} accent="violet" />
          <KpiCard label="Peak Load" value={consumption.peak_kwh} unit="kWh" accent="amber" />
          <KpiCard label="Anomalies Detected" value={anomaly_count} unit="events"
                   accent={anomaly_count > 0 ? 'alert' : 'emerald'} />
        </div>

        <div className={`transition-opacity ${rangeLoading ? 'opacity-50' : ''}`}>
          <ConsumptionChart readings={readings} selectedRange={readingsLimit} onRangeChange={handleRangeChange} />
        </div>

        <div className={`transition-opacity ${rangeLoading ? 'opacity-50' : ''}`}>
          <BreakdownChart breakdown={breakdown} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ForecastCard />
          <BriefingCard briefing={briefing} />
        </div>

        <ModelReliabilityChart
          title="1h Forecast Model Reliability"
          subtitle="Actual vs. predicted consumption on held-out test data"
          data={forecastScatter}
          unit="kWh"
        />

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-4 items-start">
          <div className="bg-paper-raised dark:bg-panel border border-slate-200 dark:border-slate-800 rounded-xl p-5 flex flex-col gap-3">
            <h3 className="font-display text-sm font-medium text-ink dark:text-slate-200">Run Deep Investigation</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Give the agent a goal — not a fixed set of steps — and let it decide which tools
              to call, in what order, based on what it finds along the way.
            </p>
            <button
              onClick={runInvestigation}
              disabled={investigating}
              className="mt-1 font-mono text-xs tracking-wide px-4 py-2.5 rounded-lg border border-teal-500/50 dark:border-teal-400/40
                         text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-400/5 hover:bg-teal-100 dark:hover:bg-teal-400/10
                         hover:border-teal-600 dark:hover:border-teal-400/70
                         disabled:opacity-40 disabled:cursor-not-allowed transition-colors self-start"
            >
              {investigating ? 'agent working…' : '▶ investigate energy efficiency'}
            </button>
          </div>

          <AgentTraceViewer investigation={investigation} isLoading={investigating} />
        </div>

        <RecommendationsList recommendations={top_recommendations} />
      </div>
    </div>
  )
}
