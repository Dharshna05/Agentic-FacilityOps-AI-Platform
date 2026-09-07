import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { occupancyService } from '../../services/occupancyService'

const STATUS_COLOR = {
  Overcrowded: '#f43f5e',
  Busy: '#f59e0b',
  Moderate: '#2dd4bf',
  Low: '#94a3b8',
  Unknown: '#94a3b8',
}

function fmtTime(t) {
  if (!t) return '—'
  return new Date(t).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function fmtHour(h) {
  if (h == null) return ''
  const d = new Date(h)
  return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-slate-900/95 border border-slate-700 rounded-lg px-3 py-2 font-mono text-[11px] text-white shadow-xl">
      <div className="text-slate-400 mb-1">{fmtHour(label)}</div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {typeof p.value === 'number' ? p.value.toFixed(1) : p.value}
        </div>
      ))}
    </div>
  )
}

export default function ZoneDetailPanel({ zoneId, onClose }) {
  const [detail, setDetail] = useState(null)
  const [history, setHistory] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!zoneId) return
    let cancelled = false
    setLoading(true)
    setError(null)
    setDetail(null)
    setHistory(null)
    Promise.all([
      occupancyService.getZoneDetail(zoneId),
      occupancyService.getZoneHistory(zoneId, 200),
    ])
      .then(([d, h]) => {
        if (cancelled) return
        setDetail(d)
        setHistory(h.readings)
      })
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [zoneId])

  const color = detail ? (STATUS_COLOR[detail.status] || '#94a3b8') : '#94a3b8'
  const isRestricted = detail?.zone_type === 'restricted'

  // Component stays mounted at all times (parent should render it
  // unconditionally) so AnimatePresence can actually play the exit
  // animation instead of the panel being yanked from the DOM instantly.
  return (
    <AnimatePresence>
      {zoneId && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/30 dark:bg-black/50 z-40"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            key="panel"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed inset-y-0 right-0 w-full sm:w-[440px] bg-paper-raised dark:bg-panel z-50
                       border-l border-slate-200 dark:border-slate-800 shadow-2xl overflow-y-auto">
        <div className="sticky top-0 bg-paper-raised dark:bg-panel border-b border-slate-200 dark:border-slate-800 px-5 py-4 flex items-start justify-between gap-3 z-10">
          <div>
            <div className="font-mono text-[10px] tracking-widest text-slate-500 mb-0.5">{zoneId}</div>
            <h3 className="font-display text-base font-semibold text-ink dark:text-slate-100">
              {detail?.name || 'Loading…'}
            </h3>
            {detail && (
              <p className="font-mono text-[11px] text-slate-500 mt-0.5 flex items-center gap-1.5">
                {detail.zone_type?.replace(/_/g, ' ')}
                {isRestricted && (
                  <span className="px-1.5 py-0.5 rounded-full text-[9px] tracking-wide border border-rose-500/30 bg-rose-500/10 text-rose-400">
                    RESTRICTED
                  </span>
                )}
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
              loading zone diagnostics…
            </div>
          )}

          {error && (
            <div className="text-xs text-red-500 font-mono">{error}</div>
          )}

          {detail && !loading && (
            <>
              {/* Utilization ring + status */}
              <div className="flex items-center gap-4">
                <div className="relative w-16 h-16 shrink-0">
                  <svg viewBox="0 0 36 36" className="w-16 h-16 -rotate-90">
                    <circle cx="18" cy="18" r="15.5" fill="none" stroke="currentColor" strokeWidth="3" className="text-slate-200 dark:text-slate-800" />
                    <circle
                      cx="18" cy="18" r="15.5" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round"
                      strokeDasharray={`${((detail.current_utilization_pct ?? 0) / 100) * 97.4} 97.4`}
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center font-display text-sm font-semibold text-ink dark:text-slate-100">
                    {detail.current_utilization_pct ?? '—'}%
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
                    {detail.current_headcount ?? '—'}/{detail.capacity} people <span className="text-slate-300 dark:text-slate-700">·</span> updated {fmtTime(detail.last_updated)}
                  </p>
                </div>
              </div>

              {/* Restricted-zone flag banner */}
              {isRestricted && detail.status === 'Overcrowded' && (
                <div className="rounded-lg p-3 border border-rose-500/30 bg-rose-500/5 font-mono text-[11px] text-rose-400 leading-relaxed">
                  Occupancy in a restricted zone at this level is exactly what triggers a Security Agent handoff during a deep investigation.
                </div>
              )}

              {/* Today's peak + expected next slot */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-50 dark:bg-panel-raised rounded-lg p-3 border border-slate-200 dark:border-slate-800">
                  <div className="font-mono text-[9px] tracking-widest text-slate-500 mb-1">PEAK TODAY</div>
                  <div className="font-display text-lg font-semibold text-ink dark:text-slate-100">
                    {detail.peak_utilization_today_pct ?? '—'}%
                  </div>
                </div>
                <div className="bg-slate-50 dark:bg-panel-raised rounded-lg p-3 border border-slate-200 dark:border-slate-800">
                  <div className="font-mono text-[9px] tracking-widest text-slate-500 mb-1">EXPECTED NEXT (SAME SLOT)</div>
                  <div className="font-display text-lg font-semibold text-ink dark:text-slate-100">
                    {detail.expected_next_same_slot_pct ?? '—'}%
                  </div>
                </div>
              </div>
              <p className="font-mono text-[9px] text-slate-400 -mt-3 leading-relaxed">
                "expected next" is a same-hour, same-weekday historical average for this zone — not a trained forecasting model.
              </p>

              {/* Utilization history chart */}
              {history?.length > 1 && (
                <div>
                  <h4 className="font-display text-xs font-medium text-ink dark:text-slate-200 mb-2">
                    Utilization Trend <span className="text-slate-400 font-mono text-[10px] font-normal">(last {history.length} readings)</span>
                  </h4>
                  <ResponsiveContainer width="100%" height={180}>
                    <LineChart data={history} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="2 4" className="stroke-slate-200 dark:stroke-slate-800" />
                      <XAxis dataKey="timestamp" tickFormatter={fmtHour} tick={{ fontSize: 9, fontFamily: 'JetBrains Mono' }} className="fill-slate-400" />
                      <YAxis tick={{ fontSize: 9, fontFamily: 'JetBrains Mono' }} className="fill-slate-400" />
                      <Tooltip content={<CustomTooltip />} />
                      <Line type="monotone" dataKey="utilization_pct" name="utilization %" stroke="#2dd4bf" dot={false} strokeWidth={1.75} />
                      <Line type="monotone" dataKey="headcount" name="headcount" stroke="#f59e0b" dot={false} strokeWidth={1.25} />
                    </LineChart>
                  </ResponsiveContainer>
                  <div className="flex gap-4 mt-1">
                    <span className="flex items-center gap-1.5 font-mono text-[10px] text-slate-500">
                      <span className="w-2 h-0.5 bg-teal-400 inline-block" /> utilization %
                    </span>
                    <span className="flex items-center gap-1.5 font-mono text-[10px] text-slate-500">
                      <span className="w-2 h-0.5 bg-amber-400 inline-block" /> headcount
                    </span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
