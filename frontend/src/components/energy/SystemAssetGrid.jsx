import { motion } from 'framer-motion'
import { Wind, Lightbulb, Plug, Boxes } from 'lucide-react'

const SYSTEMS = [
  { key: 'hvac_pct', label: 'HVAC', icon: Wind, color: 'teal' },
  { key: 'lighting_pct', label: 'Lighting', icon: Lightbulb, color: 'blue' },
  { key: 'plug_load_pct', label: 'Plug Load', icon: Plug, color: 'violet' },
  { key: 'other_pct', label: 'Other Systems', icon: Boxes, color: 'amber' },
]

const COLOR_MAP = {
  teal:   { text: 'text-teal-600 dark:text-teal-400',    bg: 'bg-teal-500/10',   border: 'border-teal-500/20' },
  blue:   { text: 'text-blue-600 dark:text-blue-400',    bg: 'bg-blue-500/10',   border: 'border-blue-500/20' },
  violet: { text: 'text-violet-600 dark:text-violet-400', bg: 'bg-violet-500/10', border: 'border-violet-500/20' },
  amber:  { text: 'text-amber-600 dark:text-signal',      bg: 'bg-amber-500/10',  border: 'border-amber-500/20' },
}

// Honest share tiers — this describes proportion of total load, not asset
// health or failure risk (which the Energy module doesn't measure per-system).
function shareTier(pct) {
  if (pct >= 40) return { label: 'dominant share', dot: 'bg-amber-500 dark:bg-signal' }
  if (pct >= 15) return { label: 'moderate share', dot: 'bg-teal-500 dark:bg-teal-400' }
  return { label: 'minor share', dot: 'bg-slate-400 dark:bg-slate-600' }
}

export default function SystemAssetGrid({ breakdown, totalKwh }) {
  if (!breakdown) return null

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      {SYSTEMS.map((sys, i) => {
        const pct = breakdown[sys.key] || 0
        const kwh = Math.round((pct / 100) * totalKwh)
        const tier = shareTier(pct)
        const c = COLOR_MAP[sys.color]
        const Icon = sys.icon

        return (
          <motion.div
            key={sys.key}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: 'spring', stiffness: 260, damping: 22, delay: i * 0.04 }}
            whileHover={{ y: -3 }}
            className={`bg-paper-raised dark:bg-panel border ${c.border} rounded-xl p-4 flex flex-col gap-3`}
          >
            <div className="flex items-start justify-between">
              <span className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${c.bg} ${c.text}`}>
                <Icon size={16} strokeWidth={2.2} />
              </span>
              <span className="flex items-center gap-1.5 font-mono text-[9px] tracking-widest text-slate-400 dark:text-slate-500">
                <span className={`w-1.5 h-1.5 rounded-full ${tier.dot}`} />
                {tier.label.toUpperCase()}
              </span>
            </div>

            <div>
              <div className="font-display text-sm font-medium text-ink dark:text-slate-200">{sys.label}</div>
              <div className="flex items-baseline gap-1.5 mt-1">
                <span className="font-mono text-xl font-semibold text-ink dark:text-slate-100">{kwh.toLocaleString()}</span>
                <span className="font-mono text-[10px] text-slate-400">kWh</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ type: 'spring', stiffness: 120, damping: 20, delay: 0.15 + i * 0.04 }}
                  className={`h-full rounded-full ${c.text.replace('text-', 'bg-')}`}
                />
              </div>
              <span className={`font-mono text-[11px] font-medium ${c.text}`}>{pct.toFixed(1)}%</span>
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}
