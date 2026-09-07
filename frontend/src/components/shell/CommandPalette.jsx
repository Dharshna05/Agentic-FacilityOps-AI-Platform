import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Wrench, UsersRound, ShieldCheck, PoundSterling, Building2, LayoutDashboard, CornerDownLeft, Loader2 } from 'lucide-react'
import { facilityService } from '../../services/costService'

const NAV_SHORTCUTS = [
  { route: '/executive', label: 'Overview', Icon: LayoutDashboard },
  { route: '/energy', label: 'Energy flow', Icon: Building2 },
  { route: '/maintenance', label: 'Asset care', Icon: Wrench },
  { route: '/occupancy', label: 'Space pulse', Icon: UsersRound },
  { route: '/security', label: 'Safety watch', Icon: ShieldCheck },
  { route: '/cost', label: 'Cost watch', Icon: PoundSterling },
]

const DOMAIN_META = {
  maintenance: { Icon: Wrench, className: 'text-teal-500 bg-teal-500/10' },
  occupancy: { Icon: UsersRound, className: 'text-violet-500 bg-violet-500/10' },
  cost: { Icon: PoundSterling, className: 'text-amber-500 bg-amber-500/10' },
  security: { Icon: ShieldCheck, className: 'text-rose-500 bg-rose-500/10' },
  energy: { Icon: Building2, className: 'text-blue-500 bg-blue-500/10' },
}

/**
 * Was a static, non-functional button in every dashboard's header (just a
 * "SEARCH ⌘" pill with no onClick). Now a real Cmd+K-style palette:
 * navigates instantly on nav-name matches, and debounced-queries
 * GET /api/facility/search for real entities (assets, zones, vendors,
 * access points, open alerts) across all five domains, jumping straight
 * to the right dashboard on selection.
 */
export default function CommandPalette({ open, onClose }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)
  const inputRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (open) {
      setQuery('')
      setResults([])
      setActiveIndex(0)
      setTimeout(() => inputRef.current?.focus(), 30)
    }
  }, [open])

  useEffect(() => {
    if (!query.trim()) {
      setResults([])
      return
    }
    setLoading(true)
    const handle = setTimeout(() => {
      facilityService.search(query.trim())
        .then(data => setResults(data.results))
        .catch(() => setResults([]))
        .finally(() => setLoading(false))
    }, 220)
    return () => clearTimeout(handle)
  }, [query])

  const navShortcuts = NAV_SHORTCUTS.filter(n => n.label.toLowerCase().includes(query.trim().toLowerCase()))
  const items = query.trim()
    ? [
        ...navShortcuts.map(n => ({ kind: 'nav', ...n })),
        ...results.map(r => ({ kind: 'entity', ...r })),
      ]
    : NAV_SHORTCUTS.map(n => ({ kind: 'nav', ...n }))

  const select = useCallback((item) => {
    if (!item) return
    navigate(item.route)
    onClose()
  }, [navigate, onClose])

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') { onClose(); return }
    if (e.key === 'ArrowDown') { e.preventDefault(); setActiveIndex(i => Math.min(i + 1, items.length - 1)); return }
    if (e.key === 'ArrowUp') { e.preventDefault(); setActiveIndex(i => Math.max(i - 1, 0)); return }
    if (e.key === 'Enter') { e.preventDefault(); select(items[activeIndex]); }
  }

  if (!open) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-start justify-center pt-[12vh] px-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, y: -12, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -12, scale: 0.98 }}
          transition={{ duration: 0.18 }}
          onClick={(e) => e.stopPropagation()}
          className="w-full max-w-lg bg-white dark:bg-[#15161a] border border-slate-200 dark:border-white/[0.08] rounded-2xl shadow-2xl overflow-hidden"
        >
          <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-200 dark:border-white/[0.06]">
            <Search size={16} className="text-slate-400 shrink-0" />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => { setQuery(e.target.value); setActiveIndex(0) }}
              onKeyDown={handleKeyDown}
              placeholder="Search assets, zones, vendors, access points, alerts…"
              className="flex-1 bg-transparent outline-none text-sm text-ink dark:text-slate-200 placeholder:text-slate-400"
            />
            {loading && <Loader2 size={14} className="animate-spin text-slate-400" />}
          </div>

          <div className="max-h-[50vh] overflow-y-auto py-2">
            {!query.trim() && (
              <div className="px-4 pt-1 pb-2 font-mono text-[9px] tracking-widest text-slate-400">JUMP TO</div>
            )}
            {query.trim() && items.length === 0 && !loading && (
              <div className="px-4 py-6 text-center text-xs text-slate-400 font-body">No matches for "{query}"</div>
            )}
            {items.map((item, i) => {
              const isActive = i === activeIndex
              if (item.kind === 'nav') {
                const Icon = item.Icon
                return (
                  <button
                    key={`nav-${item.route}`}
                    onMouseEnter={() => setActiveIndex(i)}
                    onClick={() => select(item)}
                    className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition ${isActive ? 'bg-slate-100 dark:bg-white/[0.06]' : ''}`}
                  >
                    <span className="grid h-7 w-7 place-items-center rounded-lg bg-slate-100 dark:bg-white/[0.06] text-slate-500 dark:text-slate-400"><Icon size={14} /></span>
                    <span className="flex-1 text-sm text-ink dark:text-slate-200 font-body">{item.label}</span>
                    {isActive && <CornerDownLeft size={12} className="text-slate-400" />}
                  </button>
                )
              }
              const meta = DOMAIN_META[item.domain] || DOMAIN_META.energy
              const Icon = meta.Icon
              return (
                <button
                  key={`${item.domain}-${item.type}-${item.id}`}
                  onMouseEnter={() => setActiveIndex(i)}
                  onClick={() => select(item)}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition ${isActive ? 'bg-slate-100 dark:bg-white/[0.06]' : ''}`}
                >
                  <span className={`grid h-7 w-7 place-items-center rounded-lg shrink-0 ${meta.className}`}><Icon size={14} /></span>
                  <span className="flex-1 min-w-0">
                    <span className="block text-sm text-ink dark:text-slate-200 font-body truncate">{item.label}</span>
                    <span className="block text-[11px] text-slate-400 truncate">{item.subtitle}</span>
                  </span>
                  {isActive && <CornerDownLeft size={12} className="text-slate-400 shrink-0" />}
                </button>
              )
            })}
          </div>

          <div className="flex items-center gap-3 px-4 py-2 border-t border-slate-200 dark:border-white/[0.06] font-mono text-[9px] tracking-wide text-slate-400">
            <span>↑↓ navigate</span><span>↵ open</span><span>esc close</span>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
