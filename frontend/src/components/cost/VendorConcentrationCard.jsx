import Card from '../maintenance/Card'
import { formatINR } from '../../services/costService'

export default function VendorConcentrationCard({ concentration }) {
  if (!concentration) return null
  const { top_vendors, top_n_share_pct, total_spend_inr } = concentration
  const risky = top_n_share_pct >= 60

  return (
    <Card title="Vendor / Authority Concentration" badge={risky ? 'CONCENTRATION RISK' : 'DIVERSIFIED'}>
      <div className="flex items-baseline gap-2 mb-4">
        <span className={`font-display text-3xl font-semibold ${risky ? 'text-amber-600 dark:text-signal' : 'text-teal-600 dark:text-teal-400'}`}>{top_n_share_pct}%</span>
        <span className="font-mono text-xs text-slate-500">of {formatINR(total_spend_inr)} total sits with the top {top_vendors?.length || 0}</span>
      </div>
      <div className="flex flex-col gap-2">
        {top_vendors?.map(v => (
          <div key={v.vendor_id} className="flex items-center justify-between text-xs">
            <span className="text-slate-600 dark:text-slate-300 truncate max-w-[60%]">{v.vendor_name}</span>
            <span className="font-mono text-slate-400">{v.share_pct}% · {formatINR(v.total_spend_inr)}</span>
          </div>
        ))}
      </div>
      <p className="font-body text-[11px] text-slate-500 mt-4 leading-relaxed border-t border-slate-200 dark:border-slate-800 pt-3">
        Entries starting "BBMP-EE/CE" are real issuing engineering offices/circles from the source tender data, not private
        contractors (the source doesn't name the winning bidder) — read this as departmental spend concentration for those
        rows. "INTERNAL-*" entries are this platform's own derived operational cost, not a vendor at all.
      </p>
    </Card>
  )
}
