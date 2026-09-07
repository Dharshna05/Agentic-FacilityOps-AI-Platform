import Card from '../maintenance/Card'
import { formatINR } from '../../services/costService'

const STATUS_STYLE = {
  over: { bar: 'bg-rose-500', text: 'text-rose-500', label: 'OVER BUDGET' },
  at_risk: { bar: 'bg-amber-500', text: 'text-amber-500', label: 'AT RISK' },
  on_track: { bar: 'bg-teal-500', text: 'text-teal-500', label: 'ON TRACK' },
}

export default function BudgetComplianceList({ compliance }) {
  return (
    <Card title="Budget Compliance" badge="ASSUMPTION-BASED BUDGETS">
      {!compliance?.length && <div className="text-xs text-slate-500 font-mono py-8 text-center">no budget data</div>}
      <div className="flex flex-col gap-3.5 max-h-[420px] overflow-y-auto pr-1">
        {compliance?.map(row => {
          const style = STATUS_STYLE[row.status] || STATUS_STYLE.on_track
          const widthPct = Math.min(row.pct_of_budget, 150) / 1.5
          return (
            <div key={row.category}>
              <div className="flex items-baseline justify-between mb-1">
                <span className="font-mono text-xs text-slate-500">{row.category}</span>
                <span className={`font-mono text-[10px] ${style.text}`}>{style.label} · {row.pct_of_budget}%</span>
              </div>
              <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800/80 overflow-hidden">
                <div className={`h-full rounded-full ${style.bar}`} style={{ width: `${widthPct}%` }} />
              </div>
              <p className="font-mono text-[10px] text-slate-400 mt-1">{formatINR(row.spent_inr)} of {formatINR(row.budget_inr)} this month</p>
            </div>
          )
        })}
      </div>
      <p className="font-body text-[11px] text-slate-500 mt-4 leading-relaxed border-t border-slate-200 dark:border-slate-800 pt-3">
        Budgets are an assumption (1.15x realized average monthly spend for that category) — no real published per-category facility budget exists for this combined real+derived dataset. Treat "over budget" as a trend signal, not a compliance breach.
      </p>
    </Card>
  )
}
