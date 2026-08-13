const SEVERITY_STYLE = {
  high: 'border-red-300 dark:border-red-500/40 bg-red-50 dark:bg-red-500/5 text-red-700 dark:text-red-300',
  medium: 'border-amber-300 dark:border-amber-500/40 bg-amber-50 dark:bg-amber-500/5 text-amber-700 dark:text-amber-300',
  low: 'border-teal-300 dark:border-teal-500/40 bg-teal-50 dark:bg-teal-500/5 text-teal-700 dark:text-teal-300',
}

export default function RecommendationsList({ recommendations }) {
  if (!recommendations?.length) {
    return (
      <div className="bg-paper-raised dark:bg-panel border border-slate-200 dark:border-slate-800 rounded-xl p-5 text-sm text-slate-500">
        No recommendations right now — consumption patterns look healthy.
      </div>
    )
  }

  return (
    <div className="bg-paper-raised dark:bg-panel border border-slate-200 dark:border-slate-800 rounded-xl p-5">
      <h3 className="font-display text-sm font-medium text-ink dark:text-slate-200 mb-3">Efficiency Recommendations</h3>
      <div className="flex flex-col gap-3">
        {recommendations.map(rec => (
          <div key={rec.id} className={`border rounded-lg p-3.5 ${SEVERITY_STYLE[rec.severity]}`}>
            <div className="flex items-center justify-between">
              <span className="font-medium text-sm">{rec.title}</span>
              <span className="font-mono text-[10px] uppercase tracking-wide">
                ~{rec.estimated_savings_pct}% savings
              </span>
            </div>
            <p className="text-xs opacity-80 mt-1">{rec.description}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
