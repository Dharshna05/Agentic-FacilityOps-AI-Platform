import Card from '../maintenance/Card'

const RISK_STYLE = {
  high: 'border-l-rose-500',
  medium: 'border-l-amber-500',
  low: 'border-l-teal-500',
}

function scoreColor(score) {
  if (score >= 0.75) return 'text-rose-500'
  if (score >= 0.6) return 'text-amber-500'
  return 'text-slate-400'
}

export default function FlaggedEventsList({ events }) {
  return (
    <Card title="Flagged Events" badge="ANOMALY DETECTOR">
      {!events?.length && (
        <div className="text-xs text-slate-500 font-mono py-8 text-center">no flagged events</div>
      )}
      <div className="flex flex-col gap-2 max-h-[420px] overflow-y-auto pr-1">
        {events?.map((ev, index) => (
          <div key={ev.event_id} className={`group border border-slate-200 dark:border-slate-800 border-l-4 ${RISK_STYLE[ev.risk_level] || ''} rounded-xl px-3 py-3 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md hover:border-rose-400/30`}>
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm text-ink dark:text-slate-200 flex items-center gap-2">
                  <span className={`w-1.5 h-1.5 rounded-full ${RISK_STYLE[ev.risk_level] === 'border-l-rose-500' ? 'bg-rose-500' : RISK_STYLE[ev.risk_level] === 'border-l-amber-500' ? 'bg-amber-400' : 'bg-teal-400'}`} />
                  {ev.employee_id} <span className="text-slate-400">·</span> {ev.access_point_id}
                </p>
                <p className="font-mono text-[10px] text-slate-500 mt-0.5">
                  {new Date(ev.timestamp).toLocaleString()} · {ev.access_granted ? 'granted' : 'DENIED'} · risk: {ev.risk_level}
                </p>
              </div>
              <span className={`shrink-0 font-mono text-xs font-medium ${scoreColor(ev.anomaly_score)}`}>
                {ev.anomaly_score.toFixed(2)}
              </span>
            </div>
            <div className="mt-2 flex justify-between font-mono text-[9px] tracking-wider text-slate-400"><span>EVENT {String(index + 1).padStart(2, '0')}</span><span className="opacity-0 transition-opacity group-hover:opacity-100">REVIEW SIGNAL →</span></div>
          </div>
        ))}
      </div>
    </Card>
  )
}
