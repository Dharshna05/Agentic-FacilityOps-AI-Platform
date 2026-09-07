import { Waves, TreePine, GitBranch } from 'lucide-react'
import Card from '../maintenance/Card'

function MetricBar({ label, value, accent }) {
  const pct = Math.round((value ?? 0) * 100)
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between font-mono text-[10px] text-slate-500">
        <span>{label}</span>
        <span className={accent}>{pct}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
        <div className={`h-full rounded-full ${accent.includes('rose') ? 'bg-rose-500' : accent.includes('violet') ? 'bg-violet-500' : 'bg-teal-500'}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function ModelCard({ title, Icon, data, accent, isPrimary, badgeLabel, badgeClass }) {
  if (!data?.available) return null
  return (
    <div className={`rounded-xl border p-4 flex flex-col gap-3 ${isPrimary ? 'border-rose-400/40 bg-rose-500/[0.04]' : 'border-slate-200 dark:border-slate-800'}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon size={14} className={isPrimary ? 'text-rose-500' : 'text-slate-400'} />
          <h4 className="font-display text-xs font-semibold text-ink dark:text-slate-200">{title}</h4>
        </div>
        {badgeLabel && <span className={`px-2 py-0.5 rounded-full text-[9px] font-mono border ${badgeClass}`}>{badgeLabel}</span>}
      </div>
      <div className="flex flex-col gap-2">
        <MetricBar label="Precision" value={data.precision} accent={isPrimary ? 'text-rose-500' : 'text-teal-500'} />
        <MetricBar label="Recall" value={data.recall} accent={isPrimary ? 'text-rose-500' : 'text-teal-500'} />
        <MetricBar label="F1" value={data.f1} accent={isPrimary ? 'text-rose-500' : 'text-teal-500'} />
      </div>
      {data.detection_rate_by_anomaly_type && (
        <div className="pt-2 border-t border-slate-200 dark:border-slate-800 flex flex-col gap-1">
          {Object.entries(data.detection_rate_by_anomaly_type).map(([type, d]) => (
            <div key={type} className="flex items-center justify-between font-mono text-[9px] text-slate-500">
              <span className="truncate">{type.replace(/_/g, ' ')}</span>
              <span>{Math.round(d.detection_rate * 100)}% of {d.count}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function SecurityModelComparison({ primary, comparison, supervisedReference }) {
  if (!primary?.available && !comparison?.available && !supervisedReference?.available) return null

  return (
    <Card title="Anomaly Detector Comparison" badge="THREE MODELS, ONE HONEST SCORE">
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
        <ModelCard title="Isolation Forest" Icon={TreePine} data={primary} isPrimary badgeLabel="LIVE SCORER" badgeClass="bg-rose-500/10 text-rose-500 border-rose-500/30" />
        <ModelCard title="Local Outlier Factor" Icon={Waves} data={comparison} isPrimary={false} badgeLabel="COMPARISON" badgeClass="bg-slate-500/10 text-slate-400 border-slate-500/30" />
        <ModelCard title="RandomForest (supervised)" Icon={GitBranch} data={supervisedReference} isPrimary={false} badgeLabel="REFERENCE ONLY" badgeClass="bg-violet-500/10 text-violet-500 border-violet-500/30" />
      </div>
      <p className="font-body text-[11px] text-slate-500 mt-3 leading-relaxed">
        Isolation Forest and LOF are both unsupervised — neither ever sees which events are actually anomalous during training;
        precision/recall are computed afterward against injected ground truth, purely to check the method honestly.
        The RandomForest is a different kind of comparison: it's trained WITH the labels (5-fold cross-validated) as an honest
        reference point for how much accuracy the unsupervised constraint costs — not a candidate for live scoring, since a
        real deployment has no labeled incident history to supervise on. Isolation Forest stays the real-time scorer.
      </p>
    </Card>
  )
}
