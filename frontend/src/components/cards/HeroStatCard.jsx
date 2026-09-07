import { motion } from 'framer-motion'

export default function HeroStatCard({ label, value, unit, trend, icon: Icon }) {
  const trendUp = trend > 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 240, damping: 22 }}
      whileHover={{ y: -3, scale: 1.005 }}
      className="relative h-full min-h-[230px] rounded-[1.6rem] p-6 flex flex-col justify-between overflow-hidden
                 border border-[#f5df78] bg-[#fff1a9] dark:border-teal-400/20 dark:bg-panel
                 backdrop-blur-sm shadow-[0_16px_42px_-26px_rgba(185,142,20,0.38)]"
    >
      {/* ambient glow blob */}
      <div className="absolute -top-12 -right-8 w-44 h-44 rounded-full bg-[#f9c85c]/45 blur-3xl pointer-events-none" />

      <div className="relative flex items-start justify-between">
        <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-slate-600 dark:text-slate-500">
          {label}
        </span>
        {Icon && (
          <span className="w-10 h-10 rounded-xl bg-white/60 dark:bg-teal-400/15 text-slate-800 dark:text-teal-400
                            flex items-center justify-center shrink-0 shadow-lg shadow-teal-500/10">
            <Icon size={18} strokeWidth={2.2} />
          </span>
        )}
      </div>

      <div className="relative mt-6">
        <div className="flex items-baseline gap-2">
        <span className="font-display text-5xl font-bold text-slate-900 dark:text-slate-50 tracking-tight tabular-nums">
            {value}
          </span>
          {unit && <span className="font-mono text-sm text-slate-400">{unit}</span>}
        </div>
        {trend !== undefined && (
          <span className={`inline-block mt-3 font-mono text-[11px] px-2 py-1 rounded-full border
            ${trendUp
              ? 'text-amber-600 dark:text-signal border-amber-400/30 bg-amber-500/5'
              : 'text-teal-600 dark:text-teal-400 border-teal-400/30 bg-teal-500/5'}`}>
            {trendUp ? '▲' : '▼'} {Math.abs(trend)}% vs prev period
          </span>
        )}
      </div>
    </motion.div>
  )
}
