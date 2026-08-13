import { useState, useEffect, useCallback } from 'react'
import { energyService } from '../../services/energyService'

const HORIZONS = [
  { key: '1h', label: '1H' },
  { key: '6h', label: '6H' },
  { key: '24h', label: '24H' },
]

const CONFIDENCE_STYLE = {
  high: 'text-teal-600 dark:text-teal-400 bg-teal-50 dark:bg-teal-400/10',
  medium: 'text-amber-600 dark:text-signal bg-amber-50 dark:bg-signal/10',
  low: 'text-red-500 dark:text-red-400 bg-red-50 dark:bg-red-500/10',
}

export default function ForecastCard() {
  const [horizon, setHorizon] = useState('1h')
  const [forecast, setForecast] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async (h) => {
    setLoading(true)
    try {
      const data = await energyService.getForecast('BLD-HQ-01', h)
      setForecast(data)
    } catch {
      setForecast(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(horizon) }, [horizon, load])

  const confidence = forecast?.confidence?.confidence
  const delta = forecast ? forecast.predicted_kwh - forecast.current_kwh : 0
  const isRising = delta > 0

  return (
    <div className="bg-paper-raised dark:bg-panel border border-slate-200 dark:border-slate-800 rounded-xl p-5">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h3 className="font-display text-sm font-medium text-ink dark:text-slate-200">ML Forecast</h3>
        <div className="flex gap-1">
          {HORIZONS.map(h => (
            <button
              key={h.key}
              onClick={() => setHorizon(h.key)}
              className={`text-xs px-2.5 py-1 rounded-md border transition-colors ${
                horizon === h.key
                  ? 'bg-teal-50 dark:bg-teal-500/20 border-teal-400 text-teal-700 dark:text-teal-300'
                  : 'border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:border-slate-400'
              }`}
            >
              {h.label}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="py-6 text-center font-mono text-xs text-slate-400 animate-pulse-line">
          predicting…
        </div>
      )}

      {!loading && forecast && (
        <>
          <div className="flex items-end gap-3 flex-wrap">
            <div>
              <span className="font-display text-3xl font-semibold text-teal-600 dark:text-teal-400">
                {forecast.predicted_kwh}
              </span>
              <span className="font-mono text-sm text-slate-400 dark:text-slate-600 ml-1">kWh</span>
            </div>
            <span className={`text-xs mb-1 ${isRising ? 'text-amber-600 dark:text-signal' : 'text-teal-600 dark:text-teal-400'}`}>
              {isRising ? '▲' : '▼'} {Math.abs(delta).toFixed(1)} kWh vs now ({forecast.current_kwh} kWh)
            </span>
          </div>

          <div className="flex items-center gap-2 mt-3 flex-wrap">
            <span className={`font-mono text-[10px] uppercase tracking-wide px-2 py-0.5 rounded ${CONFIDENCE_STYLE[confidence] || ''}`}>
              {confidence} confidence
            </span>
            <span className="font-mono text-[10px] text-slate-400 dark:text-slate-600">
              {forecast.model_used?.replace('_', ' ')} · MAE {forecast.confidence?.mae_kwh} kWh
            </span>
          </div>

          {confidence === 'low' && (
            <p className="text-[11px] text-red-500/80 dark:text-red-400/70 mt-2 leading-relaxed">
              24h-ahead accuracy is limited on this dataset (only {forecast.confidence?.improvement_over_naive_pct}%
              better than a naive guess) — treat this number as directional, not precise.
            </p>
          )}

          <p className="font-mono text-xs text-slate-400 dark:text-slate-500 mt-2">
            Predicted for {new Date(forecast.predicted_timestamp).toLocaleString(undefined, {
              month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
            })}
          </p>
        </>
      )}
    </div>
  )
}
