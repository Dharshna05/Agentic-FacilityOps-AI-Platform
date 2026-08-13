import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useTheme } from '../../context/ThemeContext'

const RANGE_OPTIONS = [
  { label: '24H', limit: 96 },
  { label: '3 Days', limit: 288 },
  { label: '7 Days', limit: 672 },
  { label: '30 Days', limit: 2880 },
  { label: '90 Days', limit: 8640 },
  { label: 'All (365d)', limit: 35040 },
]

/**
 * Min-max decimation: splits readings into buckets and keeps BOTH the
 * min and max point per bucket (in chronological order), instead of
 * naive "every Nth point" sampling. Naive sampling can silently skip the
 * exact row holding the true peak/trough — which caused the KPI card
 * (computed from the full dataset) and the chart (visually thinned) to
 * disagree on where the peak was. This keeps them consistent.
 */
function minMaxDecimate(readings, maxPoints) {
  if (readings.length <= maxPoints) return readings

  const bucketCount = Math.floor(maxPoints / 2)
  const bucketSize = Math.ceil(readings.length / bucketCount)
  const result = []

  for (let i = 0; i < readings.length; i += bucketSize) {
    const bucket = readings.slice(i, i + bucketSize)
    if (bucket.length === 0) continue

    let minPoint = bucket[0]
    let maxPoint = bucket[0]
    for (const r of bucket) {
      if (r.total_kwh < minPoint.total_kwh) minPoint = r
      if (r.total_kwh > maxPoint.total_kwh) maxPoint = r
    }

    // Keep chronological order within the bucket
    if (new Date(minPoint.timestamp) <= new Date(maxPoint.timestamp)) {
      result.push(minPoint, maxPoint)
    } else {
      result.push(maxPoint, minPoint)
    }
  }
  return result
}

export default function ConsumptionChart({ readings, selectedRange, onRangeChange }) {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  const MAX_POINTS = 500
  const thinned = minMaxDecimate(readings, MAX_POINTS)

  const data = thinned.map(r => ({
    time: new Date(r.timestamp).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit' }),
    total: r.total_kwh,
  }))

  const gridColor = isDark ? '#1e293b' : '#e2e8f0'
  const tickColor = isDark ? '#64748b' : '#94a3b8'
  const lineColor = isDark ? '#2DD4BF' : '#0d9488'
  const tooltipBg = isDark ? '#12141a' : '#ffffff'
  const tooltipBorder = isDark ? '#1e293b' : '#e2e8f0'

  return (
    <div className="bg-paper-raised dark:bg-panel border border-slate-200 dark:border-slate-800 rounded-xl p-5">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h3 className="font-display text-sm font-medium text-ink dark:text-slate-200">Energy Consumption (kWh)</h3>
        <div className="flex gap-1 flex-wrap">
          {RANGE_OPTIONS.map(opt => (
            <button
              key={opt.label}
              onClick={() => onRangeChange(opt.limit)}
              className={`text-xs px-2.5 py-1 rounded-md border transition-colors ${
                selectedRange === opt.limit
                  ? 'bg-teal-50 dark:bg-teal-500/20 border-teal-400 text-teal-700 dark:text-teal-300'
                  : 'border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:border-slate-400 dark:hover:border-slate-500'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={420}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis
            dataKey="time"
            tick={{ fontSize: 10, fill: tickColor }}
            interval={Math.max(Math.floor(data.length / 10), 0)}
          />
          <YAxis tick={{ fontSize: 10, fill: tickColor }} />
          <Tooltip
            contentStyle={{ background: tooltipBg, border: `1px solid ${tooltipBorder}`, borderRadius: 8, fontSize: 12 }}
          />
          <Line type="monotone" dataKey="total" stroke={lineColor} strokeWidth={1.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
