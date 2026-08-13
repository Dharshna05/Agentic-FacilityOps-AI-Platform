import { useEffect, useState } from 'react'
import { highlightForToolCall, toolDisplayName } from './traceFormatters'
import { useTheme } from '../../context/ThemeContext'

const TOOL_ICONS = {
  get_consumption_summary: '⌁',
  get_submeter_breakdown: '⊞',
  get_anomalies: '◉',
  get_temperature_correlation: '≋',
  get_occupancy_correlation: '⌂',
  get_ml_forecast: '↗',
  flag_for_maintenance_review: '⚑',
  get_fleet_summary: '▦',
  get_asset_health: '♦',
  get_at_risk_assets: '▲',
  create_work_order: '⚑',
}

const DEFAULT_FLAG_TOOLS = ['flag_for_maintenance_review', 'create_work_order']

export default function AgentTraceViewer({
  investigation,
  isLoading,
  title = 'Agent Reasoning Trace',
  hint = 'The agent chose these tools itself, in this order — not a fixed pipeline.',
  flagTools = DEFAULT_FLAG_TOOLS,
}) {
  const { theme } = useTheme()
  const [revealedCount, setRevealedCount] = useState(0)

  useEffect(() => {
    if (!investigation) {
      setRevealedCount(0)
      return
    }
    setRevealedCount(0)
    const total = investigation.tool_calls.length
    let i = 0
    const interval = setInterval(() => {
      i += 1
      setRevealedCount(i)
      if (i >= total) clearInterval(interval)
    }, 320)
    return () => clearInterval(interval)
  }, [investigation])

  const totalCalls = investigation?.tool_calls.length ?? 0
  const isRevealing = investigation && revealedCount < totalCalls
  const isComplete = investigation && revealedCount >= totalCalls && totalCalls > 0

  const statusLabel = isLoading ? 'CONNECTING' : isRevealing ? 'INVESTIGATING' : isComplete ? 'COMPLETE' : 'IDLE'
  const statusColor = isLoading || isRevealing ? 'bg-amber-500 dark:bg-signal' : isComplete ? 'bg-teal-500 dark:bg-teal-400' : 'bg-slate-400 dark:bg-slate-600'
  const statusPulses = isLoading || isRevealing
  const gridDot = theme === 'dark' ? '#2DD4BF' : '#0d9488'

  return (
    <div className="bg-paper-raised dark:bg-panel border border-slate-200 dark:border-slate-800 rounded-xl p-5 relative overflow-hidden">
      <div
        className="absolute inset-0 opacity-[0.04] dark:opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage: `linear-gradient(${gridDot} 1px, transparent 1px), linear-gradient(90deg, ${gridDot} 1px, transparent 1px)`,
          backgroundSize: '24px 24px',
        }}
      />

      <div className="relative flex items-center justify-between mb-1">
        <h3 className="font-display text-sm font-medium text-ink dark:text-slate-200 tracking-wide">
          {title}
        </h3>
        <div className="flex items-center gap-2">
          <span className={`w-1.5 h-1.5 rounded-full ${statusColor} ${statusPulses ? 'animate-pulse-line' : ''}`} />
          <span className="font-mono text-[10px] tracking-widest text-slate-500">{statusLabel}</span>
        </div>
      </div>
      <p className="relative text-[11px] text-slate-500 mb-4 font-body">
        {hint}
      </p>

      {!investigation && !isLoading && (
        <div className="relative text-xs text-slate-400 dark:text-slate-600 font-mono py-6 text-center">
          no investigation run yet
        </div>
      )}

      {isLoading && (
        <div className="relative flex items-center gap-2 py-6 justify-center">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500 dark:bg-signal animate-pulse-line" />
          <span className="font-mono text-xs text-slate-500">contacting agent…</span>
        </div>
      )}

      <div className="relative flex flex-col">
        {investigation?.tool_calls.slice(0, revealedCount).map((call, i) => {
          const isLastVisible = i === revealedCount - 1
          const isFlag = flagTools.includes(call.tool)
          return (
            <div key={i} className="flex gap-3 animate-trace-in">
              <div className="flex flex-col items-center">
                <div
                  className={`w-6 h-6 rounded-md flex items-center justify-center text-xs font-mono border shrink-0 ${
                    isFlag
                      ? 'border-amber-400 dark:border-signal text-amber-600 dark:text-signal bg-amber-50 dark:bg-signal/10'
                      : 'border-teal-400/60 dark:border-teal-400/40 text-teal-600 dark:text-teal-400 bg-teal-50 dark:bg-teal-400/5'
                  }`}
                >
                  {TOOL_ICONS[call.tool] || '•'}
                </div>
                {i < totalCalls - 1 && (
                  <div className={`w-px flex-1 min-h-[22px] my-0.5 ${
                    isLastVisible && isRevealing ? 'bg-amber-400/60 dark:bg-signal/50 animate-pulse-line' : 'bg-slate-200 dark:bg-slate-700/60'
                  }`} />
                )}
              </div>

              <div className="pb-5 flex-1 min-w-0">
                <div className="flex items-baseline gap-2 flex-wrap">
                  <span className="font-mono text-[10px] text-slate-400 dark:text-slate-600">{String(i + 1).padStart(2, '0')}</span>
                  <span className="font-mono text-xs text-ink dark:text-slate-300">{toolDisplayName(call.tool)}()</span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5 font-body">
                  {highlightForToolCall(call.tool, call.result)}
                </p>
              </div>
            </div>
          )
        })}
      </div>

      {isComplete && (
        <div className="relative mt-1 pt-4 border-t border-slate-200 dark:border-slate-800 animate-trace-in">
          <span className="font-mono text-[10px] tracking-widest text-teal-600 dark:text-teal-400/70">FINAL SYNTHESIS</span>
          <p className="text-xs text-slate-600 dark:text-slate-300 mt-2 whitespace-pre-line leading-relaxed font-body">
            {investigation.final_summary}
          </p>
        </div>
      )}
    </div>
  )
}
