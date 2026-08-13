import { useEffect, useState } from 'react'

function timeAgo(date) {
  if (!date) return '—'
  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000))
  if (seconds < 5) return 'just now'
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ago`
}

/**
 * Shows a pulsing LIVE dot, a self-updating "Updated Xs ago" label, and a
 * manual refresh control. Data itself is polled by the parent page (see
 * `usePolling` in each dashboard); this component only renders the status.
 */
export default function LiveIndicator({ lastUpdated, isRefreshing, onRefresh }) {
  const [, tick] = useState(0)

  useEffect(() => {
    const id = setInterval(() => tick((n) => n + 1), 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2">
        <span className="relative flex h-2 w-2">
          <span
            className={`absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75 ${
              isRefreshing ? 'animate-ping' : 'animate-pulse-line'
            }`}
          />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-teal-500 dark:bg-teal-400" />
        </span>
        <span className="font-mono text-[10px] tracking-[0.2em] text-teal-600 dark:text-teal-400/80">
          LIVE
        </span>
      </div>

      <span className="font-mono text-[10px] text-slate-400 dark:text-slate-600">
        {isRefreshing ? 'syncing…' : `updated ${timeAgo(lastUpdated)}`}
      </span>

      <button
        onClick={onRefresh}
        disabled={isRefreshing}
        title="Refresh now"
        className="text-slate-400 hover:text-teal-500 dark:text-slate-600 dark:hover:text-teal-400
                   transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="13" height="13" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
          className={isRefreshing ? 'animate-spin' : ''}
        >
          <path d="M21 12a9 9 0 1 1-2.64-6.36" />
          <path d="M21 3v6h-6" />
        </svg>
      </button>
    </div>
  )
}
