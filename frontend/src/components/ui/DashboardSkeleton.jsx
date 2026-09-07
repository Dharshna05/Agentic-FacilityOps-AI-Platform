const COLS_CLASS = { 2: 'lg:grid-cols-2', 3: 'lg:grid-cols-3', 4: 'lg:grid-cols-4', 5: 'lg:grid-cols-5' }

function Bar({ className = '' }) {
  return (
    <div
      className={`rounded-lg bg-[linear-gradient(90deg,rgba(148,163,184,0.12)_0%,rgba(148,163,184,0.28)_50%,rgba(148,163,184,0.12)_100%)] dark:bg-[linear-gradient(90deg,rgba(255,255,255,0.04)_0%,rgba(255,255,255,0.1)_50%,rgba(255,255,255,0.04)_100%)] bg-[length:800px_100%] animate-shimmer ${className}`}
    />
  )
}

/**
 * Every dashboard's initial load previously showed nothing but centered
 * pulsing text ("SCANNING BUILDING ZONES…" etc.) on a blank page — this
 * gives that same wait a visible shape of the page that's about to
 * render (KPI row + two content panels), which reads as faster and more
 * polished even though the actual load time is unchanged. `message` keeps
 * each dashboard's own themed loading copy front and center.
 */
export default function DashboardSkeleton({ message = 'LOADING…', kpiCount = 4 }) {
  return (
    <div className="p-4 sm:p-6 lg:p-8 flex flex-col gap-5">
      <div className="flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse-line" />
        <span className="font-mono text-[11px] tracking-widest text-slate-500">{message}</span>
      </div>

      <div className={`grid grid-cols-2 ${COLS_CLASS[Math.min(kpiCount, 5)] || COLS_CLASS[4]} gap-4`}>
        {Array.from({ length: kpiCount }).map((_, i) => (
          <div key={i} className="min-h-[142px] rounded-[1.35rem] border border-slate-200/70 dark:border-white/[0.06] p-5 flex flex-col gap-4">
            <Bar className="h-3 w-2/3" />
            <Bar className="h-8 w-1/2" />
            <Bar className="h-2 w-1/3" />
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-[1.35rem] border border-slate-200/70 dark:border-white/[0.06] p-5 h-64 flex flex-col gap-3">
          <Bar className="h-3 w-1/3" />
          <Bar className="flex-1 w-full" />
        </div>
        <div className="rounded-[1.35rem] border border-slate-200/70 dark:border-white/[0.06] p-5 h-64 flex flex-col gap-3">
          <Bar className="h-3 w-1/3" />
          {Array.from({ length: 4 }).map((_, i) => (
            <Bar key={i} className="h-9 w-full" />
          ))}
        </div>
      </div>
    </div>
  )
}
