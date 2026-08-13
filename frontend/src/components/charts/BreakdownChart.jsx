import { useState } from 'react'
import { useTheme } from '../../context/ThemeContext'

const SEGMENTS = [
  { key: 'hvac_pct', label: 'HVAC', colorDark: '#2DD4BF', colorLight: '#0d9488' },
  { key: 'lighting_pct', label: 'Lighting', colorDark: '#3b5f8f', colorLight: '#1e3a5f' },
  { key: 'plug_load_pct', label: 'Plug Load', colorDark: '#38bdf8', colorLight: '#0284c7' },
  { key: 'other_pct', label: 'Other', colorDark: '#64748b', colorLight: '#94a3b8' },
]

/**
 * Custom bar-list (not Recharts) so hover never triggers the default
 * "gray cursor rectangle over the whole row" behavior that made this
 * chart look broken. Hover here just lifts opacity on the row itself —
 * clean, predictable, no overlapping tooltip boxes.
 */
export default function BreakdownChart({ breakdown }) {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const [hovered, setHovered] = useState(null)

  if (!breakdown) return null

  const maxValue = Math.max(...SEGMENTS.map(s => breakdown[s.key] || 0), 1)

  return (
    <div className="bg-paper-raised dark:bg-panel border border-slate-200 dark:border-slate-800 rounded-xl p-5">
      <h3 className="font-display text-sm font-medium text-ink dark:text-slate-200 mb-4">Load Breakdown</h3>
      <div className="flex flex-col gap-3.5">
        {SEGMENTS.map(seg => {
          const value = breakdown[seg.key] || 0
          const widthPct = (value / maxValue) * 100
          const isHovered = hovered === seg.key

          return (
            <div
              key={seg.key}
              className="group cursor-default"
              onMouseEnter={() => setHovered(seg.key)}
              onMouseLeave={() => setHovered(null)}
            >
              <div className="flex items-baseline justify-between mb-1.5">
                <span className={`font-mono text-xs transition-colors ${
                  isHovered ? 'text-ink dark:text-slate-100' : 'text-slate-500 dark:text-slate-400'
                }`}>
                  {seg.label}
                </span>
                <span className={`font-display text-sm font-semibold transition-colors ${
                  isHovered ? 'text-ink dark:text-slate-100' : 'text-slate-600 dark:text-slate-300'
                }`}>
                  {value}%
                </span>
              </div>
              <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800/80 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500 ease-out"
                  style={{
                    width: `${widthPct}%`,
                    backgroundColor: isDark ? seg.colorDark : seg.colorLight,
                    opacity: isHovered ? 1 : 0.85,
                  }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
