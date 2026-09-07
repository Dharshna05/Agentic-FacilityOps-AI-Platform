import { motion } from 'framer-motion'
import { ArrowUpRight, CalendarDays } from 'lucide-react'
import LiveIndicator from './LiveIndicator'

const STYLE = {
  blue: { block: 'bg-[#dcedff]', ink: 'text-[#2573d5]', orb: 'bg-[#7fb7ff]' },
  teal: { block: 'bg-[#dff7ef]', ink: 'text-[#078c7d]', orb: 'bg-[#74dec8]' },
  violet: { block: 'bg-[#ede5ff]', ink: 'text-[#7445d5]', orb: 'bg-[#bfa6ff]' },
  rose: { block: 'bg-[#ffe4e9]', ink: 'text-[#d82750]', orb: 'bg-[#ff9eb2]' },
  amber: { block: 'bg-[#ffe9c0]', ink: 'text-[#92400e]', orb: 'bg-[#f0a860]' },
}

export default function DashboardHeader({ Icon, agentLabel, title, emphasis, description, buildingId, lastUpdated, isRefreshing, onRefresh, accent = 'teal' }) {
  const style = STYLE[accent]
  const today = new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })
  const hour = new Date().getHours()
  const greeting = hour < 5 ? 'Burning the midnight oil,' : hour < 12 ? 'Good morning,' : hour < 17 ? 'Good afternoon,' : hour < 21 ? 'Good evening,' : 'Working late,'
  const eyebrowPrefix = hour < 5 ? 'LATE NIGHT' : hour < 12 ? 'GOOD MORNING' : hour < 17 ? 'GOOD AFTERNOON' : hour < 21 ? 'GOOD EVENING' : 'LATE NIGHT'
  const eyebrow = `${eyebrowPrefix} · ${agentLabel}`
  return (
    <header className="px-5 pt-7 sm:px-7 lg:px-9 lg:pt-9">
      <div className="flex flex-wrap items-start justify-between gap-5">
        <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ type: 'spring', stiffness: 260, damping: 24 }}>
          <div className="mb-3 flex items-center gap-2 font-mono text-[9px] tracking-[0.16em] text-slate-400"><span className={`h-2 w-2 rounded-full ${style.orb}`} />{eyebrow}</div>
          <h1 className="font-display text-[2rem] font-semibold tracking-[-0.045em] text-slate-900 dark:text-white sm:text-[2.5rem]">{greeting} <span className={`${style.ink}`}>Operator.</span></h1>
          <p className="mt-2 max-w-xl text-sm text-slate-500">Here’s what your facility is telling you today. <span className="font-medium text-slate-700 dark:text-slate-300">{title} {emphasis.toLowerCase()}</span> is up to date.</p>
        </motion.div>
        <div className="flex items-center gap-2"><div className="hidden rounded-full border border-slate-200 bg-white px-3 py-2 font-mono text-[10px] text-slate-500 shadow-sm sm:flex sm:items-center sm:gap-2 dark:border-white/[0.08] dark:bg-panel"><CalendarDays size={13} />{today}</div><div className="rounded-full border border-slate-200 bg-white px-3 py-2 shadow-sm dark:border-white/[0.08] dark:bg-panel"><LiveIndicator lastUpdated={lastUpdated} isRefreshing={isRefreshing} onRefresh={onRefresh} /></div></div>
      </div>
      <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08, type: 'spring', stiffness: 260, damping: 24 }} className={`mt-6 flex flex-wrap items-center justify-between gap-4 rounded-[1.5rem] px-5 py-4 ${style.block}`}>
        <div className="flex items-center gap-3"><span className={`grid h-10 w-10 place-items-center rounded-2xl bg-white/80 ${style.ink} shadow-sm`}><Icon size={19} /></span><div><p className={`font-display text-sm font-semibold ${style.ink}`}>{title} {emphasis}</p><p className="mt-0.5 font-mono text-[9px] tracking-wide text-slate-500">{buildingId} · {description}</p></div></div>
        <span className={`flex items-center gap-1 font-mono text-[10px] font-medium ${style.ink}`}>OPEN WORKSPACE <ArrowUpRight size={13} /></span>
      </motion.div>
    </header>
  )
}
