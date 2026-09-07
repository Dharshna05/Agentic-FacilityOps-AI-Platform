import { TreePine, Waves, LineChart, GitBranch } from 'lucide-react'
import Card from '../maintenance/Card'
import { formatINR } from '../../services/costService'

function AnomalyModelCard({ title, Icon, data, isPrimary }) {
  if (!data?.available) return null
  const topCategories = data.top_flagged_categories ? Object.entries(data.top_flagged_categories) : []
  return (
    <div className={`rounded-xl border p-4 flex flex-col gap-2 ${isPrimary ? 'border-amber-400/40 bg-amber-500/[0.04]' : 'border-slate-200 dark:border-slate-800'}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon size={14} className={isPrimary ? 'text-amber-500' : 'text-slate-400'} />
          <h4 className="font-display text-xs font-semibold text-ink dark:text-slate-200">{title}</h4>
        </div>
        {isPrimary && <span className="px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-signal text-[9px] font-mono border border-amber-500/30">LIVE SCORER</span>}
      </div>
      <p className="font-mono text-[11px] text-slate-500">{data.pct_flagged}% of invoices flagged ({data.n_flagged ?? '—'})</p>
      <p className="font-mono text-[10px] text-slate-400">Agreement with the other model: {data.agreement_with_lof_pct ?? data.agreement_with_isolation_forest_pct}%</p>
      {isPrimary && data.flagged_total_value_inr != null && (
        <p className="font-mono text-[10px] text-slate-400">Flagged value: {formatINR(data.flagged_total_value_inr)}</p>
      )}
      {!isPrimary && data.both_models_flagged_count != null && (
        <p className="font-mono text-[10px] text-slate-400">{data.both_models_flagged_count} invoices flagged by both models</p>
      )}
      {isPrimary && topCategories.length > 0 && (
        <div className="pt-1.5 mt-0.5 border-t border-amber-500/20 flex flex-col gap-1">
          <span className="font-mono text-[9px] text-slate-400 uppercase tracking-wide">Top flagged categories</span>
          {topCategories.slice(0, 3).map(([cat, count]) => (
            <div key={cat} className="flex items-center justify-between text-[10px]">
              <span className="text-slate-500 dark:text-slate-400 truncate max-w-[70%]">{cat}</span>
              <span className="font-mono text-slate-400">{count}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ForecastModelBar({ name, metrics, best }) {
  if (!metrics) return null
  const isBest = name === best
  const pct = metrics.improvement_over_naive_pct
  return (
    <div className={`rounded-lg border p-3 ${isBest ? 'border-amber-400/40 bg-amber-500/[0.04]' : 'border-slate-200 dark:border-slate-800'}`}>
      <div className="flex items-center justify-between font-mono text-[10px]">
        <span className="text-slate-500">{name}{isBest ? ' (used live)' : ''}</span>
        <span className={pct >= 0 ? 'text-teal-500' : 'text-rose-500'}>{pct >= 0 ? '+' : ''}{pct}% vs naive</span>
      </div>
      <p className="font-mono text-[10px] text-slate-400 mt-1">MAE {formatINR(metrics.held_out_test_mae_inr)}</p>
    </div>
  )
}

export default function CostModelComparison({ anomalyPrimary, anomalyComparison, forecastConfidence }) {
  if (!anomalyPrimary?.available && !forecastConfidence?.available) return null

  return (
    <Card title="Cost Model Comparison" badge="MULTIPLE MODELS, HONEST METRICS">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
        <AnomalyModelCard title="Isolation Forest" Icon={TreePine} data={anomalyPrimary} isPrimary />
        <AnomalyModelCard title="Local Outlier Factor" Icon={Waves} data={anomalyComparison} isPrimary={false} />
      </div>
      {forecastConfidence?.available && (
        <div className="pt-3 border-t border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-2 mb-2">
            <LineChart size={13} className="text-amber-500" />
            <h4 className="font-display text-xs font-semibold text-ink dark:text-slate-200">Spend Trend Forecasters</h4>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {Object.entries(forecastConfidence.all_models || {}).map(([name, m]) => (
              <ForecastModelBar key={name} name={name} metrics={m} best={forecastConfidence.best_model} />
            ))}
          </div>
        </div>
      )}
      <p className="font-body text-[11px] text-slate-500 mt-3 leading-relaxed">
        The real BBMP tenders and derived cross-agent records have no labeled ground truth, so the anomaly detectors are compared
        by flag rate and cross-model agreement, not precision/recall. The forecast models are compared honestly
        against a naive "trend continues" baseline on a held-out tail of real weeks — see each dashboard's
        forecast card for the caveat about only 27 weeks of history.
      </p>
    </Card>
  )
}
