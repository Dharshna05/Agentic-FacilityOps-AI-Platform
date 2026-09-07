import { useState } from 'react'
import Card from '../maintenance/Card'

// Anomaly score is unbounded (higher = more statistically unusual), but in
// practice this dataset's live scores cluster roughly 0.2-0.9 — thresholds
// tuned against that real range, not an arbitrary 0-1 guess.
function riskColor(score) {
  if (score >= 0.65) return 'bg-rose-500'
  if (score >= 0.5) return 'bg-amber-400'
  if (score >= 0.35) return 'bg-teal-400'
  if (score > 0) return 'bg-teal-200 dark:bg-teal-900'
  return 'bg-slate-100 dark:bg-slate-800'
}

const HOURS = Array.from({ length: 24 }, (_, i) => i)

export default function RiskHeatmap({ heatmap, accessPoints, onSelect }) {
  const nameById = Object.fromEntries((accessPoints || []).map(a => [a.access_point_id, a.name]))
  const [hovered, setHovered] = useState(null)

  if (!heatmap?.length) return null

  return (
    <Card title="Access Risk Heatmap" badge="AVG ANOMALY SCORE BY HOUR">
      <div className="overflow-x-auto">
        <div className="min-w-[640px]">
          <div className="grid gap-[3px] mb-1" style={{ gridTemplateColumns: '140px repeat(24, 1fr)' }}>
            <div />
            {HOURS.map(h => (
              <div key={h} className="text-center font-mono text-[8px] text-slate-400">
                {h % 3 === 0 ? h : ''}
              </div>
            ))}
          </div>
          {heatmap.map(row => (
            <div key={row.access_point_id} className="grid gap-[3px] mb-[3px] items-center" style={{ gridTemplateColumns: '140px repeat(24, 1fr)' }}>
              <div
                onClick={() => onSelect?.(row.access_point_id)}
                className={`font-mono text-[10px] text-slate-500 truncate pr-2 ${onSelect ? 'cursor-pointer hover:text-rose-500 transition-colors' : ''}`}
              >
                {nameById[row.access_point_id] || row.access_point_id}
              </div>
              {row.hourly_avg_risk.map((score, h) => (
                <div
                  key={h}
                  onMouseEnter={() => setHovered(`${row.access_point_id}-${h}`)}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => onSelect?.(row.access_point_id)}
                  title={`${nameById[row.access_point_id] || row.access_point_id} · ${h}:00 · anomaly score ${score}`}
                  className={`h-4 rounded-[3px] ${riskColor(score)} ${onSelect ? 'cursor-pointer' : ''} transition-all duration-150 ${hovered === `${row.access_point_id}-${h}` ? 'scale-125 ring-2 ring-rose-400/60 shadow-md relative z-10' : 'hover:brightness-110'}`}
                />
              ))}
            </div>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-3 mt-3 font-mono text-[9px] text-slate-500">
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-slate-100 dark:bg-slate-800" /> no activity</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-teal-200 dark:bg-teal-900" /> low</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-teal-400" /> moderate</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-amber-400" /> elevated</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-rose-500" /> high risk</span>
      </div>
    </Card>
  )
}
