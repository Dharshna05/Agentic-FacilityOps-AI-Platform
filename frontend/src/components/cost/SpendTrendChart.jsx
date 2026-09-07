import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceDot, ResponsiveContainer } from 'recharts'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import Card from '../maintenance/Card'
import { useTheme } from '../../context/ThemeContext'
import { formatINR } from '../../services/costService'

const DIRECTION_META = {
  up: { Icon: TrendingUp, className: 'text-rose-500' },
  down: { Icon: TrendingDown, className: 'text-teal-500' },
  flat: { Icon: Minus, className: 'text-slate-400' },
}

/**
 * Actual weekly spend (real, from the ledger) plotted alongside the
 * model's forecasted next-week point — the same "history + honest forward
 * prediction" framing the Energy and Maintenance dashboards already give
 * their own ML models, previously missing from the Cost dashboard (which
 * only surfaced a single forward number, with no sense of the trend that
 * produced it).
 */
export default function SpendTrendChart({ forecast }) {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  if (!forecast?.available || !forecast.history?.length) return null

  const { history, predicted_next_3wk_avg_spend_inr, direction, next_week } = forecast
  const data = history.map(h => ({ week: h.week, actual: h.actual_spend_inr }))
  const dirMeta = DIRECTION_META[direction] || DIRECTION_META.flat
  const DirIcon = dirMeta.Icon

  const gridColor = isDark ? '#1e293b' : '#e2e8f0'
  const tickColor = isDark ? '#64748b' : '#94a3b8'
  const lineColor = isDark ? '#f0a860' : '#d97706'
  const forecastColor = isDark ? '#2DD4BF' : '#0d9488'
  const tooltipBg = isDark ? '#12141a' : '#ffffff'
  const tooltipBorder = isDark ? '#1e293b' : '#e2e8f0'

  return (
    <Card title="Weekly Spend Trend" badge="ACTUAL + FORECAST">
      <div className="flex items-center gap-2 mb-3">
        <DirIcon size={14} className={dirMeta.className} />
        <span className="font-mono text-[11px] text-slate-500">
          Next-week forecast: <span className="text-ink dark:text-slate-200 font-semibold">{formatINR(predicted_next_3wk_avg_spend_inr)}</span>
          {next_week ? ` (week of ${next_week})` : ''}, trending {direction}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis dataKey="week" tick={{ fontSize: 9, fill: tickColor }} interval={Math.max(Math.floor(data.length / 8), 0)} />
          <YAxis tick={{ fontSize: 9, fill: tickColor }} tickFormatter={v => `₹${(v / 1e5).toFixed(1)}L`} width={54} />
          <Tooltip
            contentStyle={{ background: tooltipBg, border: `1px solid ${tooltipBorder}`, borderRadius: 8, fontSize: 12 }}
            formatter={v => formatINR(v)}
          />
          <Line type="monotone" dataKey="actual" name="Actual weekly spend" stroke={lineColor} strokeWidth={1.5} dot={{ r: 2 }} />
          {data.length > 0 && (
            <ReferenceDot
              x={data[data.length - 1].week}
              y={predicted_next_3wk_avg_spend_inr}
              r={5}
              fill={forecastColor}
              stroke={isDark ? '#0b0d12' : '#ffffff'}
              strokeWidth={2}
              ifOverflow="extendDomain"
            />
          )}
        </LineChart>
      </ResponsiveContainer>
      <p className="font-body text-[11px] text-slate-500 mt-2 leading-relaxed">
        Amber line: real observed weekly spend (last {data.length} weeks). Teal dot: the forecast model's next-3-week
        average, plotted against the same axis so the prediction's plausibility is visible at a glance, not just its
        number.
      </p>
    </Card>
  )
}
