import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { maintenanceService } from '../../services/maintenanceService'
import DataDriftBanner from '../ui/DataDriftBanner'

const STATUS_COLOR = {
  Excellent: '#10b981',
  Good: '#2dd4bf',
  Warning: '#f59e0b',
  Critical: '#f43f5e',
}

function fmtDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-slate-900/95 border border-slate-700 rounded-lg px-3 py-2 font-mono text-[11px] text-white shadow-xl">
      <div className="text-slate-400 mb-1">cycle {label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {typeof p.value === 'number' ? p.value.toFixed(3) : p.value}
        </div>
      ))}
    </div>
  )
}

// Horizontal bar showing the RUL prediction interval [lower — predicted — upper]
// against the model's clip ceiling (125 cycles). This is the whole point of
// having a quantile model at all: a single number invites false precision,
// a band is the honest picture.
function RulIntervalBar({ predicted, lower, upper, clip = 125 }) {
  const pct = (v) => Math.max(0, Math.min(100, (v / clip) * 100))
  if (lower == null || upper == null) {
    return (
      <div className="text-xs font-mono text-slate-500">
        predicted RUL: {predicted} cycles (interval unavailable)
      </div>
    )
  }
  return (
    <div>
      <div className="relative h-2.5 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
        <div
          className="absolute h-full bg-teal-400/30 dark:bg-teal-400/25 rounded-full"
          style={{ left: `${pct(lower)}%`, width: `${pct(upper) - pct(lower)}%` }}
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-1 h-4 rounded-full bg-teal-500 dark:bg-teal-300 shadow"
          style={{ left: `calc(${pct(predicted)}% - 2px)` }}
        />
      </div>
      <div className="flex justify-between mt-1.5 font-mono text-[10px] text-slate-500">
        <span>p10: {lower}d</span>
        <span className="text-teal-600 dark:text-teal-300 font-medium">predicted: {predicted}d</span>
        <span>p90: {upper}d</span>
      </div>
    </div>
  )
}

