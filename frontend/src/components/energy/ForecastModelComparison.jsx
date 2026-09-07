import { useEffect, useState } from 'react'
import { GitCompareArrows } from 'lucide-react'
import Card from '../maintenance/Card'
import { energyService } from '../../services/energyService'

const MODEL_LABELS = {
  linear_regression: 'Linear Regression',
  random_forest: 'Random Forest',
  gradient_boosting: 'Gradient Boosting',
}

export default function ForecastModelComparison({ horizon }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    let cancelled = false
    energyService.getForecastModelComparison(horizon).then(d => { if (!cancelled) setData(d) }).catch(() => setData(null))
    return () => { cancelled = true }
  }, [horizon])

  if (!data?.available) return null

  const entries = Object.entries(data.models)
  const maxMae = Math.max(...entries.map(([, m]) => m.held_out_test_mae_kwh))

  return (
    <Card title="Forecast Model Comparison" badge={`HORIZON: ${horizon.toUpperCase()}`}>
      <div className="flex flex-col gap-2.5">
        {entries.map(([name, m]) => {
          const isBest = name === data.best_model
          const barPct = Math.round((m.held_out_test_mae_kwh / maxMae) * 100)
          return (
            <div key={name} className={`rounded-lg border p-3 ${isBest ? 'border-blue-400/40 bg-blue-500/[0.04]' : 'border-slate-200 dark:border-slate-800'}`}>
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-mono text-xs text-ink dark:text-slate-200">{MODEL_LABELS[name] || name}</span>
                {isBest && <span className="px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-500 text-[9px] font-mono border border-blue-500/30">BEST — LIVE MODEL</span>}
              </div>
              <div className="flex items-center gap-3">
                <div className="flex-1 h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                  <div className={`h-full rounded-full ${isBest ? 'bg-blue-500' : 'bg-slate-400'}`} style={{ width: `${barPct}%` }} />
                </div>
                <span className="font-mono text-[10px] text-slate-500 w-24 text-right">MAE {m.held_out_test_mae_kwh} kWh</span>
                <span className="font-mono text-[10px] text-slate-500 w-16 text-right">R² {m.held_out_test_r2}</span>
              </div>
            </div>
          )
        })}
      </div>
      <p className="font-body text-[11px] text-slate-500 mt-3">
        Naive baselines for comparison: predicting "no change" gives {data.naive_flat_mae_kwh} kWh MAE;
        predicting "same as this time yesterday" gives {data.naive_daily_mae_kwh} kWh MAE. Lower MAE is better — all 3 models are trained
        and evaluated fresh for this horizon, the winner isn't fixed in advance.
      </p>
    </Card>
  )
}
