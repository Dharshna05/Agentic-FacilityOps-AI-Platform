const STATUS_COLOR = {
  Critical: '#f43f5e',
  Warning: '#f59e0b',
  Excellent: '#10b981',
  Good: '#2dd4bf',
}

// Surfaces the fleet's own `risk_ranking` (already computed server-side,
// lowest health first) as a horizontally-scrollable strip of spotlight
// cards. With 100 assets in the table below, the 3-5 that actually need a
// human's attention right now can get lost — this puts them front and
// center, one click from the detail panel, before any scrolling or
// filtering is needed.
export default function CriticalAssetsSpotlight({ riskRanking, onSelect, selectedAssetId }) {
  const top = (riskRanking || []).slice(0, 5)
  if (!top.length) return null

  const worst = top[0]
  if (worst.status !== 'Critical' && worst.status !== 'Warning') return null

  return (
    <div>
      <div className="flex items-center gap-2 mb-2.5">
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75 animate-ping" />
          <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-rose-500" />
        </span>
        <h3 className="font-mono text-[10px] tracking-widest text-slate-500">NEEDS ATTENTION FIRST</h3>
      </div>

      <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1">
        {top
          .filter((a) => a.status === 'Critical' || a.status === 'Warning')
          .map((asset) => {
            const color = STATUS_COLOR[asset.status] || '#94a3b8'
            const isSelected = selectedAssetId === asset.asset_id
            return (
              <button
                key={asset.asset_id}
                onClick={() => onSelect(asset.asset_id)}
                className={`shrink-0 w-[210px] text-left rounded-2xl border p-3.5 transition-all duration-200 hover:-translate-y-1
                  bg-paper-raised dark:bg-panel hover:border-teal-500/40 hover:shadow-lg
                  ${isSelected ? 'ring-2 ring-teal-500/50 border-teal-500/40' : 'border-slate-200 dark:border-slate-800'}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span
                    className="px-2 py-0.5 rounded-full border text-[9px] font-mono tracking-widest"
                    style={{ color, borderColor: `${color}50`, backgroundColor: `${color}15` }}
                  >
                    {asset.status}
                  </span>
                  <span className="font-mono text-[10px] text-slate-400">{asset.health_score}%</span>
                </div>
                <p className="text-sm font-medium text-ink dark:text-slate-200 truncate">{asset.name}</p>
                <p className="font-mono text-[10px] text-slate-500 mt-0.5">{asset.asset_type}</p>
                <p className="font-mono text-[10px] text-slate-500 mt-1.5">
                  RUL ~{asset.predicted_rul_cycles}d
                  {asset.rul_lower_cycles != null && ` (${asset.rul_lower_cycles}-${asset.rul_upper_cycles})`}
                </p>
              </button>
            )
          })}
      </div>
    </div>
  )
}
