import { IndianRupee, Receipt, Building2, TrendingUp } from 'lucide-react'
import KpiCard from '../cards/KpiCard'
import { formatINR } from '../../services/costService'

export default function CostKpiRow({ summary, forecast, hideHero = false }) {
  return (
    <div className={`grid grid-cols-1 sm:grid-cols-2 ${hideHero ? 'xl:grid-cols-4' : 'xl:grid-cols-5'} gap-4`}>
      <KpiCard label="Total Spend" value={formatINR(summary.total_spend_inr)} unit={`${summary.record_count} records`} accent="amber" icon={IndianRupee} />
      {!hideHero && (
        <KpiCard label="Records Tracked" value={summary.record_count} accent="teal" icon={Receipt} />
      )}
      <KpiCard label="Vendors/Authorities" value={summary.vendor_count} accent="blue" icon={Building2} />
      {forecast?.available && (
        <KpiCard
          label="3-wk Trend"
          value={forecast.direction === 'up' ? '▲ Up' : forecast.direction === 'down' ? '▼ Down' : '— Flat'}
          unit={`${formatINR(forecast.predicted_next_3wk_avg_spend_inr)} proj.`}
          accent={forecast.direction === 'up' ? 'alert' : 'emerald'}
          icon={TrendingUp}
        />
      )}
    </div>
  )
}
