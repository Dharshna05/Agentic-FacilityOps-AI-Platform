export default function BriefingCard({ briefing }) {
  if (!briefing) return null

  const isFallback = /call failed|unavailable/i.test(briefing.provider || '')
  const badgeClass = isFallback
    ? 'text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-500/10 border border-rose-400/40'
    : 'text-slate-500 bg-slate-100 dark:bg-slate-800'

  return (
    <div className="bg-paper-raised dark:bg-panel border border-teal-200 dark:border-teal-900/40 rounded-xl p-5">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-display text-sm font-medium text-ink dark:text-slate-200">AI Briefing</h3>
        <span
          title={isFallback ? 'The configured real provider failed at runtime and this fell back to a mock response — see the note at the end of the briefing.' : undefined}
          className={`text-[10px] uppercase tracking-wide px-2 py-0.5 rounded ${badgeClass}`}
        >
          {isFallback ? '⚠ fallback: mock' : briefing.provider}
        </span>
      </div>
      <p className="text-xs text-slate-600 dark:text-slate-400 whitespace-pre-line leading-relaxed">
        {briefing.briefing}
      </p>
    </div>
  )
}
