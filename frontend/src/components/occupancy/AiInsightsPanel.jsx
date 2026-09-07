import { motion } from 'framer-motion'
import { Sparkles, MoveRight } from 'lucide-react'

export default function AiInsightsPanel({ insights, bestZone }) {
  if (!insights?.length && !bestZone) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 260, damping: 24 }}
      className="surface-card p-5 flex flex-col gap-3"
    >
      <div className="flex items-center gap-2">
        <span className="w-8 h-8 rounded-lg bg-violet-500/10 text-violet-600 dark:text-violet-400 flex items-center justify-center shrink-0">
          <Sparkles size={15} strokeWidth={2.2} />
        </span>
        <h3 className="font-display text-sm font-semibold text-ink dark:text-slate-100">AI Insights</h3>
        <span className="data-pill ml-auto">RULE-BASED, LIVE DATA</span>
      </div>

      <ul className="flex flex-col gap-2">
        {insights?.map((text, i) => (
          <li key={i} className="flex items-start gap-2 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
            <span className="w-1 h-1 rounded-full bg-violet-500 dark:bg-violet-400 mt-1.5 shrink-0" />
            {text}
          </li>
        ))}
      </ul>

      {bestZone && (
        <div className="mt-1 pt-3 border-t border-slate-200 dark:border-slate-800 flex items-center gap-3">
          <MoveRight size={14} className="text-teal-600 dark:text-teal-400 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs text-ink dark:text-slate-200">
              Best available: <span className="font-medium">{bestZone.name}</span>
            </p>
            <p className="font-mono text-[10px] text-slate-500">
              {bestZone.available_spots} spots free · {bestZone.current_utilization_pct}% utilized
            </p>
          </div>
        </div>
      )}
    </motion.div>
  )
}
