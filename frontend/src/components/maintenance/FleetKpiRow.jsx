import KpiCard from "../cards/KpiCard";

export default function FleetKpiRow({ fleet, workOrderCount }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">

      <KpiCard
        label="Assets Monitored"
        value={fleet.assets_monitored}
        accent="blue"
      />

      <KpiCard
        label="Avg Health Score"
        value={fleet.avg_health_score}
        unit="%"
        accent="emerald"
      />

      <KpiCard
        label="Critical Assets"
        value={fleet.open_critical}
        accent="alert"
      />

      <KpiCard
        label="Open Work Orders"
        value={workOrderCount}
        accent="amber"
      />

    </div>
  );
}