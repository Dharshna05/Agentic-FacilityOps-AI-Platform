import Card from '../maintenance/Card'

const STATUS_STYLE = {
  Overcrowded: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
  Busy: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  Moderate: 'bg-teal-500/10 text-teal-400 border-teal-500/30',
  Low: 'bg-slate-500/10 text-slate-400 border-slate-500/30',
}

const BAR_COLOR = (pct) => pct >= 90 ? 'bg-rose-500' : pct >= 70 ? 'bg-amber-400' : pct >= 40 ? 'bg-teal-400' : 'bg-slate-400'

export default function ZoneTable({ zones, onSelect, selectedZoneId }) {
  return (
    <Card title="Zones" badge={`${zones?.length ?? 0} TOTAL`}>
      <div className="flex flex-col gap-2 max-h-[420px] overflow-y-auto pr-1">
        {zones?.map(z => (
          <div
            key={z.zone_id}
            onClick={() => onSelect?.(z.zone_id)}
            className={`flex items-center gap-3 border rounded-xl px-3 py-2.5 cursor-pointer transition-all duration-200
                        border-slate-200 dark:border-slate-800 hover:-translate-y-0.5 hover:bg-violet-50 dark:hover:bg-violet-500/10 hover:border-violet-400/40 hover:shadow-md
                        ${selectedZoneId === z.zone_id ? 'bg-violet-500/10 dark:bg-violet-400/10 border-violet-500/40' : ''}`}
          >
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-ink dark:text-slate-200 truncate">{z.name}</p>
              <p className="font-mono text-[10px] text-slate-500">{z.zone_type.replace(/_/g, ' ')} · {z.current_headcount}/{z.capacity} people</p>
            </div>
            <div className="w-24 shrink-0">
              <div className="h-1.5 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                <div className={`h-full rounded-full ${BAR_COLOR(z.current_utilization_pct)}`} style={{ width: `${z.current_utilization_pct}%` }} />
              </div>
            </div>
            <span className={`shrink-0 px-2 py-1 rounded-full border text-[10px] font-mono ${STATUS_STYLE[z.status] || ''}`}>
              {z.status}
            </span>
          </div>
        ))}
      </div>
    </Card>
  )
}