export default function AssetDetailPanel({ assetId, onClose }) {
  const [detail, setDetail] = useState(null)
  const [history, setHistory] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!assetId) return
    let cancelled = false
    setLoading(true)
    setError(null)
    Promise.all([
      maintenanceService.getAssetDetail(assetId),
      maintenanceService.getAssetHistory(assetId, 100),
    ])
      .then(([d, h]) => {
        if (cancelled) return
        setDetail(d)
        setHistory(h.readings)
      })
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [assetId])

  const color = detail ? STATUS_COLOR[detail.status] || '#94a3b8' : '#94a3b8'

  return (
    <AnimatePresence>
      {assetId && <>
      <motion.div key="asset-backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/30 dark:bg-black/50 z-40" onClick={onClose} />

      <motion.div key="asset-panel" initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={{ type: 'spring', stiffness: 300, damping: 30 }} className="fixed inset-y-0 right-0 w-full sm:w-[440px] bg-paper-raised dark:bg-panel z-50
                       border-l border-slate-200 dark:border-slate-800 shadow-2xl overflow-y-auto">
        <div className="sticky top-0 bg-paper-raised dark:bg-panel border-b border-slate-200 dark:border-slate-800 px-5 py-4 flex items-start justify-between gap-3 z-10">
          <div>
            <div className="font-mono text-[10px] tracking-widest text-slate-500 mb-0.5">{assetId}</div>
            <h3 className="font-display text-base font-semibold text-ink dark:text-slate-100">
              {detail?.name || 'Loading…'}
            </h3>
            {detail && (
              <p className="font-mono text-[11px] text-slate-500 mt-0.5">
                {detail.asset_type} <span className="text-slate-300 dark:text-slate-700">·</span> {detail.location}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-slate-400
                       hover:text-ink dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-5 flex flex-col gap-5">
          {loading && (
            <div className="font-mono text-xs text-slate-500 animate-pulse-line py-8 text-center">
              loading asset diagnostics…
            </div>
          )}

          {error && (
            <div className="text-xs text-red-500 font-mono">{error}</div>
          )}

          {detail && !loading && (
            <>
              {/* Health + status */}
              <div className="flex items-center gap-4">
                <div className="relative w-16 h-16 shrink-0">
                  <svg viewBox="0 0 36 36" className="w-16 h-16 -rotate-90">
                    <circle cx="18" cy="18" r="15.5" fill="none" stroke="currentColor" strokeWidth="3" className="text-slate-200 dark:text-slate-800" />
                    <circle
                      cx="18" cy="18" r="15.5" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round"
                      strokeDasharray={`${(detail.health_score / 100) * 97.4} 97.4`}
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center font-display text-sm font-semibold text-ink dark:text-slate-100">
                    {detail.health_score}
                  </div>
                </div>
                <div>
                  <span
                    className="inline-block px-2.5 py-1 rounded-full text-[11px] font-mono border"
                    style={{ color, borderColor: `${color}50`, backgroundColor: `${color}15` }}
                  >
                    {detail.status}
                  </span>
                  <p className="font-mono text-[11px] text-slate-500 mt-1.5">
                    latest cycle {detail.latest_cycle} <span className="text-slate-300 dark:text-slate-700">·</span> {fmtDate(detail.latest_timestamp)}
                  </p>
                </div>
              </div>

              {/* RUL prediction interval */}
              <div className="bg-slate-50 dark:bg-panel-raised rounded-lg p-4 border border-slate-200 dark:border-slate-800">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-display text-xs font-medium text-ink dark:text-slate-200">Remaining Useful Life</h4>
                  <span className="font-mono text-[9px] tracking-widest px-2 py-0.5 rounded-full bg-teal-500/10 border border-teal-500/30 text-teal-500 dark:text-teal-400">
                    {detail.confidence?.model_used?.replace(/_/g, ' ') || 'ML MODEL'}
                  </span>
                </div>
                <RulIntervalBar
                  predicted={detail.predicted_rul_cycles}
                  lower={detail.rul_lower_cycles}
                  upper={detail.rul_upper_cycles}
                />
                <p className="font-mono text-[10px] text-slate-500 mt-3 leading-relaxed">
                  Predicted maintenance window: {fmtDate(detail.maintenance_date_earliest) ?? '—'} → {fmtDate(detail.maintenance_date_latest)}
                  {' '}(best estimate {fmtDate(detail.predicted_maintenance_date)})
                </p>
              </div>

              {/* Top contributing factors — lightweight, honest explainability */}
              {detail.top_factors?.length > 0 && (
                <div>
                  <h4 className="font-display text-xs font-medium text-ink dark:text-slate-200 mb-2">
                    Why This Score
                  </h4>
                  <div className="flex flex-col gap-1.5">
                    {detail.top_factors.map((f, i) => (
                      <div
                        key={i}
                        className="flex items-center justify-between gap-2 text-xs bg-slate-50 dark:bg-panel-raised rounded-lg px-3 py-2 border border-slate-200 dark:border-slate-800"
                      >
                        <span className="text-slate-600 dark:text-slate-300">{f.feature}</span>
                        <span className={`font-mono text-[10px] shrink-0 ${f.direction === 'above normal' ? 'text-amber-500' : 'text-blue-400'}`}>
                          {f.direction} ({f.z_score > 0 ? '+' : ''}{f.z_score}σ)
                        </span>
                      </div>
                    ))}
                  </div>
                  <p className="font-mono text-[9px] text-slate-400 mt-1.5 leading-relaxed">
                    most statistically unusual readings for this asset vs. the training fleet, weighted by how much the model relies on each signal — not a per-instance SHAP explanation
                  </p>
                </div>
              )}

              {/* Degradation trend */}
              {detail.trend?.available && (
                <div className="flex items-center gap-2.5 text-xs font-mono">
                  <span
                    className={`px-2 py-1 rounded-full border ${
                      detail.trend.direction === 'worsening'
                        ? 'text-rose-500 border-rose-500/30 bg-rose-500/10'
                        : detail.trend.direction === 'improving'
                        ? 'text-emerald-500 border-emerald-500/30 bg-emerald-500/10'
                        : 'text-slate-500 border-slate-300 dark:border-slate-700'
                    }`}
                  >
                    vibration trend: {detail.trend.direction}
                  </span>
                  <span className="text-slate-400">slope {detail.trend.vibration_slope_per_cycle}/cycle</span>
                </div>
              )}

              {/* Sensor trend chart */}
              {history?.length > 1 && (
                <div>
                  <h4 className="font-display text-xs font-medium text-ink dark:text-slate-200 mb-2">
                    Sensor Trend <span className="text-slate-400 font-mono text-[10px] font-normal">(last {history.length} cycles)</span>
                  </h4>
                  <ResponsiveContainer width="100%" height={180}>
                    <LineChart data={history} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="2 4" className="stroke-slate-200 dark:stroke-slate-800" />
                      <XAxis dataKey="cycle" tick={{ fontSize: 9, fontFamily: 'JetBrains Mono' }} className="fill-slate-400" />
                      <YAxis tick={{ fontSize: 9, fontFamily: 'JetBrains Mono' }} className="fill-slate-400" />
                      <Tooltip content={<CustomTooltip />} />
                      <Line type="monotone" dataKey="vibration_index" name="vibration" stroke="#f43f5e" dot={false} strokeWidth={1.75} />
                      <Line type="monotone" dataKey="efficiency_ratio" name="efficiency" stroke="#2dd4bf" dot={false} strokeWidth={1.75} />
                    </LineChart>
                  </ResponsiveContainer>
                  <div className="flex gap-4 mt-1">
                    <span className="flex items-center gap-1.5 font-mono text-[10px] text-slate-500">
                      <span className="w-2 h-0.5 bg-rose-500 inline-block" /> vibration index
                    </span>
                    <span className="flex items-center gap-1.5 font-mono text-[10px] text-slate-500">
                      <span className="w-2 h-0.5 bg-teal-400 inline-block" /> efficiency ratio
                    </span>
                  </div>
                </div>
              )}

              {/* Model confidence footer */}
              {detail.confidence?.available && (
                <div className="pt-3 border-t border-slate-200 dark:border-slate-800 font-mono text-[10px] text-slate-500 leading-relaxed">
                  Model held-out accuracy: MAE {detail.confidence.mae_cycles} cycles, R² {detail.confidence.r2}
                  {' '}({detail.confidence.confidence} confidence, {detail.confidence.improvement_over_naive_pct}% better than naive baseline)
                  {detail.confidence.is_deep_learning && <span className="ml-1 text-teal-600 dark:text-teal-400">· deep learning (LSTM)</span>}
                </div>
              )}

              <DataDriftBanner drift={detail.data_drift} subject="this asset's current sensor readings" />
            </>
          )}
        </div>
      </motion.div>
      </>}
    </AnimatePresence>
  )
}
