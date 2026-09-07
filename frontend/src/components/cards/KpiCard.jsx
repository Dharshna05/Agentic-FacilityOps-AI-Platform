import { motion } from 'framer-motion'
import AnimatedNumber from '../ui/AnimatedNumber'

// Light mode: saturated pastel fills (intelly-style) — bright enough to read as
// color-coded cards, not just tinted white. Dark mode: near-black panel + a soft
// colored glow instead of a flat fill, matching a neon-on-charcoal dashboard feel.
const ACCENT_STYLES = {
  teal:    { bar: 'bg-[#14b8a6]', text: 'text-[#066a5e] dark:text-teal-400',    badge: 'bg-[#9aeed9] text-[#066a5e] dark:bg-teal-400/15 dark:text-teal-300',    panel: 'bg-[#c7f5e9]', glowDark: 'dark:shadow-[0_0_26px_-6px_rgba(45,212,191,0.35)]' },
  blue:    { bar: 'bg-[#3b82f6]', text: 'text-[#1d4ed8] dark:text-blue-400',   badge: 'bg-[#bcdcff] text-[#1d4ed8] dark:bg-blue-400/15 dark:text-blue-300',   panel: 'bg-[#d8e9ff]', glowDark: 'dark:shadow-[0_0_26px_-6px_rgba(59,130,246,0.35)]' },
  violet:  { bar: 'bg-[#8b5cf6]', text: 'text-[#5b21b6] dark:text-violet-400', badge: 'bg-[#dfcdff] text-[#5b21b6] dark:bg-violet-400/15 dark:text-violet-300', panel: 'bg-[#ecdfff]', glowDark: 'dark:shadow-[0_0_26px_-6px_rgba(139,92,246,0.35)]' },
  emerald: { bar: 'bg-[#10b981] ', text: 'text-[#046c4e] dark:text-emerald-400', badge: 'bg-[#a7f3d0] text-[#046c4e] dark:bg-emerald-400/15 dark:text-emerald-300', panel: 'bg-[#c3f5e0]', glowDark: 'dark:shadow-[0_0_26px_-6px_rgba(16,185,129,0.35)]' },
  amber:   { bar: 'bg-[#f0a860]', text: 'text-[#92400e] dark:text-signal',    badge: 'bg-[#ffdca0] text-[#92400e] dark:bg-signal/15 dark:text-signal',       panel: 'bg-[#ffe9c0]', glowDark: 'dark:shadow-[0_0_26px_-6px_rgba(240,168,96,0.35)]' },
  alert:   { bar: 'bg-[#f43f5e]', text: 'text-[#9f1239] dark:text-rose-400',  badge: 'bg-[#ffc3cf] text-[#9f1239] dark:bg-rose-400/15 dark:text-rose-300',   panel: 'bg-[#ffd6de]', glowDark: 'dark:shadow-[0_0_26px_-6px_rgba(244,63,94,0.35)]' },
  neutral: { bar: 'bg-navy/40',   text: 'text-ink dark:text-slate-200',       badge: 'bg-slate-500/10 text-ink dark:text-slate-200',                          panel: 'bg-white',      glowDark: '' },
}

export default function KpiCard({ label, value, unit, trend, accent = 'teal', icon: Icon }) {
  const style = ACCENT_STYLES[accent] || ACCENT_STYLES.teal
  const trendUp = trend > 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4 }}
      transition={{ type: 'spring', stiffness: 260, damping: 22 }}
      className={`flex min-h-[142px] flex-col gap-3 rounded-[1.35rem] border border-white/80 p-5 relative overflow-hidden
                  shadow-[0_14px_30px_-26px_rgba(15,23,42,0.48)] transition-all duration-300 hover:-translate-y-1 hover:shadow-lg
                  dark:border-white/[0.08] dark:bg-[#0d0f13] ${style.panel} ${style.glowDark}`}
    >
      <div className={`absolute bottom-0 left-0 top-0 w-[3px] ${style.bar} dark:shadow-[0_0_12px_2px_currentColor]`} />

      <div className="flex items-start justify-between">
        <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-slate-600 dark:text-slate-500">
          {label}
        </span>
        {Icon && (
          <span className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${style.badge}`}>
            <Icon size={15} strokeWidth={2.2} />
          </span>
        )}
      </div>

      <div className="flex items-baseline gap-1.5">
        <span className={`font-display text-3xl font-semibold tracking-tight ${style.text}`}><AnimatedNumber value={value} /></span>
        {unit && <span className="font-mono text-xs text-slate-600 dark:text-slate-400">{unit}</span>}
      </div>

      {trend !== undefined && (
        <span className={`font-mono text-[10px] ${trendUp ? 'text-amber-700 dark:text-signal' : 'text-teal-700 dark:text-teal-400'}`}>
          {trendUp ? '▲' : '▼'} {Math.abs(trend)}% vs prev period
        </span>
      )}
    </motion.div>
  )
}
