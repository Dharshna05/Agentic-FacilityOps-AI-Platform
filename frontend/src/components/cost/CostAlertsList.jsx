import Card from '../maintenance/Card'

const SEVERITY_STYLE = {
  high: { border: 'border-l-rose-500', badge: 'bg-rose-500/10 text-rose-400 border-rose-500/30', label: 'HIGH' },
  medium: { border: 'border-l-amber-500', badge: 'bg-amber-500/10 text-amber-400 border-amber-500/30', label: 'MEDIUM' },
  low: { border: 'border-l-teal-500', badge: 'bg-teal-500/10 text-teal-400 border-teal-500/30', label: 'LOW' },
}

export default function CostAlertsList({ alerts }) {
  return (
    <Card title="Cost Alerts" badge={`${alerts?.length ?? 0} TOTAL`}>
      {!alerts?.length && <div className="text-xs text-slate-500 font-mono py-8 text-center">no alerts yet — run an investigation to generate some</div>}
      <div className="flex flex-col gap-3 max-h-[360px] overflow-y-auto pr-1">
        {alerts?.map(alert => {
          const style = SEVERITY_STYLE[alert.severity] || SEVERITY_STYLE.low
          return (
            <div key={alert.id} className={`border border-l-4 ${style.border} border-slate-200 dark:border-slate-800 rounded-lg p-3`}>
              <div className="flex items-start justify-between gap-3 mb-2">
                <span className="px-2 py-0.5 rounded-full border text-[9px] font-mono tracking-widest bg-slate-500/10 text-slate-400 border-slate-500/30">{alert.alert_type.replace(/_/g, ' ').toUpperCase()}</span>
                <span className={`h-fit px-2 py-1 rounded border text-[10px] font-mono ${style.badge}`}>{style.label}</span>
              </div>
              <p className="text-sm text-ink dark:text-slate-200 leading-relaxed">{alert.description}</p>
              <div className="flex flex-wrap gap-4 mt-2 font-mono text-[10px] text-slate-500">
                {alert.category && <span>Category: {alert.category}</span>}
                {alert.vendor_id && <span>Vendor: {alert.vendor_id}</span>}
                <span>{new Date(alert.created_at).toLocaleString()}</span>
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
