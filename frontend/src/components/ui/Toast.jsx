import { useEffect } from 'react'

const VARIANT_STYLE = {
  info: 'border-teal-500/40 bg-teal-50 dark:bg-teal-400/10 text-teal-700 dark:text-teal-300',
  success: 'border-emerald-500/40 bg-emerald-50 dark:bg-emerald-400/10 text-emerald-700 dark:text-emerald-300',
  warning: 'border-amber-500/40 bg-amber-50 dark:bg-amber-400/10 text-amber-700 dark:text-signal',
}

export default function Toast({ message, variant = 'info', onDismiss, duration = 4500 }) {
  useEffect(() => {
    if (!message) return
    const t = setTimeout(onDismiss, duration)
    return () => clearTimeout(t)
  }, [message, duration, onDismiss])

  if (!message) return null

  return (
    <div className="fixed bottom-5 right-5 z-[60] animate-fade-in">
      <div className={`flex items-center gap-2.5 px-4 py-3 rounded-xl border shadow-xl font-mono text-xs backdrop-blur-sm ${VARIANT_STYLE[variant] || VARIANT_STYLE.info}`}>
        <span className="w-1.5 h-1.5 rounded-full bg-current shrink-0" />
        <span>{message}</span>
        <button onClick={onDismiss} className="ml-1 opacity-60 hover:opacity-100 transition-opacity">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  )
}
