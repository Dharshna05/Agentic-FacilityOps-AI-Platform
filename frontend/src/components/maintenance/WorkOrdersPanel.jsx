import Card from './Card'

const STATUS_STYLE = {
  open: { badge: 'bg-rose-500/10 text-rose-400 border-rose-500/30' },
  resolved: { badge: 'bg-teal-500/10 text-teal-400 border-teal-500/30' },
}

const SEVERITY_STYLE = {
  high: 'border-l-rose-500',
  medium: 'border-l-amber-500',
  low: 'border-l-teal-500',
}

// Cross-agent handoff work orders (source === 'energy_agent') are the
// project's headline feature — an energy anomaly triggering a real
// maintenance work order on an HVAC asset. These must stand out visually.
const SOURCE_LABEL = {
  energy_agent: { label: 'ENERGY AGENT → HANDOFF', className: 'bg-teal-500/15 text-teal-300 border-teal-400/40' },
  maintenance_agent: { label: 'MAINTENANCE AGENT', className: 'bg-slate-500/10 text-slate-400 border-slate-500/30' },
  rule_engine: { label: 'RULE ENGINE', className: 'bg-slate-500/10 text-slate-400 border-slate-500/30' },
}

export default function WorkOrdersPanel({ workOrders, onSelect }) {
  return (
    <Card title="Work Orders" badge={`${workOrders?.length ?? 0} TOTAL`}>
      {!workOrders?.length && (
        <div className="text-xs text-slate-500 font-mono py-8 text-center">
          no work orders available
        </div>
      )}

      <div className="flex flex-col gap-3 max-h-[320px] overflow-y-auto pr-1">
        {workOrders?.map((order) => {
          const isHandoff = order.source === 'energy_agent'
          const sourceMeta = SOURCE_LABEL[order.source] || SOURCE_LABEL.maintenance_agent
          const severityBorder = SEVERITY_STYLE[order.severity] || SEVERITY_STYLE.low

          return (
            <div
              key={order.id}
              onClick={() => onSelect?.(order.asset_id)}
              className={`
                border border-l-4 ${severityBorder}
                rounded-lg p-3 transition-colors ${onSelect ? 'cursor-pointer' : ''}
                ${isHandoff
                  ? 'border-teal-400/50 bg-teal-500/5 shadow-[0_0_0_1px_rgba(45,212,191,0.15)] hover:bg-teal-500/10'
                  : 'border-slate-200 dark:border-slate-800 hover:border-teal-500/30 hover:bg-slate-50 dark:hover:bg-slate-900/40'}
              `}
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <span
                  className={`px-2 py-0.5 rounded-full border text-[9px] font-mono tracking-widest ${sourceMeta.className}`}
                >
                  {sourceMeta.label}
                </span>

                <span
                  className={`h-fit px-2 py-1 rounded border text-[10px] font-mono uppercase ${
                    STATUS_STYLE[order.status]?.badge || STATUS_STYLE.open.badge
                  }`}
                >
                  {order.status}
                </span>
              </div>

              <p className="text-sm text-ink dark:text-slate-200 leading-relaxed">
                {order.reason}
              </p>

              <div className="flex flex-wrap gap-4 mt-2 font-mono text-[10px] text-slate-500">
                <span className={onSelect ? 'text-teal-600 dark:text-teal-400' : ''}>
                  Asset: {order.asset_id}{onSelect && ' →'}
                </span>
                <span className="uppercase">{order.severity} severity</span>
                {order.created_at && (
                  <span>Created: {new Date(order.created_at).toLocaleDateString()}</span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
