import Card from '../maintenance/Card'

const DOMAIN_META = {
  energy: { label: 'Energy', accent: '#3b82f6' },
  maintenance: { label: 'Maintenance', accent: '#14b8a6' },
  occupancy: { label: 'Occupancy', accent: '#8b5cf6' },
  security: { label: 'Security', accent: '#f43f5e' },
  cost: { label: 'Cost', accent: '#f0a860' },
}

const STATUS_COLOR = {
  Excellent: 'text-teal-500',
  Good: 'text-emerald-500',
  'Needs Attention': 'text-amber-500',
  Critical: 'text-rose-500',
}

export default function FacilityHealthGauge({ health }) {
  if (!health) return null
  const { composite_score, status, subscores } = health

  return (
    <Card title="Facility Health Score" badge="ALL 5 AGENTS, ONE VIEW">
      <div className="flex items-center gap-6 flex-wrap">
        <div className="relative shrink-0 w-32 h-32">
          <svg viewBox="0 0 120 120" className="w-32 h-32 -rotate-90">
            <circle cx="60" cy="60" r="52" stroke="currentColor" strokeWidth="10" fill="none" className="text-slate-100 dark:text-slate-800" />
            <circle
              cx="60" cy="60" r="52" stroke="currentColor" strokeWidth="10" fill="none" strokeLinecap="round"
              strokeDasharray={2 * Math.PI * 52}
              strokeDashoffset={2 * Math.PI * 52 * (1 - composite_score / 100)}
              className={STATUS_COLOR[status] || 'text-teal-500'}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-display text-3xl font-bold text-ink dark:text-slate-50">{composite_score}</span>
            <span className={`font-mono text-[9px] tracking-wide ${STATUS_COLOR[status] || ''}`}>{status.toUpperCase()}</span>
          </div>
        </div>
        <div className="flex-1 min-w-[220px] flex flex-col gap-2.5">
          {Object.entries(subscores).map(([key, value]) => {
            const meta = DOMAIN_META[key]
            return (
              <div key={key}>
                <div className="flex items-center justify-between font-mono text-[10px] text-slate-500 mb-1">
                  <span>{meta.label}</span>
                  <span>{value}</span>
                </div>
                <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${value}%`, backgroundColor: meta.accent }} />
                </div>
              </div>
            )
          })}
        </div>
      </div>
      <p className="font-body text-[11px] text-slate-500 mt-4 leading-relaxed border-t border-slate-200 dark:border-slate-800 pt-3">
        {health.note}
      </p>
    </Card>
  )
}
