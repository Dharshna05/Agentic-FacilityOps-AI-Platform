// Maps a tool name + its raw JSON result to a short, human-readable
// highlight line — so the trace reads like a technician's log, not raw JSON.
export function highlightForToolCall(name, result) {
  if (!result) return 'no data returned'

  switch (name) {
    case 'get_consumption_summary':
      return `${result.total_kwh?.toLocaleString()} kWh total · peak ${result.peak_kwh} kWh`
    case 'get_submeter_breakdown':
      return `HVAC ${result.hvac_pct}% · Lighting ${result.lighting_pct}% · Plug ${result.plug_load_pct}%`
    case 'get_anomalies': {
      const high = (result || []).filter(a => a.severity === 'high').length
      return `${result?.length ?? 0} anomalies found (${high} high-severity)`
    }
    case 'get_temperature_correlation':
      return result.available ? `correlation r = ${result.correlation}` : 'temperature data unavailable'
    case 'get_occupancy_correlation':
      return result.available
        ? `unoccupied load = ${result.unoccupied_load_pct_of_occupied}% of occupied avg`
        : 'occupancy data unavailable'
    case 'get_ml_forecast':
      return `predicted ${result.predicted_kwh} kWh (${result.horizon} ahead, ${result.model_used}, `
        + `${result.confidence?.confidence ?? 'n/a'} confidence)`
    case 'flag_for_maintenance_review':
      return `flagged → ${result.severity} severity`
    case 'get_fleet_summary':
      return `${result.assets_monitored} assets · avg health ${result.avg_health_score}/100 · ${result.open_critical} critical`
    case 'get_asset_health':
      return `${result.name}: health ${result.health_score}/100 (${result.status}) · RUL ${result.predicted_rul_cycles}d`
    case 'get_at_risk_assets':
      return `${result?.length ?? 0} at-risk assets found`
    case 'create_work_order':
      return `work order #${result.id} opened → ${result.severity} severity`
    default:
      return 'completed'
  }
}

export function toolDisplayName(name) {
  return name.replace(/_/g, ' ')
}
