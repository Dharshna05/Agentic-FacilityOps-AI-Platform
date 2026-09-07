import { AlertTriangle } from 'lucide-react'

/**
 * Shared across every dashboard that now reports `data_drift` (Energy,
 * Maintenance, Security, Cost) — was written once inline in Energy's
 * ForecastCard, extracted here so the other three domains render an
 * identical, consistent warning instead of four slightly-different copies.
 */
export default function DataDriftBanner({ drift, subject = 'this dataset' }) {
  if (!drift?.drift_detected) return null

  return (
    <div className="flex items-start gap-2 mt-2.5 px-2.5 py-2 rounded-lg border border-amber-400/40 bg-amber-50 dark:bg-amber-500/10">
      <AlertTriangle size={13} className="text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
      <p className="text-[11px] text-amber-700 dark:text-amber-300 leading-relaxed">
        <span className="font-semibold">Different dataset detected</span> — {subject} doesn't match what this
        model was trained on ({drift.level} drift). The confidence/accuracy shown reflects the ORIGINAL training
        data, not this dataset — treat this prediction as unverified until the model is retrained on data like this.
      </p>
    </div>
  )
}
