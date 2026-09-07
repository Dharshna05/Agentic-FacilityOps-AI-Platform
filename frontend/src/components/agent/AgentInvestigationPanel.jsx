import { motion } from 'framer-motion'
import { Bot, Play, Sparkles } from 'lucide-react'
import AgentTraceViewer from './AgentTraceViewer'

export default function AgentInvestigationPanel({
  investigation,
  isLoading,
  onRun,
  buildingId,
  title,
  prompt,
  traceTitle,
  hint,
  buttonLabel,
  accent = 'teal',
}) {
  const accentClass = accent === 'rose' ? 'bg-[#fff0f3]' : accent === 'violet' ? 'bg-[#f3efff]' : accent === 'blue' ? 'bg-[#ecf5ff]' : 'bg-[#ecfbf6]'
  const buttonClass = accent === 'rose' ? 'bg-[#e11d48] hover:bg-[#c81942]' : accent === 'violet' ? 'bg-[#7c3aed] hover:bg-[#6932ca]' : accent === 'blue' ? 'bg-[#2374d9] hover:bg-[#1763c2]' : 'bg-[#0d9488] hover:bg-[#087c72]'

  return (
    <section className={`rounded-[1.8rem] p-3 sm:p-4 ${accentClass}`}>
      <div className="mb-3 flex items-center gap-2 px-2 pt-1">
        <Sparkles size={14} className="text-slate-700" />
        <span className="font-mono text-[10px] tracking-[0.18em] text-slate-500">THE AI DESK</span>
      </div>
      <div className="grid items-stretch gap-3 lg:grid-cols-[minmax(260px,.72fr)_minmax(0,1.7fr)]">
        <motion.div whileHover={{ y: -3, rotate: -0.25 }} className="flex flex-col justify-between rounded-[1.4rem] bg-[#1c1d21] p-5 text-white shadow-xl shadow-slate-500/10 sm:p-6">
          <div>
            <div className="mb-5 flex items-center justify-between">
              <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/[0.12] text-[#c7f36a]"><Bot size={19} /></span>
              <span className="rounded-full bg-white/[0.09] px-2.5 py-1 font-mono text-[9px] tracking-wider text-slate-300">LIVE TOOL CALLING</span>
            </div>
            <p className="font-mono text-[9px] tracking-[0.16em] text-slate-500">agent://facility-ops/{buildingId}</p>
            <h2 className="mt-2 font-display text-xl font-semibold text-white">{title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-300">{prompt}</p>
          </div>
          <button onClick={onRun} disabled={isLoading} className={`mt-6 inline-flex w-full items-center justify-center gap-2 rounded-full px-4 py-3 font-mono text-[11px] tracking-wide text-white shadow-lg transition-all hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-45 ${buttonClass}`}>
            <Play size={12} fill="currentColor" />{isLoading ? 'AGENT WORKING…' : buttonLabel}
          </button>
        </motion.div>
        <AgentTraceViewer investigation={investigation} isLoading={isLoading} title={traceTitle} hint={hint} />
      </div>
    </section>
  )
}
