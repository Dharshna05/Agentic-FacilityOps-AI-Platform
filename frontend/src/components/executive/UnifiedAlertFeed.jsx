import Card from '../maintenance/Card'

const DOMAIN_BADGE = {
  maintenance: { label: 'MAINTENANCE', className: 'bg-teal-500/10 text-teal-400 border-teal-500/30' },
  security: { label: 'SECURITY', className: 'bg-rose-500/10 text-rose-400 border-rose-500/30' },
  cost: { label: 'COST', className: 'bg-amber-500/10 text-amber-600 dark:text-signal border-amber-500/30' },
}
const SEVERITY_STYLE = {
  high: 'border-l-rose-500',
  medium: 'border-l-amber-500',
  low: 'border-l-teal-500',
}

export default function UnifiedAlertFeed({ alerts, totalOpen }) {
  return (
    <Card title="Unified Alert Feed" badge={`${totalOpen ?? 0} OPEN`}>
      {!alerts?.length && <div className="text-xs text-slate-500 font-mono py-8 text-center">no open alerts across any agent</div>}
      <div className="flex flex-col gap-2.5 max-h-[440px] overflow-y-auto pr-1">
        {alerts?.map((a, i) => {
          const domain = DOMAIN_BADGE[a.domain] || DOMAIN_BADGE.cost
          return (
            <div key={`${a.domain}-${a.id}-${i}`} className={`border border-l-4 ${SEVERITY_STYLE[a.severity] || 'border-l-slate-400'} border-slate-200 dark:border-slate-800 rounded-lg p-3`}>
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <span className={`px-2 py-0.5 rounded-full border text-[9px] font-mono tracking-widest ${domain.className}`}>{domain.label}</span>
                <span className="font-mono text-[10px] text-slate-400">{a.created_at ? new Date(a.created_at).toLocaleDateString() : ''}</span>
              </div>
              <p className="text-sm text-ink dark:text-slate-200 leading-relaxed">{a.title || a.description}</p>
              {a.title && a.description && a.title !== a.description && (
                <p className="text-xs text-slate-500 mt-1">{a.description}</p>
              )}
            </div>
          )
        })}
      </div>
    </Card>
  )
}
