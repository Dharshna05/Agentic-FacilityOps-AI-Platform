import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Bell } from 'lucide-react'
import { facilityService } from '../../services/costService'

const DOMAIN_ROUTE = { maintenance: '/maintenance', security: '/security', cost: '/cost' }
const SEVERITY_DOT = { high: 'bg-rose-500', medium: 'bg-amber-500', low: 'bg-teal-500' }

/**
 * Was a purely decorative bell icon with no data behind it. Now polls the
 * same unified alert feed the Executive Overview page already shows
 * (GET /api/facility/alerts) so every dashboard's header carries a live
 * open-alert count, not just the Overview page — and clicking an alert
 * jumps straight to the domain dashboard it came from.
 */
export default function NotificationBell() {
  const [open, setOpen] = useState(false)
  const [alerts, setAlerts] = useState([])
  const [totalOpen, setTotalOpen] = useState(0)
  const ref = useRef(null)
  const navigate = useNavigate()

  const refresh = useCallback(() => {
    facilityService.getAlerts()
      .then(data => {
        setAlerts(data.alerts || [])
        setTotalOpen(data.total_open ?? (data.alerts || []).length)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 45000)
    return () => clearInterval(interval)
  }, [refresh])

  useEffect(() => {
    const onClickOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  const goTo = (alert) => {
    setOpen(false)
    const route = DOMAIN_ROUTE[alert.domain]
    if (route) navigate(route)
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => { setOpen(o => !o); if (!open) refresh() }}
        className="grid h-9 w-9 place-items-center rounded-full border border-slate-200 bg-white text-slate-500 transition hover:-translate-y-0.5 hover:shadow-sm dark:border-white/[0.08] dark:bg-white/[0.04] relative"
      >
        <Bell size={15} />
        {totalOpen > 0 && (
          <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-full bg-rose-500 text-white text-[9px] font-mono font-bold flex items-center justify-center">
            {totalOpen > 9 ? '9+' : totalOpen}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.97 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-11 w-80 max-h-96 overflow-y-auto bg-white dark:bg-[#15161a] border border-slate-200 dark:border-white/[0.08] rounded-xl shadow-2xl z-50"
          >
            <div className="px-4 py-2.5 border-b border-slate-200 dark:border-white/[0.06] flex items-center justify-between">
              <span className="font-display text-xs font-semibold text-ink dark:text-slate-200">Open Alerts</span>
              <span className="font-mono text-[10px] text-slate-400">{totalOpen} total</span>
            </div>
            {alerts.length === 0 && (
              <div className="px-4 py-8 text-center text-xs text-slate-400 font-mono">No open alerts — all clear.</div>
            )}
            {alerts.slice(0, 8).map((a, i) => (
              <button
                key={`${a.domain}-${a.id}-${i}`}
                onClick={() => goTo(a)}
                className="w-full text-left px-4 py-2.5 border-b border-slate-100 dark:border-white/[0.04] last:border-0 hover:bg-slate-50 dark:hover:bg-white/[0.04] transition flex items-start gap-2.5"
              >
                <span className={`mt-1.5 w-1.5 h-1.5 rounded-full shrink-0 ${SEVERITY_DOT[a.severity] || 'bg-slate-400'}`} />
                <span className="min-w-0 flex-1">
                  <span className="block text-xs text-ink dark:text-slate-200 font-body truncate">{a.title || a.description}</span>
                  <span className="block text-[10px] text-slate-400 font-mono uppercase mt-0.5">{a.domain}</span>
                </span>
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
