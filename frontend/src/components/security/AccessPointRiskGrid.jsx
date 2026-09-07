import { ShieldAlert, ShieldCheck, Shield } from 'lucide-react'
import Card from '../maintenance/Card'

const RISK_STYLE = {
  high: {
    border: 'border-rose-500/40 dark:border-rose-400/30',
    bg: 'bg-rose-500/[0.06] dark:bg-rose-400/[0.05]',
    text: 'text-rose-600 dark:text-rose-400',
    badge: 'bg-rose-500/10 text-rose-500 border-rose-500/30',
    Icon: ShieldAlert,
  },
  medium: {
    border: 'border-amber-400/40 dark:border-amber-400/30',
    bg: 'bg-amber-400/[0.06] dark:bg-amber-400/[0.05]',
    text: 'text-amber-600 dark:text-amber-400',
    badge: 'bg-amber-400/10 text-amber-500 border-amber-400/30',
    Icon: Shield,
  },
  low: {
    border: 'border-teal-400/40 dark:border-teal-400/30',
    bg: 'bg-teal-400/[0.06] dark:bg-teal-400/[0.05]',
    text: 'text-teal-600 dark:text-teal-400',
    badge: 'bg-teal-400/10 text-teal-500 border-teal-400/30',
    Icon: ShieldCheck,
  },
}

export default function AccessPointRiskGrid({ activity, onSelect }) {
  if (!activity?.length) return null

  const counts = activity.reduce((acc, a) => {
    acc[a.risk_level] = (acc[a.risk_level] || 0) + 1
    return acc
  }, {})

  return (
    <Card title="Access Point Risk Overview" badge={`${activity.length} MONITORED`}>
      <div className="flex items-center gap-4 mb-4 font-mono text-[10px]">
        {['high', 'medium', 'low'].map(level => {
          const s = RISK_STYLE[level]
          return (
            <span key={level} className={`flex items-center gap-1.5 ${s.text}`}>
              <s.Icon size={12} /> {counts[level] || 0} {level}
            </span>
          )
        })}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {activity.map(ap => {
          const s = RISK_STYLE[ap.risk_level] || RISK_STYLE.low
          return (
            <div
              key={ap.access_point_id}
              onClick={() => onSelect?.(ap.access_point_id)}
              className={`rounded-xl border ${s.border} ${s.bg} p-3 flex flex-col gap-2 ${onSelect ? 'cursor-pointer hover:brightness-105 transition-all' : ''}`}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <s.Icon size={14} className={s.text} />
                  <p className="text-sm text-ink dark:text-slate-200 truncate">{ap.name}</p>
                </div>
                <span className={`px-2 py-0.5 rounded-full border text-[9px] font-mono shrink-0 ${s.badge}`}>
                  {ap.risk_level}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2 font-mono text-[9px] text-slate-500">
                <div>
                  <div className="text-slate-400">EVENTS</div>
                  <div className={`text-xs ${s.text} font-semibold`}>{ap.event_count}</div>
                </div>
                <div>
                  <div className="text-slate-400">DENIED</div>
                  <div className="text-xs text-ink dark:text-slate-200 font-semibold">{ap.denied_count}</div>
                </div>
                <div>
                  <div className="text-slate-400">FLAGGED</div>
                  <div className={`text-xs font-semibold ${ap.flagged_count > 0 ? 'text-rose-500' : 'text-ink dark:text-slate-200'}`}>{ap.flagged_count}</div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
