import Card from '../maintenance/Card'
import { formatINR } from '../../services/costService'

function scoreColor(score) {
  if (score >= 0.75) return 'text-rose-500'
  if (score >= 0.6) return 'text-amber-500'
  return 'text-slate-400'
}

export default function FlaggedInvoicesList({ invoices }) {
  return (
    <Card title="Flagged Cost Records" badge="ANOMALY DETECTOR">
      {!invoices?.length && <div className="text-xs text-slate-500 font-mono py-8 text-center">no flagged records</div>}
      <div className="flex flex-col gap-2 max-h-[420px] overflow-y-auto pr-1">
        {invoices?.map((inv, index) => (
          <div key={inv.record_id} className="group border border-slate-200 dark:border-slate-800 border-l-4 border-l-amber-500 rounded-xl px-3 py-3 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md hover:border-amber-400/50">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm text-ink dark:text-slate-200 truncate">{inv.vendor_name}</p>
                <p className="font-mono text-[10px] text-slate-500 mt-0.5">
                  {new Date(inv.date).toLocaleDateString()} · {formatINR(inv.amount_inr)} · {inv.category}
                </p>
              </div>
              <span className={`shrink-0 font-mono text-xs font-medium ${scoreColor(inv.anomaly_score)}`}>{inv.anomaly_score.toFixed(2)}</span>
            </div>
            <div className="mt-2 flex justify-between font-mono text-[9px] tracking-wider text-slate-400"><span>RECORD {String(index + 1).padStart(2, '0')}</span><span className="opacity-0 transition-opacity group-hover:opacity-100">REVIEW SIGNAL →</span></div>
          </div>
        ))}
      </div>
    </Card>
  )
}
