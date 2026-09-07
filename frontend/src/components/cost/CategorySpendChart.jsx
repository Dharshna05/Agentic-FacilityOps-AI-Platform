import { useState } from 'react'
import { formatINR } from '../../services/costService'

const PALETTE = ['#f0a860', '#2DD4BF', '#3b82f6', '#8b5cf6', '#f43f5e', '#10b981', '#64748b', '#eab308', '#0ea5e9']

export default function CategorySpendChart({ breakdown }) {
  const [hovered, setHovered] = useState(null)
  if (!breakdown?.length) return null
  const max = Math.max(...breakdown.map(b => b.spend_inr), 1)

  return (
    <div className="bg-paper-raised dark:bg-panel border border-slate-200 dark:border-slate-800 rounded-xl p-5">
      <h3 className="font-display text-sm font-medium text-ink dark:text-slate-200 mb-4">Spend by Category</h3>
      <div className="flex flex-col gap-3.5">
        {breakdown.map((row, i) => {
          const widthPct = (row.spend_inr / max) * 100
          const isHovered = hovered === row.category
          return (
            <div key={row.category} className="group cursor-default" onMouseEnter={() => setHovered(row.category)} onMouseLeave={() => setHovered(null)}>
              <div className="flex items-baseline justify-between mb-1.5">
                <span className={`font-mono text-xs transition-colors ${isHovered ? 'text-ink dark:text-slate-100' : 'text-slate-500 dark:text-slate-400'}`}>{row.category}</span>
                <span className={`font-display text-sm font-semibold transition-colors ${isHovered ? 'text-ink dark:text-slate-100' : 'text-slate-600 dark:text-slate-300'}`}>
                  {formatINR(row.spend_inr)} <span className="text-slate-400 font-mono text-[10px]">({row.pct_of_total}%)</span>
                </span>
              </div>
              <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800/80 overflow-hidden">
                <div className="h-full rounded-full transition-all duration-500 ease-out" style={{ width: `${widthPct}%`, backgroundColor: PALETTE[i % PALETTE.length], opacity: isHovered ? 1 : 0.85 }} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
