import Card from '../maintenance/Card'

const SEVERITY_STYLE = {
  high: { border: 'border-l-rose-500', badge: 'bg-rose-500/10 text-rose-400 border-rose-500/30', label: 'HIGH' },
  medium: { border: 'border-l-amber-500', badge: 'bg-amber-500/10 text-amber-400 border-amber-500/30', label: 'MEDIUM' },
  low: { border: 'border-l-teal-500', badge: 'bg-teal-500/10 text-teal-400 border-teal-500/30', label: 'LOW' },
}

const CATEGORY_LABEL = {
  overcrowding: 'OVERCROWDING',
  space_optimization: 'SPACE OPTIMIZATION',
  security_handoff: 'SECURITY HANDOFF',
}

export default function OccupancyAlertsList({ alerts }) {
  return (
    <Card title="Occupancy Alerts" badge={`${alerts?.length ?? 0} ACTIVE`}>
      {!alerts?.length && (
        <div className="text-xs text-slate-500 font-mono py-8 text-center">no active alerts</div>
      )}
      <div className="flex flex-col gap-3 max-h-[320px] overflow-y-auto pr-1">
        {alerts?.map((alert) => {
          const style = SEVERITY_STYLE[alert.severity] || SEVERITY_STYLE.low
          return (
            <div key={alert.id} className={`border border-slate-200 dark:border-slate-800 border-l-4 ${style.border} rounded-lg p-3`}>
              <div className="flex justify-between gap-3">
                <div className="min-w-0">
                  <h4 className="text-sm font-medium text-ink dark:text-slate-200 mb-1">{alert.title}</h4>
                  <p className="text-xs text-slate-500 leading-relaxed">{alert.description}</p>
                  <div className="flex flex-wrap gap-3 mt-2 font-mono text-[10px] text-slate-500">
                    <span>{CATEGORY_LABEL[alert.category] || alert.category}</span>
                    {alert.zone_id && <span>Zone: {alert.zone_id}</span>}
                  </div>
                </div>
                <span className={`h-fit px-2 py-1 rounded border text-[10px] font-mono ${style.badge}`}>{style.label}</span>
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
