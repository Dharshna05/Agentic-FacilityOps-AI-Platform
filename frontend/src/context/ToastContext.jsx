import { createContext, useContext, useState, useCallback, useRef } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { CheckCircle2, AlertTriangle, Info, X } from 'lucide-react'

const ToastContext = createContext(null)

const VARIANT = {
  success: { className: 'border-emerald-500/40 bg-emerald-50 dark:bg-emerald-400/10 text-emerald-700 dark:text-emerald-300', Icon: CheckCircle2 },
  error: { className: 'border-rose-500/40 bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-300', Icon: AlertTriangle },
  info: { className: 'border-teal-500/40 bg-teal-50 dark:bg-teal-400/10 text-teal-700 dark:text-teal-300', Icon: Info },
}

/**
 * Global, stacked toast notifications — before this, only the Maintenance
 * dashboard had a (page-local, single-message) Toast component; every
 * other action across the app (login, logout, add/delete a record, an
 * investigation completing or failing, a search with no results) gave no
 * feedback at all beyond whatever inline UI happened to update. Mounted
 * once in AppShell; any component calls useToast().show(...) directly.
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const idRef = useRef(0)

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const show = useCallback((message, variant = 'info', duration = 4000) => {
    const id = ++idRef.current
    setToasts((prev) => [...prev, { id, message, variant }])
    setTimeout(() => dismiss(id), duration)
    return id
  }, [dismiss])

  return (
    <ToastContext.Provider value={{ show }}>
      {children}
      <div className="fixed bottom-5 right-5 z-[100] flex flex-col gap-2 items-end pointer-events-none">
        <AnimatePresence>
          {toasts.map((t) => {
            const meta = VARIANT[t.variant] || VARIANT.info
            const Icon = meta.Icon
            return (
              <motion.div
                key={t.id}
                initial={{ opacity: 0, x: 24, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: 24, scale: 0.95 }}
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                className={`pointer-events-auto flex items-center gap-2.5 px-4 py-3 rounded-xl border shadow-xl font-mono text-xs backdrop-blur-sm max-w-sm ${meta.className}`}
              >
                <Icon size={14} className="shrink-0" />
                <span className="leading-snug">{t.message}</span>
                <button onClick={() => dismiss(t.id)} className="ml-1 opacity-60 hover:opacity-100 transition-opacity shrink-0">
                  <X size={12} />
                </button>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    // Fail soft rather than crashing a page that forgot the provider is
    // mounted higher up — a no-op show() is safer than a hard error for
    // a purely cosmetic feature.
    return { show: () => {} }
  }
  return ctx
}
