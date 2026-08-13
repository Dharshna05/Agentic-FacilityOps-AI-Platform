export default function BriefingCard({ briefing }) {
  if (!briefing) return null

  return (
    <div className="bg-paper-raised dark:bg-panel border border-teal-200 dark:border-teal-900/40 rounded-xl p-5">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-display text-sm font-medium text-ink dark:text-slate-200">AI Briefing</h3>
        <span className="text-[10px] uppercase tracking-wide text-slate-500 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
          {briefing.provider}
        </span>
      </div>
      <p className="text-xs text-slate-600 dark:text-slate-400 whitespace-pre-line leading-relaxed">
        {briefing.briefing}
      </p>
    </div>
  )
}
