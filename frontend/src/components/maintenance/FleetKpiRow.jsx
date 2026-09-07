import { Boxes, HeartPulse, AlertOctagon, ClipboardList, Gauge } from "lucide-react";
import KpiCard from "../cards/KpiCard";

export default function FleetKpiRow({ fleet, workOrderCount, confidence }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">

      <KpiCard
        label="Assets Monitored"
        value={fleet.assets_monitored}
        accent="blue"
        icon={Boxes}
      />

      <KpiCard
        label="Avg Health Score"
        value={fleet.avg_health_score}
        unit="%"
        accent="emerald"
        icon={HeartPulse}
      />

      <KpiCard
        label="Critical Assets"
        value={fleet.open_critical}
        accent="alert"
        icon={AlertOctagon}
      />

      <KpiCard
        label="Open Work Orders"
        value={workOrderCount}
        accent="amber"
        icon={ClipboardList}
      />

      {confidence?.available && (
        <KpiCard
          label="Model Confidence"
          value={confidence.confidence}
          unit={`· MAE ${confidence.mae_cycles}d`}
          accent="violet"
          icon={Gauge}
        />
      )}

    </div>
  );
}