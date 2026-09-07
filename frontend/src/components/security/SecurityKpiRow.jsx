import { KeyRound, Activity, ShieldOff, FlagTriangleRight, ScanEye } from 'lucide-react'
import KpiCard from '../cards/KpiCard'

export default function SecurityKpiRow({ building, confidence, hideHero = false }) {
  return (
    <div className={`grid grid-cols-1 sm:grid-cols-2 ${hideHero ? 'xl:grid-cols-4' : 'xl:grid-cols-5'} gap-4`}>
      <KpiCard label="Access Points" value={building.access_points_monitored} accent="blue" icon={KeyRound} />
      {!hideHero && (
        <KpiCard label="Events (24h)" value={building.events_last_24h} accent="teal" icon={Activity} />
      )}
      <KpiCard label="Denied (24h)" value={building.denied_last_24h} accent="amber" icon={ShieldOff} />
      <KpiCard label="Flagged (24h)" value={building.flagged_last_24h} accent="alert" icon={FlagTriangleRight} />
      {confidence?.available && (
        <KpiCard
          label="Detector F1"
          value={confidence.f1}
          unit={`P ${confidence.precision} / R ${confidence.recall}`}
          accent="violet"
          icon={ScanEye}
        />
      )}
    </div>
  )
}
