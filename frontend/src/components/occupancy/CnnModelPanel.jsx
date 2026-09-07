import { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { motion, AnimatePresence } from 'framer-motion'
import { BrainCircuit, Play, CheckCircle2, XCircle } from 'lucide-react'
import { occupancyService } from '../../services/occupancyService'

function ConfusionMatrix({ confusion }) {
  if (!confusion) return null
  const [[tn, fp], [fn, tp]] = confusion.matrix
  const max = Math.max(tn, fp, fn, tp)
  const cellStyle = (val) => ({
    opacity: 0.25 + 0.75 * (val / max),
  })

  return (
    <div className="grid grid-cols-[auto_1fr_1fr] gap-1 items-center font-mono text-[10px]">
      <div />
      <div className="text-center text-slate-400 pb-1">Pred: Empty</div>
      <div className="text-center text-slate-400 pb-1">Pred: Occupied</div>

      <div className="text-slate-400 pr-1">Actual: Empty</div>
      <div style={cellStyle(tn)} className="bg-teal-500 dark:bg-teal-400 text-white rounded-md py-3 text-center font-semibold">{tn}</div>
      <div style={cellStyle(fp)} className="bg-rose-400 dark:bg-rose-500 text-white rounded-md py-3 text-center font-semibold">{fp}</div>

      <div className="text-slate-400 pr-1">Actual: Occupied</div>
      <div style={cellStyle(fn)} className="bg-rose-400 dark:bg-rose-500 text-white rounded-md py-3 text-center font-semibold">{fn}</div>
      <div style={cellStyle(tp)} className="bg-teal-500 dark:bg-teal-400 text-white rounded-md py-3 text-center font-semibold">{tp}</div>
    </div>
  )
}

function ActivationHeatmap({ activations, title, subtitle }) {
  if (!activations?.length) return null
  const flat = activations.flat()
  const max = Math.max(...flat, 0.001)

  return (
    <div>
      <h5 className="font-mono text-[9px] tracking-widest text-slate-500 mb-1.5">{title}</h5>
      <div
        className="grid gap-[2px]"
        style={{ gridTemplateColumns: `repeat(${activations[0].length}, 1fr)` }}
      >
        {activations.flatMap((timestep, t) =>
          timestep.map((val, f) => (
            <div
              key={`${t}-${f}`}
              title={`t=${t + 1}, filter ${f + 1}: ${val.toFixed(3)}`}
              className="aspect-square rounded-[2px]"
              style={{
                backgroundColor: val <= 0 ? 'transparent' : `rgba(139, 92, 246, ${0.12 + 0.85 * (val / max)})`,
                border: val <= 0 ? '1px solid rgba(148,163,184,0.15)' : 'none',
              }}
            />
          ))
        )}
      </div>
      <p className="font-mono text-[8px] text-slate-400 mt-1">{subtitle}</p>
    </div>
  )
}

function LiveInferenceDemo() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const runDemo = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await occupancyService.getCnnLiveInference()
      setResult(data)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-xl border border-violet-500/20 dark:border-violet-400/15 bg-violet-500/[0.03] dark:bg-violet-400/[0.03] p-4 flex flex-col gap-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h4 className="font-display text-sm font-medium text-ink dark:text-slate-200">Live Inference Demo</h4>
          <p className="text-xs text-slate-500 mt-0.5">
            Runs the actual trained model on a real held-out window it's never seen — picked at random, right now.
          </p>
        </div>
        <button
          onClick={runDemo}
          disabled={loading}
          className="flex items-center gap-1.5 font-mono text-xs px-3.5 py-2 rounded-lg border border-violet-500/40 dark:border-violet-400/40
                     text-violet-700 dark:text-violet-300 bg-violet-50 dark:bg-violet-400/10 hover:bg-violet-100 dark:hover:bg-violet-400/20
                     disabled:opacity-40 disabled:cursor-not-allowed transition-colors shrink-0"
        >
          <Play size={12} /> {loading ? 'running model…' : result ? 'run again' : 'run live inference'}
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-400/30 bg-amber-500/5 p-3">
          <p className="text-xs text-amber-700 dark:text-signal leading-relaxed">{error}</p>
        </div>
      )}

      <AnimatePresence mode="wait">
        {result && (
          <motion.div
            key={JSON.stringify(result.raw_window).slice(0, 20)}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ type: 'spring', stiffness: 260, damping: 24 }}
            className="flex flex-col sm:flex-row gap-4"
          >
            <div className="flex flex-col gap-2 sm:w-56 shrink-0">
              <div className="flex items-center gap-2">
                {result.correct ? (
                  <CheckCircle2 size={16} className="text-teal-600 dark:text-teal-400" />
                ) : (
                  <XCircle size={16} className="text-rose-500" />
                )}
                <span className={`font-mono text-xs ${result.correct ? 'text-teal-700 dark:text-teal-400' : 'text-rose-500'}`}>
                  {result.correct ? 'Correct' : 'Wrong — shown honestly'}
                </span>
              </div>
              <div className="text-xs text-slate-500">
                Model predicted <span className="font-semibold text-ink dark:text-slate-200">{result.predicted_class}</span>
                {' '}({(result.confidence * 100).toFixed(1)}% confidence)
              </div>
              <div className="text-xs text-slate-500">
                Real label: <span className="font-semibold text-ink dark:text-slate-200">{result.true_class}</span>
              </div>
              <p className="font-mono text-[9px] text-slate-400 mt-1">{result.note}</p>
            </div>

            <div className="flex-1 min-w-0">
              <ResponsiveContainer width="100%" height={140}>
                <LineChart
                  data={result.raw_window.map((row, i) => ({
                    minute: i + 1,
                    ...Object.fromEntries(result.feature_cols.map((c, j) => [c, row[j]])),
                  }))}
                  margin={{ top: 4, right: 4, left: -20, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="2 4" className="stroke-slate-200 dark:stroke-slate-800" />
                  <XAxis dataKey="minute" tick={{ fontSize: 8, fontFamily: 'JetBrains Mono' }} className="fill-slate-400" />
                  <YAxis tick={{ fontSize: 8, fontFamily: 'JetBrains Mono' }} className="fill-slate-400" />
                  <Tooltip contentStyle={{ fontSize: 10, fontFamily: 'JetBrains Mono' }} />
                  {result.feature_cols.map((c, i) => (
                    <Line key={c} type="monotone" dataKey={c} dot={false} strokeWidth={1.25}
                          stroke={['#2dd4bf', '#3b82f6', '#f0a860', '#8b5cf6', '#f43f5e'][i % 5]} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
              <p className="font-mono text-[8px] text-slate-400 mt-1">real 10-minute sensor trace fed into the model for this prediction</p>
            </div>

            {(result.conv1_activations || result.conv2_activations) && (
              <div className="flex-1 min-w-0 flex flex-col gap-3 sm:border-l sm:border-slate-200 sm:dark:border-slate-800 sm:pl-4">
                <p className="font-mono text-[9px] tracking-widest text-violet-600 dark:text-violet-400">INSIDE THE NETWORK — REAL FILTER ACTIVATIONS</p>
                <ActivationHeatmap
                  activations={result.conv1_activations}
                  title="CONV LAYER 1 (10 timesteps × 16 filters)"
                  subtitle="brighter = that filter fired harder at that minute, for THIS exact window"
                />
                <ActivationHeatmap
                  activations={result.conv2_activations}
                  title="CONV LAYER 2 (5 timesteps × 32 filters)"
                  subtitle="deeper layer, after pooling — combines layer 1's patterns into higher-level shapes"
                />
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function CnnModelPanel({ cnn, baseline }) {
  if (!cnn?.available) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 240, damping: 24 }}
      className="surface-card p-5 md:p-6 flex flex-col gap-5"
    >
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <span className="w-10 h-10 rounded-xl bg-violet-500/10 text-violet-600 dark:text-violet-400 flex items-center justify-center shrink-0">
            <BrainCircuit size={18} strokeWidth={2.2} />
          </span>
          <div>
            <h3 className="font-display text-base font-semibold text-ink dark:text-slate-100">Supplementary CNN Model</h3>
            <p className="font-mono text-[10px] text-slate-500">{cnn.model_type}</p>
          </div>
        </div>
        <span className="data-pill">{cnn.window_size_minutes}-MIN SLIDING WINDOW</span>
      </div>

      <p className="text-xs text-slate-500 leading-relaxed max-w-3xl">{cnn.task}</p>

      {/* Metrics row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-violet-500/5 dark:bg-violet-400/5 border border-violet-500/15 rounded-xl p-3">
          <div className="font-mono text-[9px] tracking-widest text-slate-500">HELD-OUT ACCURACY</div>
          <div className="font-display text-xl font-semibold text-violet-700 dark:text-violet-400 mt-1">{(cnn.held_out_accuracy * 100).toFixed(2)}%</div>
        </div>
        <div className="bg-violet-500/5 dark:bg-violet-400/5 border border-violet-500/15 rounded-xl p-3">
          <div className="font-mono text-[9px] tracking-widest text-slate-500">PRECISION</div>
          <div className="font-display text-xl font-semibold text-ink dark:text-slate-100 mt-1">{cnn.precision.toFixed(3)}</div>
        </div>
        <div className="bg-violet-500/5 dark:bg-violet-400/5 border border-violet-500/15 rounded-xl p-3">
          <div className="font-mono text-[9px] tracking-widest text-slate-500">RECALL</div>
          <div className="font-display text-xl font-semibold text-ink dark:text-slate-100 mt-1">{cnn.recall.toFixed(3)}</div>
        </div>
        <div className="bg-violet-500/5 dark:bg-violet-400/5 border border-violet-500/15 rounded-xl p-3">
          <div className="font-mono text-[9px] tracking-widest text-slate-500">F1 SCORE</div>
          <div className="font-display text-xl font-semibold text-ink dark:text-slate-100 mt-1">{cnn.f1.toFixed(3)}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Training curves */}
        <div>
          <h4 className="font-display text-xs font-medium text-ink dark:text-slate-200 mb-2">Training vs. Held-out Accuracy</h4>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={cnn.training_history} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="2 4" className="stroke-slate-200 dark:stroke-slate-800" />
              <XAxis dataKey="epoch" tick={{ fontSize: 9, fontFamily: 'JetBrains Mono' }} className="fill-slate-400" />
              <YAxis domain={[0.8, 1]} tick={{ fontSize: 9, fontFamily: 'JetBrains Mono' }} className="fill-slate-400" />
              <Tooltip contentStyle={{ fontSize: 11, fontFamily: 'JetBrains Mono' }} />
              <Legend wrapperStyle={{ fontSize: 10, fontFamily: 'JetBrains Mono' }} />
              <Line type="monotone" dataKey="train_accuracy" name="train" stroke="#8b5cf6" dot={{ r: 2 }} strokeWidth={1.75} />
              <Line type="monotone" dataKey="val_accuracy" name="held-out" stroke="#2dd4bf" dot={{ r: 2 }} strokeWidth={1.75} />
            </LineChart>
          </ResponsiveContainer>
          <p className="font-mono text-[9px] text-slate-400 mt-1">
            Early stopping on held-out accuracy — the run shown is the model's actual best epoch, not cherry-picked.
          </p>
        </div>

        {/* Confusion matrix */}
        <div>
          <h4 className="font-display text-xs font-medium text-ink dark:text-slate-200 mb-2">Confusion Matrix (held-out)</h4>
          <ConfusionMatrix confusion={cnn.confusion_matrix} />
        </div>
      </div>

      {/* Honest comparison note */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-panel-raised p-4">
        <div className="flex items-baseline justify-between mb-2 flex-wrap gap-2">
          <span className="font-mono text-[10px] tracking-widest text-slate-500">VS. PRIMARY MODEL (Logistic Regression)</span>
          {baseline?.available && (
            <span className="font-mono text-xs text-teal-700 dark:text-teal-400">
              {(baseline.held_out_accuracy * 100).toFixed(2)}% accuracy · {baseline.model_used?.replace(/_/g, ' ')}
            </span>
          )}
        </div>
        <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{cnn.comparison_note}</p>
      </div>

      <LiveInferenceDemo />
    </motion.div>
  )
}
